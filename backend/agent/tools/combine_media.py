"""ADK agent tools — combine video and audio with FFmpeg."""

from __future__ import annotations

from services.ffmpeg_service import combine_from_gcs


def combine_media_tool(
    video_gcs_uri: str,
    audio_gcs_uri: str,
) -> str:
    """
    ADK Tool 4: Combine original video + generated audio, return signed URL.

    Args:
        video_gcs_uri: GCS URI of the original dance video.
        audio_gcs_uri: GCS URI of the generated audio MP3.

    Returns:
        Signed URL for the final combined MP4 video.
    """
    return combine_from_gcs(video_gcs_uri, audio_gcs_uri)
