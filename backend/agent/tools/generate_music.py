"""ADK agent tools — generate music with Lyria."""

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
    ADK Tool 3: Generate music with Lyria, upload WAV to GCS, return GCS URI.

    Args:
        music_prompt: Timestamp-aware music prompt from plan_music.
        duration_seconds: Target duration (from choreography analysis).
        bpm: Optional BPM from movement_tempo_bpm.
        output_type: 'instrumental' or 'song'.

    Returns:
        GCS URI of the generated WAV audio file.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="ac_lyria_"))
    audio_path = tmp_dir / f"generated_{uuid.uuid4().hex[:8]}.wav"

    try:
        lyria_service.generate_music(
            music_prompt,
            duration_seconds,
            audio_path,
            bpm=bpm,
            output_type=output_type,
        )

        # Upload to GCS (WAV format)
        blob_name = gcs.make_blob_name("audio", "wav")
        audio_gcs_uri = gcs.upload_file(
            audio_path, blob_name, content_type="audio/wav"
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
