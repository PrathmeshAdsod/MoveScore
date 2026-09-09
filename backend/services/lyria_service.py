"""
Lyria Music Generation Service

Calls Lyria via the Gemini Live Music API (google-genai v2+ SDK).
Uses the async music session to stream audio chunks.

Reference: https://ai.google.dev/gemini-api/docs/music-generation
API class: google.genai.live.AsyncLiveMusic / AsyncMusicSession

Key facts (verified from SDK):
- Uses client.aio.live.music.connect(model=LYRIA_MODEL) — async websocket session
- set_weighted_prompts(): send text prompts with weights
- set_music_generation_config(): set BPM, density, brightness, scale, mode
- play(): start generation
- receive(): async iterator yielding LiveMusicServerMessage
- Audio arrives in AudioChunk.data (raw PCM bytes)
- music_generation_mode: VOCALIZATION for vocals, QUALITY/DIVERSITY for instrumental
"""

from __future__ import annotations

import asyncio
import io
import logging
import struct
import wave
from pathlib import Path

from google import genai
from google.genai import types

from config import settings
from utils.errors import MusicGenerationError

logger = logging.getLogger(__name__)

# Lyria audio output parameters (verified from SDK examples)
AUDIO_SAMPLE_RATE = 48000  # 48 kHz
AUDIO_CHANNELS = 2          # Stereo
AUDIO_SAMPLE_WIDTH = 2      # 16-bit PCM = 2 bytes per sample

# Maximum audio collection time (safety limit)
MAX_COLLECTION_SECS = 120.0


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
    Generate music using Lyria via the Gemini Live Music API.

    Args:
        music_prompt: Natural language music description with timestamp markers.
        duration_seconds: Target duration in seconds (from choreography analysis).
        output_path: Local path where the WAV file will be saved.
        bpm: Optional BPM override (from movement_tempo_bpm).
        output_type: 'instrumental' or 'song' (song uses VOCALIZATION mode).

    Returns:
        The output_path where the WAV was saved.

    Raises:
        MusicGenerationError: If generation fails.
    """
    # Clamp duration
    target_secs = max(5.0, min(float(duration_seconds), 60.0))

    logger.info(
        "Generating music with Lyria (model: %s, target: %.1fs, mode: %s)...",
        settings.lyria_model,
        target_secs,
        output_type,
    )

    try:
        # Run the async generation in a new event loop
        audio_data = asyncio.run(
            _generate_async(
                music_prompt=music_prompt,
                target_secs=target_secs,
                bpm=bpm,
                output_type=output_type,
            )
        )
    except MusicGenerationError:
        raise
    except Exception as exc:
        error_msg = str(exc)
        if "quota" in error_msg.lower():
            raise MusicGenerationError(
                "Lyria quota exceeded. Check your Google Cloud quota settings."
            ) from exc
        if "not found" in error_msg.lower() or "404" in error_msg.lower():
            raise MusicGenerationError(
                f"Lyria model '{settings.lyria_model}' not found. "
                "Verify the model ID in your Google AI Studio account."
            ) from exc
        raise MusicGenerationError(f"Lyria generation failed: {error_msg}") from exc

    if not audio_data:
        raise MusicGenerationError(
            "Lyria returned no audio data. "
            "Check model availability and content policy."
        )

    # Save as WAV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _save_as_wav(audio_data, output_path)

    logger.info(
        "Music generated: %s (%d bytes, %.1fs)",
        output_path,
        output_path.stat().st_size,
        target_secs,
    )
    return output_path


async def _generate_async(
    music_prompt: str,
    target_secs: float,
    bpm: int | None,
    output_type: str,
) -> bytes:
    """
    Async implementation of Lyria music generation.
    Connects to the Live Music API, streams audio chunks, returns raw PCM bytes.
    """
    client = _get_client()

    # Determine generation mode
    if output_type == "song":
        mode = types.MusicGenerationMode.VOCALIZATION
    else:
        mode = types.MusicGenerationMode.QUALITY

    # Build generation config
    gen_config = types.LiveMusicGenerationConfig(
        music_generation_mode=mode,
    )
    if bpm:
        gen_config.bpm = float(bpm)

    # Calculate how many bytes we need for target duration
    # PCM: sample_rate * channels * sample_width * duration
    target_bytes = int(AUDIO_SAMPLE_RATE * AUDIO_CHANNELS * AUDIO_SAMPLE_WIDTH * target_secs)
    collected_bytes = bytearray()

    logger.debug(
        "Lyria async: model=%s, target_bytes=%d, mode=%s",
        settings.lyria_model,
        target_bytes,
        mode,
    )

    async with client.aio.live.music.connect(model=settings.lyria_model) as session:
        # Send the music prompt
        await session.set_weighted_prompts(
            prompts=[types.WeightedPrompt(text=music_prompt, weight=1.0)]
        )

        # Set generation config
        await session.set_music_generation_config(config=gen_config)

        # Start playback
        await session.play()

        # Collect audio chunks until we have enough data
        async for message in session.receive():
            if message.server_content and message.server_content.audio_chunks:
                for chunk in message.server_content.audio_chunks:
                    if chunk.data:
                        collected_bytes.extend(chunk.data)
                        collected_secs = len(collected_bytes) / (
                            AUDIO_SAMPLE_RATE * AUDIO_CHANNELS * AUDIO_SAMPLE_WIDTH
                        )
                        logger.debug(
                            "Collected %.1f / %.1f seconds of audio",
                            collected_secs,
                            target_secs,
                        )

                        if collected_secs >= target_secs:
                            await session.stop()
                            break

            if len(collected_bytes) >= target_bytes:
                break

    # Trim to exact target duration
    if len(collected_bytes) > target_bytes:
        collected_bytes = collected_bytes[:target_bytes]

    return bytes(collected_bytes)


def _save_as_wav(pcm_data: bytes, output_path: Path) -> None:
    """Save raw PCM audio data as a WAV file."""
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(AUDIO_CHANNELS)
        wav_file.setsampwidth(AUDIO_SAMPLE_WIDTH)
        wav_file.setframerate(AUDIO_SAMPLE_RATE)
        wav_file.writeframes(pcm_data)
