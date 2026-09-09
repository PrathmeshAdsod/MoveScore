"""
FFmpeg Media Combine Service

Downloads video and audio from GCS to /tmp, combines them using FFmpeg,
uploads the result to GCS, and returns a signed URL.

The original video's length determines the output duration (-shortest flag).
The generated audio replaces (does not mix with) any original audio track.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from config import settings
from services import storage as gcs
from utils.errors import MediaCombineError

logger = logging.getLogger(__name__)


def _check_ffmpeg() -> None:
    """Verify ffmpeg is installed and accessible."""
    if shutil.which("ffmpeg") is None:
        raise MediaCombineError(
            "ffmpeg not found. Install ffmpeg (apt-get install -y ffmpeg) "
            "or ensure it is on the PATH."
        )


def combine_video_and_audio(
    video_gcs_uri: str,
    audio_local_path: Path,
) -> str:
    """
    Combine the original video with the generated audio track.

    - Downloads the original video from GCS to /tmp
    - Runs FFmpeg to replace the audio track
    - Uploads the final MP4 to GCS
    - Returns a signed URL for the final video

    Args:
        video_gcs_uri: GCS URI of the original dance video.
        audio_local_path: Local path to the generated MP3/audio file.

    Returns:
        Signed URL for the final combined video.
    """
    _check_ffmpeg()

    job_id = uuid.uuid4().hex[:8]
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"ac_{job_id}_"))

    try:
        video_path = tmp_dir / "input_video.mp4"
        output_path = tmp_dir / "output.mp4"

        # Download original video from GCS
        logger.info("Downloading original video from %s...", video_gcs_uri)
        gcs.download_to_file(video_gcs_uri, video_path)

        # Combine with FFmpeg
        logger.info("Running FFmpeg combine...")
        _run_ffmpeg(video_path, audio_local_path, output_path)

        # Upload final video to GCS
        final_blob_name = gcs.make_blob_name("final", "mp4")
        final_gcs_uri = gcs.upload_file(
            output_path, final_blob_name, content_type="video/mp4"
        )
        logger.info("Final video uploaded to %s", final_gcs_uri)

        # Generate signed URL
        signed_url = gcs.generate_signed_url(final_gcs_uri)
        return signed_url

    finally:
        # Clean up /tmp regardless of success or failure
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


def _run_ffmpeg(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
) -> None:
    """
    Run FFmpeg to combine video with audio.

    Strategy:
    - Take the video stream from the original video
    - Replace the audio stream with the generated audio
    - Use -shortest to match the shorter of the two streams
    - Re-encode audio to AAC for broad compatibility
    - Copy video stream to avoid re-encoding (faster)
    """
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output without prompting
        "-i", str(video_path),  # Input 1: original video
        "-i", str(audio_path),  # Input 2: generated audio
        "-map", "0:v:0",        # Take video stream from input 0
        "-map", "1:a:0",        # Take audio stream from input 1
        "-c:v", "copy",         # Copy video stream (no re-encode)
        "-c:a", "aac",          # Encode audio as AAC
        "-b:a", "192k",         # Audio bitrate
        "-shortest",            # Output duration = shorter of the two inputs
        "-movflags", "+faststart",  # Optimize for web streaming
        str(output_path),
    ]

    logger.debug("FFmpeg command: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout for FFmpeg
        )

        if result.returncode != 0:
            logger.error("FFmpeg stderr: %s", result.stderr)
            raise MediaCombineError(
                f"FFmpeg exited with code {result.returncode}. "
                f"Error: {result.stderr[-500:]}"
            )

        logger.info("FFmpeg combine complete: %s", output_path)

    except subprocess.TimeoutExpired as exc:
        raise MediaCombineError("FFmpeg timed out after 120 seconds") from exc


def combine_from_gcs(
    video_gcs_uri: str,
    audio_gcs_uri: str,
) -> str:
    """
    Combine video and audio, both sourced from GCS.
    Downloads audio to /tmp, then calls combine_video_and_audio.

    Returns signed URL for the final video.
    """
    _check_ffmpeg()

    job_id = uuid.uuid4().hex[:8]
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"ac_dl_{job_id}_"))

    try:
        audio_path = tmp_dir / "generated_audio.mp3"
        gcs.download_to_file(audio_gcs_uri, audio_path)
        return combine_video_and_audio(video_gcs_uri, audio_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
