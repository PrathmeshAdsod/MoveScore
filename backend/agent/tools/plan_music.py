"""ADK agent tools — plan music from choreography."""

from __future__ import annotations

import logging

from schemas.api import UserPreferences
from schemas.choreography import ChoreographySchema
from services import gemini_service

logger = logging.getLogger(__name__)


def plan_music_tool(
    choreography_json: str,
    style: str = "",
    mood: str = "",
    energy: str = "medium",
    movement_feel: str = "",
    output_type: str = "instrumental",
    custom_instruction: str = "",
) -> str:
    """
    ADK Tool 2: Generate a timestamp-aware music prompt from choreography JSON + creator preferences.
    Uses gemini-3.8-flash as the music director.
    Returns a natural language music prompt string for Lyria 3.5.
    """
    logger.info(
        "plan_music_tool called: style=%s, mood=%s, energy=%s",
        style,
        mood,
        energy,
    )
    choreography = ChoreographySchema.model_validate_json(choreography_json)
    preferences = UserPreferences(
        style=style or None,
        mood=mood or None,
        energy=energy or "medium",
        movement_feel=movement_feel or None,
        output_type=output_type or "instrumental",
        custom_instruction=custom_instruction or None,
    )
    return gemini_service.plan_music(choreography, preferences)
