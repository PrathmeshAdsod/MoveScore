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

from services import storage as gcs
from utils.errors import InvalidVideoDurationError, MediaCombineError

logger = logging.getLogger(__name__)


def _check_ffmpeg() -> None:
    """Verify ffmpeg and ffprobe are installed and accessible."""
    if shutil.which("ffmpeg") is None:
        raise MediaCombineError(
            "ffmpeg not found. Install ffmpeg (apt-get install -y ffmpeg) "
            "or ensure it is on the PATH."
        )


def _check_ffprobe() -> None:
    """Verify ffprobe is installed and accessible."""
    if shutil.which("ffprobe") is None:
        raise MediaCombineError(
            "ffprobe not found. Install ffmpeg (apt-get install -y ffmpeg) "
            "or ensure it is on the PATH."
        )


def get_video_duration(video_path: Path) -> float:
    """
    Use ffprobe to determine the duration of a video file in seconds.
    """
    _check_ffprobe()
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("ffprobe error: %s", result.stderr)
            raise MediaCombineError(f"Could not probe video duration: {result.stderr.strip()}")
        output = result.stdout.strip()
        if not output:
            raise MediaCombineError("ffprobe returned empty duration output.")
        return float(output)
    except subprocess.TimeoutExpired as exc:
        raise MediaCombineError("ffprobe timed out reading video metadata") from exc
    except ValueError as exc:
        raise MediaCombineError(f"Invalid duration value from ffprobe: {exc}") from exc


def validate_video_duration(video_path: Path, max_duration_sec: float = 60.0) -> float:
    """
    Validate that video duration does not exceed max_duration_sec.
    Raises InvalidVideoDurationError if exceeded.
    """
    duration = get_video_duration(video_path)
    if duration > max_duration_sec:
        raise InvalidVideoDurationError(duration_sec=duration, max_sec=max_duration_sec)
    return duration


def combine_video_and_audio(
    video_gcs_uri: str,
    audio_local_path: Path,
) -> str:
    """
    Combine the original video with the generated audio track.

    - Downloads the original video from GCS to /tmp
    - Validates duration
    - Runs FFmpeg with H.264/yuv420p + AAC for universal browser playback
    - Uploads the final MP4 to GCS
    - Returns a signed URL for the final video
    """
    _check_ffmpeg()

    job_id = uuid.uuid4().hex[:8]
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"ac_{job_id}_"))

    try:
        video_path = tmp_dir / "input_video"
        output_path = tmp_dir / "output.mp4"

        # Download original video from GCS
        logger.info("Downloading original video from %s...", video_gcs_uri)
        gcs.download_to_file(video_gcs_uri, video_path)

        # Validate duration before combining
        duration = validate_video_duration(video_path, max_duration_sec=60.0)
        logger.info("Input video duration verified: %.2fs", duration)

        # Combine with FFmpeg
        logger.info("Running FFmpeg combine with safe H.264 transcode...")
        _run_ffmpeg(video_path, audio_local_path, output_path)

        # Upload final video to GCS
        final_blob_name = gcs.make_blob_name("final", "mp4")
        final_gcs_uri = gcs.upload_file(output_path, final_blob_name, content_type="video/mp4")
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
    - Transcode video to standard H.264 (yuv420p) for universal browser support
      across MP4, WebM (VP8/VP9/AV1), and MOV (ProRes/H.265) inputs
    - Re-encode audio to AAC for broad compatibility
    - movflags +faststart for immediate web streaming
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    logger.debug("FFmpeg command: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,  # 3 minute timeout for FFmpeg encode
        )

        if result.returncode != 0:
            logger.error("FFmpeg stderr: %s", result.stderr)
            raise MediaCombineError(
                f"FFmpeg exited with code {result.returncode}. " f"Error: {result.stderr[-500:]}"
            )

        logger.info("FFmpeg combine complete: %s", output_path)

    except subprocess.TimeoutExpired as exc:
        raise MediaCombineError("FFmpeg timed out after 180 seconds") from exc


def combine_from_gcs(
    video_gcs_uri: str,
    audio_gcs_uri: str,
) -> str:
    """
    Combine video and audio, both sourced from GCS.
    Downloads the Lyria 3.5 MP3 audio to /tmp, combines with video.

    Returns signed URL for the final combined video.
    """
    _check_ffmpeg()

    job_id = uuid.uuid4().hex[:8]
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"ms_combine_{job_id}_"))

    try:
        # Lyria 3.5 generates MP3 via the Interactions API
        audio_path = tmp_dir / "generated_audio.mp3"
        gcs.download_to_file(audio_gcs_uri, audio_path)
        return combine_video_and_audio(video_gcs_uri, audio_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
