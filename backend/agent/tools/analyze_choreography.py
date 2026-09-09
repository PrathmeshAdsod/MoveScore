"""ADK agent tools — analyze choreography."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from services import gemini_service
from services import storage as gcs

logger = logging.getLogger(__name__)


def analyze_choreography_tool(
    video_gcs_uri: str,
    mime_type: str = "video/mp4",
) -> str:
    """
    ADK Tool 1: Analyze choreography from a dance video in GCS.
    Downloads video from video_gcs_uri, uploads to Gemini Files API,
    and analyzes with gemini-3.8-flash.
    Returns JSON string of ChoreographySchema.
    """
    logger.info("analyze_choreography_tool called with URI: %s", video_gcs_uri)
    fd, tmp_str = tempfile.mkstemp(suffix=".mp4")
    tmp_path = Path(tmp_str)
    os.close(fd)
    try:
        gcs.download_to_file(video_gcs_uri, tmp_path)
        video_bytes = tmp_path.read_bytes()
        schema = gemini_service.analyze_choreography(video_bytes, mime_type=mime_type)
        return schema.model_dump_json()
    finally:
        tmp_path.unlink(missing_ok=True)
