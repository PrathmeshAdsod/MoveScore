"""
Prompt 2 — Choreography to Music Plan

Takes the ChoreographySchema JSON + user preferences and produces
a timestamp-aware natural language music prompt for Lyria.
"""

from __future__ import annotations

from schemas.api import UserPreferences
from schemas.choreography import ChoreographySchema

_SYSTEM_PROMPT = """\
You are an expert music director who creates music for dance videos.
You have received a structured choreography analysis of a dance video.
Your job is to write a single, concise music generation prompt for an AI music composer.

RULES:
1. Translate the choreography's movement structure into musical structure.
2. Use timestamp markers in [MM:SS] or [S.S] format for key musical moments.
3. Map movement events to musical language:
   - accent / hit  → strong drum hit or musical accent
   - freeze        → brief silence, breath, or sustained note
   - buildup       → rising energy, expanding instrumentation
   - climax_start  → drop, high-energy section begins
   - spin          → swirling melodic or rhythmic transition element
   - final_pose    → strong, conclusive ending
4. Use "around [timestamp]" phrasing — these are musical directions, not sample-accurate sync guarantees.
5. Always mention: total duration, overall energy arc, style, mood, and instrumentation.
6. If movement_tempo_bpm is provided, include a BPM direction.
7. Keep under 300 words.
8. Output ONLY the music generation prompt text — no preamble, no explanation.

IMPORTANT: Do NOT use JSON. Write natural language that an AI music model can interpret.
"""


def build_music_plan_prompt(
    choreography: ChoreographySchema,
    preferences: UserPreferences,
) -> str:
    """Build the full prompt string to send to Gemini for music planning."""
    choreo_json = choreography.model_dump_json(indent=2)

    prefs_parts: list[str] = []
    if preferences.style:
        prefs_parts.append(f"Style: {preferences.style}")
    if preferences.mood:
        prefs_parts.append(f"Mood: {preferences.mood}")
    if preferences.energy:
        prefs_parts.append(f"Energy: {preferences.energy}")
    if preferences.movement_feel:
        prefs_parts.append(f"Movement Feel: {preferences.movement_feel}")
    if preferences.output_type:
        output_desc = (
            "Song with vocals" if preferences.output_type == "song" else "Instrumental only"
        )
        prefs_parts.append(f"Output: {output_desc}")
    if preferences.custom_instruction:
        prefs_parts.append(f"Custom instruction: {preferences.custom_instruction}")

    prefs_str = "\n".join(prefs_parts) if prefs_parts else "No specific preferences provided."

    return f"""{_SYSTEM_PROMPT}

---
CHOREOGRAPHY ANALYSIS:
{choreo_json}

---
CREATOR PREFERENCES:
{prefs_str}

---
Write the music generation prompt now:"""


def build_music_plan_prompt_from_dict(
    choreography_dict: dict,
    preferences: UserPreferences,
) -> str:
    """Build prompt from a raw dict (used when re-planning with cached choreography)."""
    choreography = ChoreographySchema.model_validate(choreography_dict)
    return build_music_plan_prompt(choreography, preferences)
