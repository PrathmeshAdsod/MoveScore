"""ADK agent tools — analyze choreography."""

from __future__ import annotations

from schemas.api import UserPreferences
from schemas.choreography import ChoreographySchema
from services import gemini_service


def analyze_choreography_tool(
    video_bytes: bytes,
    mime_type: str = "video/mp4",
) -> ChoreographySchema:
    """
    ADK Tool 1: Analyze choreography from a video.
    Uploads video to Gemini Files API, returns ChoreographySchema.
    """
    return gemini_service.analyze_choreography(video_bytes, mime_type=mime_type)
