"""
Unit tests for music plan prompt builder.

Tests the prompt construction logic without making any API calls.
"""

from __future__ import annotations

from schemas.api import UserPreferences
from schemas.choreography import ChoreographySchema
from prompts.music_plan import build_music_plan_prompt, build_music_plan_prompt_from_dict


def _make_choreography() -> ChoreographySchema:
    return ChoreographySchema.model_validate(
        {
            "duration_seconds": 18.0,
            "overall_energy": "high",
            "movement_tempo_bpm": 120,
            "segments": [
                {
                    "start_sec": 0.0,
                    "end_sec": 18.0,
                    "label": "routine",
                    "description": "full dance routine",
                    "energy": "high",
                    "move_type": "sequence",
                    "intensity": 7,
                }
            ],
            "key_moments": [
                {"time_sec": 3.0, "type": "accent", "note": "chest pop"},
                {"time_sec": 10.0, "type": "freeze", "note": "full stop"},
                {"time_sec": 18.0, "type": "final_pose", "note": "held pose"},
            ],
            "movement_patterns": {
                "repeated_motifs": [],
                "dominant_style": "hip-hop",
                "has_buildup": True,
                "has_drop": True,
                "has_freeze": True,
                "has_final_pose": True,
            },
            "analysis_confidence": "high",
            "analysis_notes": "Clear video.",
        }
    )


def _make_prefs(**kwargs) -> UserPreferences:
    defaults = {
        "output_type": "instrumental",
        "style": "Afrobeat",
        "mood": "Euphoric",
        "energy": "high",
        "movement_feel": "Groovy",
    }
    defaults.update(kwargs)
    return UserPreferences(**defaults)


class TestMusicPlanPrompt:
    def test_prompt_is_nonempty(self) -> None:
        prompt = build_music_plan_prompt(_make_choreography(), _make_prefs())
        assert len(prompt) > 100

    def test_prompt_contains_style(self) -> None:
        prompt = build_music_plan_prompt(_make_choreography(), _make_prefs(style="Amapiano"))
        assert "Amapiano" in prompt

    def test_prompt_contains_mood(self) -> None:
        prompt = build_music_plan_prompt(_make_choreography(), _make_prefs(mood="Melancholic"))
        assert "Melancholic" in prompt

    def test_prompt_contains_energy(self) -> None:
        prompt = build_music_plan_prompt(_make_choreography(), _make_prefs(energy="soft"))
        assert "soft" in prompt.lower()

    def test_prompt_contains_custom_instruction(self) -> None:
        prompt = build_music_plan_prompt(
            _make_choreography(),
            _make_prefs(custom_instruction="Make the freeze dramatic."),
        )
        assert "dramatic" in prompt.lower()

    def test_song_output_mentioned(self) -> None:
        prompt = build_music_plan_prompt(_make_choreography(), _make_prefs(output_type="song"))
        assert "vocal" in prompt.lower() or "song" in prompt.lower()

    def test_instrumental_output_mentioned(self) -> None:
        prompt = build_music_plan_prompt(_make_choreography(), _make_prefs(output_type="instrumental"))
        assert "instrumental" in prompt.lower()

    def test_no_preferences_handled(self) -> None:
        prefs = UserPreferences()  # all optional, none set
        prompt = build_music_plan_prompt(_make_choreography(), prefs)
        assert len(prompt) > 50  # still builds a prompt

    def test_from_dict_equivalent(self) -> None:
        choreo = _make_choreography()
        prefs = _make_prefs()
        prompt_from_obj = build_music_plan_prompt(choreo, prefs)
        prompt_from_dict = build_music_plan_prompt_from_dict(choreo.model_dump(), prefs)
        assert prompt_from_obj == prompt_from_dict

    def test_bpm_included_when_present(self) -> None:
        prompt = build_music_plan_prompt(_make_choreography(), _make_prefs())
        # BPM 120 should appear somewhere in the system prompt injection
        assert "120" in prompt or "bpm" in prompt.lower() or "tempo" in prompt.lower()
