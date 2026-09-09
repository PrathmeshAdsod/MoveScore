"""ADK agent tools — plan music from choreography."""

from __future__ import annotations

from schemas.api import UserPreferences
from schemas.choreography import ChoreographySchema
from services import gemini_service


def plan_music_tool(
    choreography: ChoreographySchema,
    preferences: UserPreferences,
) -> str:
    """
    ADK Tool 2: Generate a timestamp-aware music prompt from choreography + user prefs.
    Returns a natural language music prompt string for Lyria.
    """
    return gemini_service.plan_music(choreography, preferences)
