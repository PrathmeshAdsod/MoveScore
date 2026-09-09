"""
MoveScore — Google ADK & Gemini Enterprise Agent Platform Workflow

Architecture:
- Agent Runtime / ADK Agent:
    Tool 1: analyze_choreography (Gemini 3.8 Flash multimodal video analysis)
    Tool 2: plan_music (Gemini 3.8 Flash text reasoning for music direction)
    Tool 3: generate_music (Lyria 3.5 via Interactions API, output to GCS)
- Local Cloud Run Media Processing:
    Step 4: combine_media (FFmpeg safe H.264/yuv420p + AAC) -> V4 Signed URL

Generate Again logic:
    - cached_choreography + cached_music_prompt: skip tools 1 & 2, run 3 + 4
    - cached_choreography only: skip tool 1, rerun 2 + 3 + 4
    - fresh run: full pipeline
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass

from agent.tools.analyze_choreography import analyze_choreography_tool
from agent.tools.generate_music import generate_music_tool
from agent.tools.plan_music import plan_music_tool
from config import settings
from schemas.api import UserPreferences
from schemas.choreography import ChoreographySchema
from services.ffmpeg_service import combine_from_gcs
from utils.errors import (
    AgenticCinemaError,
    ChoreographyAnalysisError,
    MediaCombineError,
    MusicGenerationError,
    MusicPlanError,
)

logger = logging.getLogger(__name__)

_REMOTE_OUTPUT_KEYS = {"choreography_json", "music_prompt", "audio_gcs_uri"}


def _event_text_parts(event: object) -> list[str]:
    """Extract only model text blocks from an Agent Runtime stream event."""
    if isinstance(event, str):
        return [event]

    if not isinstance(event, Mapping) and hasattr(event, "model_dump"):
        event = event.model_dump()  # type: ignore[union-attr]

    if isinstance(event, Mapping):
        direct_text = event.get("text")
        content = event.get("content")
    else:
        direct_text = getattr(event, "text", None)
        content = getattr(event, "content", None)

    text_parts = [direct_text] if isinstance(direct_text, str) else []
    if content is None:
        return text_parts

    if not isinstance(content, Mapping) and hasattr(content, "model_dump"):
        content = content.model_dump()

    parts = (
        content.get("parts", [])
        if isinstance(content, Mapping)
        else getattr(content, "parts", [])
    )
    for part in parts or []:
        if not isinstance(part, Mapping) and hasattr(part, "model_dump"):
            part = part.model_dump()
        text = (
            part.get("text")
            if isinstance(part, Mapping)
            else getattr(part, "text", None)
        )
        if isinstance(text, str):
            text_parts.append(text)
    return text_parts


def _parse_remote_agent_payload(text_chunks: list[str]) -> dict:
    """Return the final structured payload without stringifying event dictionaries."""
    response_text = "".join(text_chunks).strip()
    decoder = json.JSONDecoder()

    for start in (index for index, char in enumerate(response_text) if char == "{"):
        try:
            payload, _ = decoder.raw_decode(response_text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and _REMOTE_OUTPUT_KEYS.issubset(payload):
            return payload

    raise ValueError(
        "No complete MoveScore JSON payload was found in the Agent Runtime events"
    )


@dataclass
class AgentResult:
    """Output from a complete MoveScore pipeline run."""

    choreography: ChoreographySchema
    music_prompt: str
    audio_gcs_uri: str
    final_video_signed_url: str


class ChoreographyMusicAgent:
    """
    MoveScore pipeline agent built for Gemini Enterprise Agent Platform.

    Orchestrates the 3 AI steps (analysis, planning, music generation)
    via static ADK tools or remote Agent Runtime, then performs deterministic
    FFmpeg video+audio combine on Cloud Run.
    """

    def run(
        self,
        video_bytes: bytes,
        video_mime_type: str,
        video_gcs_uri: str,
        user_preferences: UserPreferences,
        cached_choreography: dict | None = None,
        cached_music_prompt: str | None = None,
    ) -> AgentResult:
        """
        Run the complete pipeline.

        Supports Generate Again via cached_choreography and cached_music_prompt.
        """
        logger.info(
            "ChoreographyMusicAgent.run: has_choreo_cache=%s, has_prompt_cache=%s, remote_engine=%s",
            cached_choreography is not None,
            cached_music_prompt is not None,
            bool(settings.agent_engine_resource_name),
        )

        choreography: ChoreographySchema
        music_prompt: str
        audio_gcs_uri: str

        # If a remote Agent Runtime ReasoningEngine resource is configured:
        if settings.agent_engine_resource_name:
            choreography, music_prompt, audio_gcs_uri = self._run_remote_agent_runtime(
                video_gcs_uri=video_gcs_uri,
                user_preferences=user_preferences,
                cached_choreography=cached_choreography,
                cached_music_prompt=cached_music_prompt,
            )
        else:
            choreography, music_prompt, audio_gcs_uri = self._run_local_pipeline(
                video_gcs_uri=video_gcs_uri,
                video_mime_type=video_mime_type,
                user_preferences=user_preferences,
                cached_choreography=cached_choreography,
                cached_music_prompt=cached_music_prompt,
            )

        # Step 4: Deterministic FFmpeg combine on Cloud Run
        logger.info(
            "Executing Step 4: Combining video (%s) with audio (%s) via FFmpeg...",
            video_gcs_uri,
            audio_gcs_uri,
        )
        try:
            final_video_signed_url = combine_from_gcs(video_gcs_uri, audio_gcs_uri)
        except AgenticCinemaError:
            raise
        except Exception as exc:
            logger.error("FFmpeg combine failed: %s", exc, exc_info=True)
            raise MediaCombineError(
                f"Failed to combine video and audio: {exc}"
            ) from exc

        return AgentResult(
            choreography=choreography,
            music_prompt=music_prompt,
            audio_gcs_uri=audio_gcs_uri,
            final_video_signed_url=final_video_signed_url,
        )

    def _run_local_pipeline(
        self,
        video_gcs_uri: str,
        video_mime_type: str,
        user_preferences: UserPreferences,
        cached_choreography: dict | None,
        cached_music_prompt: str | None,
    ) -> tuple[ChoreographySchema, str, str]:
        """Execute the 3 AI steps using the ADK tools with strict error propagation."""

        # ── Step 1: Choreography Analysis ──
        if cached_choreography is not None:
            logger.info("Step 1: Using cached choreography analysis")
            try:
                choreography = ChoreographySchema.model_validate(cached_choreography)
            except Exception as exc:
                raise ChoreographyAnalysisError(
                    f"Invalid cached choreography data: {exc}"
                ) from exc
        else:
            logger.info("Step 1: Analyzing choreography with Gemini 3.8 Flash...")
            try:
                choreo_json_str = analyze_choreography_tool(
                    video_gcs_uri=video_gcs_uri,
                    mime_type=video_mime_type,
                )
                choreography = ChoreographySchema.model_validate_json(choreo_json_str)
            except AgenticCinemaError:
                raise
            except Exception as exc:
                logger.error("Choreography analysis error: %s", exc, exc_info=True)
                raise ChoreographyAnalysisError(
                    f"Video analysis failed: {exc}"
                ) from exc

        # ── Step 2: Music Planning ──
        if cached_music_prompt is not None and cached_choreography is not None:
            logger.info("Step 2: Using cached music plan")
            music_prompt = cached_music_prompt
        else:
            logger.info("Step 2: Planning music direction with Gemini 3.8 Flash...")
            try:
                music_prompt = plan_music_tool(
                    choreography_json=choreography.model_dump_json(),
                    style=user_preferences.style or "",
                    mood=user_preferences.mood or "",
                    energy=user_preferences.energy or "medium",
                    movement_feel=user_preferences.movement_feel or "",
                    output_type=user_preferences.output_type or "instrumental",
                    custom_instruction=user_preferences.custom_instruction or "",
                )
            except AgenticCinemaError:
                raise
            except Exception as exc:
                logger.error("Music planning error: %s", exc, exc_info=True)
                raise MusicPlanError(f"Music plan composition failed: {exc}") from exc

        # ── Step 3: Music Generation with Lyria 3.5 ──
        logger.info("Step 3: Generating music with Lyria 3.5 (Interactions API)...")
        try:
            audio_gcs_uri = generate_music_tool(
                music_prompt=music_prompt,
                duration_seconds=choreography.duration_seconds,
                bpm=choreography.movement_tempo_bpm,
                output_type=user_preferences.output_type,
            )
        except AgenticCinemaError:
            raise
        except Exception as exc:
            logger.error("Lyria generation error: %s", exc, exc_info=True)
            raise MusicGenerationError(f"Lyria music generation failed: {exc}") from exc

        return choreography, music_prompt, audio_gcs_uri

    def _run_remote_agent_runtime(
        self,
        video_gcs_uri: str,
        user_preferences: UserPreferences,
        cached_choreography: dict | None,
        cached_music_prompt: str | None,
    ) -> tuple[ChoreographySchema, str, str]:
        """Query the deployed Gemini Enterprise Agent Platform ReasoningEngine."""
        import asyncio

        import vertexai

        logger.info(
            "Connecting to Agent Runtime: %s", settings.agent_engine_resource_name
        )
        client = vertexai.Client(
            project=settings.google_cloud_project_id,
            location=settings.gcp_region,
        )
        remote_agent = client.agent_engines.get(
            name=settings.agent_engine_resource_name
        )

        input_message = {
            "video_gcs_uri": video_gcs_uri,
            "preferences": user_preferences.model_dump(),
            "cached_choreography": cached_choreography,
            "cached_music_prompt": cached_music_prompt,
        }

        async def _query() -> list[str]:
            response_chunks: list[str] = []
            async for event in remote_agent.async_stream_query(
                user_id="movescore_user",
                message=json.dumps(input_message),
            ):
                response_chunks.extend(_event_text_parts(event))
            return response_chunks

        response_chunks = asyncio.run(_query())
        logger.info(
            "Received Agent Runtime response (%d text chunks)", len(response_chunks)
        )

        try:
            data = _parse_remote_agent_payload(response_chunks)
            choreography = ChoreographySchema.model_validate(data["choreography_json"])
            music_prompt = data["music_prompt"]
            audio_gcs_uri = data["audio_gcs_uri"]
            return choreography, music_prompt, audio_gcs_uri
        except Exception as exc:
            logger.error("Failed to parse Agent Runtime output: %s", exc, exc_info=True)
            raise AgenticCinemaError(
                "Agent Runtime completed but returned an invalid structured response"
            ) from exc
