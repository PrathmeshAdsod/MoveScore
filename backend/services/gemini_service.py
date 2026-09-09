"""
Gemini Service

Wraps the google-genai SDK (v2+) for:
1. Uploading video via the Gemini Files API
2. Choreography analysis (multimodal: video + prompt → ChoreographySchema)
3. Music plan reasoning (text: choreography + prefs → music prompt string)

Authentication: uses GEMINI_API_KEY environment variable.
"""

from __future__ import annotations

import io
import logging
import tempfile
import time
from pathlib import Path

from google import genai
from google.genai import types

from config import settings
from prompts.choreography_analysis import CHOREOGRAPHY_ANALYSIS_PROMPT
from prompts.music_plan import build_music_plan_prompt
from schemas.api import UserPreferences
from schemas.choreography import ChoreographySchema
from utils.errors import ChoreographyAnalysisError, MusicPlanError

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    """Return a configured google-genai client using the API key."""
    return genai.Client(api_key=settings.gemini_api_key)


def upload_video_to_files_api(
    video_bytes: bytes,
    mime_type: str = "video/mp4",
    display_name: str = "dance_video",
) -> types.File:
    """
    Upload a video to the Gemini Files API.
    Returns the File object (contains .name and .uri).
    The Files API auto-expires files after ~48 hours.

    Note: The google-genai v2 SDK requires a file path or IOBase, not raw bytes.
    We use a BytesIO stream to avoid writing to disk.
    """
    client = _get_client()
    logger.info("Uploading %d bytes to Gemini Files API...", len(video_bytes))

    file_stream = io.BytesIO(video_bytes)

    response = client.files.upload(
        file=file_stream,
        config=types.UploadFileConfig(
            display_name=display_name,
            mime_type=mime_type,
        ),
    )

    logger.info(
        "File uploaded: name=%s, state=%s", response.name, response.state
    )

    # Wait for the file to be ACTIVE before using it
    _wait_for_file_active(client, response.name)
    return response


def _wait_for_file_active(
    client: genai.Client, file_name: str, max_wait_secs: int = 60
) -> None:
    """Poll until the uploaded file transitions to ACTIVE state."""
    deadline = time.time() + max_wait_secs
    while time.time() < deadline:
        file_info = client.files.get(name=file_name)
        if file_info.state == types.FileState.ACTIVE:
            return
        if file_info.state == types.FileState.FAILED:
            raise ChoreographyAnalysisError(
                f"Gemini Files API processing failed for {file_name}"
            )
        logger.debug("File state: %s — waiting...", file_info.state)
        time.sleep(2)
    raise ChoreographyAnalysisError(
        f"File {file_name} did not become ACTIVE within {max_wait_secs}s"
    )


def delete_file_from_files_api(file_name: str) -> None:
    """Delete a file from the Gemini Files API after use."""
    try:
        client = _get_client()
        client.files.delete(name=file_name)
        logger.info("Deleted file from Files API: %s", file_name)
    except Exception as exc:
        logger.warning("Could not delete Files API file %s: %s", file_name, exc)


def analyze_choreography(
    video_bytes: bytes,
    mime_type: str = "video/mp4",
    max_retries: int = 2,
) -> ChoreographySchema:
    """
    Upload video to Gemini Files API, call gemini model with the
    choreography analysis prompt and response_schema, return parsed ChoreographySchema.

    Retries once with a stricter prompt on parse failure.
    """
    client = _get_client()
    uploaded_file: types.File | None = None

    try:
        # Step 1: Upload video
        uploaded_file = upload_video_to_files_api(video_bytes, mime_type=mime_type)

        # Step 2: Analyze with Gemini
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Choreography analysis attempt %d/%d (model: %s)",
                    attempt,
                    max_retries,
                    settings.gemini_model,
                )
                response = client.models.generate_content(
                    model=settings.gemini_model,
                    contents=[
                        types.Part.from_uri(
                            file_uri=uploaded_file.uri,
                            mime_type=mime_type,
                        ),
                        CHOREOGRAPHY_ANALYSIS_PROMPT,
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ChoreographySchema,
                        temperature=0.1,
                    ),
                )

                raw_text = response.text
                logger.debug(
                    "Gemini raw response (first 500 chars): %s", raw_text[:500]
                )

                # Parse and validate
                choreography = ChoreographySchema.model_validate_json(raw_text)
                logger.info(
                    "Choreography analysis complete: %d segments, %d key moments, confidence=%s",
                    len(choreography.segments),
                    len(choreography.key_moments),
                    choreography.analysis_confidence,
                )
                return choreography

            except Exception as exc:
                last_error = exc
                logger.warning("Analysis attempt %d failed: %s", attempt, exc)
                if attempt < max_retries:
                    time.sleep(1)

        raise ChoreographyAnalysisError(
            f"Failed after {max_retries} attempts: {last_error}"
        )

    finally:
        # Always clean up Files API resource
        if uploaded_file is not None:
            delete_file_from_files_api(uploaded_file.name)


def plan_music(
    choreography: ChoreographySchema,
    preferences: UserPreferences,
) -> str:
    """
    Call Gemini (text-only) to convert the choreography analysis + user preferences
    into a timestamp-aware natural language music prompt for Lyria.
    """
    client = _get_client()
    prompt = build_music_plan_prompt(choreography, preferences)

    logger.info("Generating music plan (model: %s)...", settings.gemini_model)
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=512,
            ),
        )
        music_prompt = response.text.strip()

        if not music_prompt:
            raise MusicPlanError("Gemini returned an empty music prompt")

        logger.info("Music plan generated (%d words)", len(music_prompt.split()))
        return music_prompt

    except MusicPlanError:
        raise
    except Exception as exc:
        raise MusicPlanError(str(exc)) from exc
