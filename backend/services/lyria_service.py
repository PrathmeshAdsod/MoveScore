"""
Lyria 3.5 Music Generation Service

Uses the Gemini Interactions API (google-genai v2+ SDK) for music generation.

Lyria 3.5 is NOT a real-time/live API. It uses the standard Interactions API:
    client.interactions.create(model="lyria-3.5", input="<prompt>", ...)

Output: audio/mp3 (44.1 kHz stereo), returned as base64-encoded bytes in
interaction.output_audio.data

Reference: https://ai.google.dev/gemini-api/docs/music-generation
Model: lyria-3.5

IMPORTANT: Do NOT confuse with Lyria RealTime (live.music.connect) which is a
completely different WebSocket-based streaming API. MoveScore uses Lyria 3.5
via the standard Interactions API only.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path

from google import genai

from config import settings
from utils.errors import MusicGenerationError

logger = logging.getLogger(__name__)

# Lyria 3.5 output format (via Interactions API)
AUDIO_MIME_TYPE = "audio/mp3"
AUDIO_EXTENSION = ".mp3"


def _get_client() -> genai.Client:
    """Return a configured google-genai client using the Gemini API key."""
    return genai.Client(api_key=settings.gemini_api_key)


def generate_music(
    music_prompt: str,
    duration_seconds: float,
    output_path: Path,
    bpm: int | None = None,
    output_type: str = "instrumental",
) -> Path:
    """
    Generate music using Lyria 3.5 via the Gemini Interactions API.

    The music prompt should be a natural language description with timestamp
    markers like "around 0:03 strong accent", "around 0:10 freeze moment".
    These are musical directions for the AI — not sample-accurate sync
    guarantees.

    Args:
        music_prompt: Natural language music description with timestamp markers.
        duration_seconds: Target duration in seconds (from choreography analysis).
        output_path: Local path where the MP3 file will be saved.
        bpm: Optional BPM hint (included in the prompt as a musical direction).
        output_type: 'instrumental' or 'song' (song allows vocal generation).

    Returns:
        The output_path where the MP3 was saved.

    Raises:
        MusicGenerationError: If generation fails.
    """
    # Clamp duration
    target_secs = max(5.0, min(float(duration_seconds), 60.0))

    # Build the full prompt with duration, BPM, and output type context
    full_prompt = _build_full_prompt(music_prompt, target_secs, bpm, output_type)

    logger.info(
        "Generating music with Lyria 3.5 (model: %s, target: %.1fs, mode: %s)...",
        settings.lyria_model,
        target_secs,
        output_type,
    )
    logger.debug("Full Lyria prompt (%d chars): %s", len(full_prompt), full_prompt[:300])

    client = _get_client()

    try:
        interaction = client.interactions.create(
            model=settings.lyria_model,
            input=full_prompt,
        )
    except Exception as exc:
        error_msg = str(exc)
        if "quota" in error_msg.lower():
            raise MusicGenerationError(
                "Lyria quota exceeded. Check your Google Cloud quota settings."
            ) from exc
        if "not found" in error_msg.lower() or "404" in error_msg.lower():
            raise MusicGenerationError(
                f"Lyria model '{settings.lyria_model}' not found. "
                "Verify the model ID and ensure your API key has Lyria 3.5 access."
            ) from exc
        if "permission" in error_msg.lower() or "403" in error_msg.lower():
            raise MusicGenerationError(
                "Lyria 3.5 permission denied. "
                "Verify your API key has access to Lyria 3.5 at ai.google.dev"
            ) from exc
        raise MusicGenerationError(f"Lyria generation failed: {error_msg}") from exc

    # Extract audio from the interaction response
    audio = interaction.output_audio
    if audio is None or audio.data is None:
        raise MusicGenerationError(
            "Lyria returned no audio data. "
            "Check model availability, content policy, and API key access."
        )

    # audio.data is a Base64EncodedString — decode to raw bytes
    if isinstance(audio.data, str):
        audio_bytes = base64.b64decode(audio.data)
    else:
        # Already decoded by SDK
        audio_bytes = bytes(audio.data)

    if len(audio_bytes) == 0:
        raise MusicGenerationError(
            "Lyria returned empty audio data. Check content policy and prompt."
        )

    # Save the MP3
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(audio_bytes)

    logger.info(
        "Music generated: %s (%.1f KB, mime=%s)",
        output_path,
        len(audio_bytes) / 1024,
        audio.mime_type or AUDIO_MIME_TYPE,
    )
    return output_path


def _build_full_prompt(
    music_prompt: str,
    duration_secs: float,
    bpm: int | None,
    output_type: str,
) -> str:
    """
    Build the complete Lyria prompt from the music plan.

    Lyria 3.5 understands natural language music descriptions with approximate
    timestamp markers. We include:
    - The choreography-derived music plan (already has timestamps)
    - Duration direction
    - BPM direction if available
    - Output type (instrumental vs vocals)

    Note: These timestamp markers are musical directions, not sync guarantees.
    """
    parts = [music_prompt.strip()]

    # Ensure duration is mentioned if not already in the prompt
    duration_str = f"{duration_secs:.0f} seconds"
    if duration_str not in music_prompt and "second" not in music_prompt.lower():
        parts.append(f"Total duration: approximately {duration_str}.")

    if bpm and "bpm" not in music_prompt.lower():
        parts.append(f"Suggested tempo: approximately {bpm} BPM.")

    if output_type == "instrumental" and "instrumental" not in music_prompt.lower():
        parts.append("Instrumental only — no lyrics, no vocals.")
    elif output_type == "song" and "vocal" not in music_prompt.lower():
        parts.append("Include melodic vocal phrasing (song mode).")

    return " ".join(parts)
