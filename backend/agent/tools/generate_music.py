"""Agent tool — generate music with Lyria 3.5."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Optional

from services import lyria_service
from services import storage as gcs


def generate_music_tool(
    music_prompt: str,
    duration_seconds: float,
    bpm: Optional[int] = None,
    output_type: str = "instrumental",
) -> str:
    """
    Tool 3: Generate music with Lyria 3.5, upload MP3 to GCS, return GCS URI.

    Uses the Gemini Interactions API (client.interactions.create) to generate
    music from a natural-language, timestamp-aware music prompt.

    Output format: MP3 (audio/mpeg), from Lyria 3.5 standard generation.
    NOT the Lyria RealTime/Live API.

    Args:
        music_prompt: Timestamp-aware music prompt from plan_music.
        duration_seconds: Target duration (from choreography analysis).
        bpm: Optional BPM hint from movement_tempo_bpm.
        output_type: 'instrumental' or 'song'.

    Returns:
        GCS URI of the generated MP3 audio file.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="ms_lyria_"))
    # Lyria 3.5 Interactions API returns MP3
    audio_path = tmp_dir / f"generated_{uuid.uuid4().hex[:8]}.mp3"

    try:
        lyria_service.generate_music(
            music_prompt,
            duration_seconds,
            audio_path,
            bpm=bpm,
            output_type=output_type,
        )

        # Upload MP3 to GCS
        blob_name = gcs.make_blob_name("audio", "mp3")
        audio_gcs_uri = gcs.upload_file(
            audio_path, blob_name, content_type="audio/mpeg"
        )
        return audio_gcs_uri

    finally:
        # Clean up temp file
        try:
            if audio_path.exists():
                audio_path.unlink()
            tmp_dir.rmdir()
        except Exception:
            pass
