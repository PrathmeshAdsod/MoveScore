"""
Unit tests for ChoreographySchema.

Tests Pydantic validation, to_ui_summary(), and edge cases.
No API calls — pure schema logic.
"""

from __future__ import annotations

import pytest

from schemas.choreography import (
    ChoreographySchema,
    EnergyLevel,
    MoveType,
)


def _make_minimal_choreography(**overrides) -> dict:
    """Return the minimal valid ChoreographySchema dict."""
    base = {
        "duration_seconds": 15.0,
        "overall_energy": "high",
        "movement_tempo_bpm": 110,
        "segments": [
            {
                "start_sec": 0.0,
                "end_sec": 15.0,
                "label": "full_sequence",
                "description": "continuous dance routine",
                "energy": "high",
                "move_type": "sequence",
                "intensity": 7,
            }
        ],
        "key_moments": [
            {"time_sec": 3.0, "type": "accent", "note": "chest pop"},
            {"time_sec": 10.0, "type": "freeze", "note": "full stop"},
            {"time_sec": 15.0, "type": "final_pose", "note": "held pose"},
        ],
        "movement_patterns": {
            "repeated_motifs": [],
            "dominant_style": "hip-hop",
            "has_buildup": False,
            "has_drop": True,
            "has_freeze": True,
            "has_final_pose": True,
        },
        "analysis_confidence": "high",
        "analysis_notes": "Clear video, good lighting.",
    }
    base.update(overrides)
    return base


class TestChoreographySchemaValidation:
    def test_valid_schema_parses(self) -> None:
        data = _make_minimal_choreography()
        schema = ChoreographySchema.model_validate(data)
        assert schema.duration_seconds == 15.0
        assert schema.overall_energy == EnergyLevel.high
        assert schema.movement_tempo_bpm == 110
        assert len(schema.key_moments) == 3

    def test_null_bpm_is_valid(self) -> None:
        data = _make_minimal_choreography(movement_tempo_bpm=None)
        schema = ChoreographySchema.model_validate(data)
        assert schema.movement_tempo_bpm is None

    def test_intensity_range_valid(self) -> None:
        data = _make_minimal_choreography()
        data["segments"][0]["intensity"] = 1
        ChoreographySchema.model_validate(data)
        data["segments"][0]["intensity"] = 10
        ChoreographySchema.model_validate(data)

    def test_intensity_out_of_range_fails(self) -> None:
        data = _make_minimal_choreography()
        data["segments"][0]["intensity"] = 0  # below minimum
        with pytest.raises(Exception):
            ChoreographySchema.model_validate(data)

        data["segments"][0]["intensity"] = 11  # above maximum
        with pytest.raises(Exception):
            ChoreographySchema.model_validate(data)

    def test_invalid_move_type_fails(self) -> None:
        data = _make_minimal_choreography()
        data["key_moments"][0]["type"] = "moonwalk"  # not in enum
        with pytest.raises(Exception):
            ChoreographySchema.model_validate(data)

    def test_all_move_types_valid(self) -> None:
        for mt in MoveType:
            data = _make_minimal_choreography()
            data["key_moments"][0]["type"] = mt.value
            ChoreographySchema.model_validate(data)

    def test_json_round_trip(self) -> None:
        data = _make_minimal_choreography()
        schema = ChoreographySchema.model_validate(data)
        json_str = schema.model_dump_json()
        schema2 = ChoreographySchema.model_validate_json(json_str)
        assert schema.duration_seconds == schema2.duration_seconds
        assert len(schema.key_moments) == len(schema2.key_moments)

    def test_empty_key_moments_valid(self) -> None:
        data = _make_minimal_choreography()
        data["key_moments"] = []
        schema = ChoreographySchema.model_validate(data)
        assert schema.key_moments == []


class TestUiSummary:
    def test_summary_has_expected_keys(self) -> None:
        schema = ChoreographySchema.model_validate(_make_minimal_choreography())
        summary = schema.to_ui_summary()
        assert "moment_count" in summary
        assert "moment_labels" in summary
        assert "duration_seconds" in summary
        assert "overall_energy" in summary
        assert "analysis_confidence" in summary
        assert "low_confidence_warning" in summary

    def test_summary_moment_count(self) -> None:
        schema = ChoreographySchema.model_validate(_make_minimal_choreography())
        summary = schema.to_ui_summary()
        assert summary["moment_count"] == 3

    def test_summary_labels_are_human_readable(self) -> None:
        schema = ChoreographySchema.model_validate(_make_minimal_choreography())
        summary = schema.to_ui_summary()
        labels = summary["moment_labels"]
        # accent → Hit, freeze → Freeze, final_pose → Final Pose
        assert "Hit" in labels
        assert "Freeze" in labels
        assert "Final Pose" in labels

    def test_low_confidence_warning_flag(self) -> None:
        data = _make_minimal_choreography(analysis_confidence="low")
        schema = ChoreographySchema.model_validate(data)
        summary = schema.to_ui_summary()
        assert summary["low_confidence_warning"] is True

    def test_high_confidence_no_warning(self) -> None:
        schema = ChoreographySchema.model_validate(_make_minimal_choreography())
        summary = schema.to_ui_summary()
        assert summary["low_confidence_warning"] is False

    def test_duplicate_labels_deduplicated(self) -> None:
        data = _make_minimal_choreography()
        # Add two accents — should only appear once in labels
        data["key_moments"] = [
            {"time_sec": 2.0, "type": "accent", "note": "first hit"},
            {"time_sec": 5.0, "type": "accent", "note": "second hit"},
        ]
        schema = ChoreographySchema.model_validate(data)
        summary = schema.to_ui_summary()
        assert summary["moment_labels"].count("Hit") == 1
