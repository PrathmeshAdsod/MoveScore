"""
ChoreographySchema — Pydantic models for Gemini structured output.

This schema defines what Gemini must return after analyzing a dance video.
It is also used as the response_schema for strict JSON enforcement.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# Agent Runtime currently executes Python 3.10, where StrEnum is unavailable.
class MoveType(str, Enum):  # noqa: UP042
    entrance = "entrance"
    accent = "accent"
    transition = "transition"
    spin = "spin"
    jump = "jump"
    freeze = "freeze"
    pose = "pose"
    sequence = "sequence"
    buildup = "buildup"
    climax_start = "climax_start"
    cooldown = "cooldown"
    final_pose = "final_pose"


class EnergyLevel(str, Enum):  # noqa: UP042
    low = "low"
    medium = "medium"
    high = "high"


class AnalysisConfidence(str, Enum):  # noqa: UP042
    high = "high"
    medium = "medium"
    low = "low"


class Segment(BaseModel):
    """A continuous movement segment within the dance."""

    start_sec: float = Field(..., description="Segment start time in seconds")
    end_sec: float = Field(..., description="Segment end time in seconds")
    label: str = Field(..., description="Short label for this segment")
    description: str = Field(..., description="Describe only clearly visible movements")
    energy: EnergyLevel
    move_type: MoveType
    intensity: int = Field(..., ge=1, le=10, description="1=stillness, 10=max exertion")


class KeyMoment(BaseModel):
    """A discrete important movement event."""

    time_sec: float = Field(..., description="Timestamp in seconds")
    type: MoveType
    note: str = Field(..., description="Brief description of what happens")


class MovementPatterns(BaseModel):
    repeated_motifs: list[str] = Field(
        default_factory=list,
        description="Describe any movement patterns that repeat",
    )
    dominant_style: str = Field(
        ..., description="Overall movement style (e.g. hip-hop, contemporary)"
    )
    has_buildup: bool = False
    has_drop: bool = False
    has_freeze: bool = False
    has_final_pose: bool = False


class ChoreographySchema(BaseModel):
    """
    Complete structured analysis of a dance video.
    Returned by Gemini after multimodal video analysis.
    """

    duration_seconds: float = Field(..., description="Total video duration in seconds")
    overall_energy: EnergyLevel
    movement_tempo_bpm: int | None = Field(
        None,
        description=(
            "Estimated tempo inferred from observed movement rhythm. "
            "NOT a song BPM — there may be no music. "
            "Set null if rhythm is unclear."
        ),
    )
    segments: list[Segment] = Field(
        ..., description="Ordered list of movement segments covering the whole video"
    )
    key_moments: list[KeyMoment] = Field(
        ..., description="Discrete important events (accents, spins, freezes, etc.)"
    )
    movement_patterns: MovementPatterns
    analysis_confidence: AnalysisConfidence
    analysis_notes: str = Field(
        ...,
        description=(
            "Any notes about video quality, unclear sections, "
            "or fast movements that could not be fully analyzed"
        ),
    )

    def to_ui_summary(self) -> dict:
        """Compact summary for the frontend UI — does NOT expose raw JSON."""
        moment_labels: list[str] = []
        label_map = {
            "entrance": "Intro",
            "accent": "Hit",
            "spin": "Spin",
            "jump": "Jump",
            "freeze": "Freeze",
            "buildup": "Buildup",
            "climax_start": "Drop",
            "final_pose": "Final Pose",
            "pose": "Pose",
            "transition": "Transition",
            "sequence": "Sequence",
            "cooldown": "Cooldown",
        }
        for km in self.key_moments:
            mapped = label_map.get(
                km.type.value, km.type.value.replace("_", " ").title()
            )
            if mapped not in moment_labels:
                moment_labels.append(mapped)

        return {
            "moment_count": len(self.key_moments),
            "moment_labels": moment_labels,
            "duration_seconds": self.duration_seconds,
            "overall_energy": self.overall_energy.value,
            "movement_tempo_bpm": self.movement_tempo_bpm,
            "analysis_confidence": self.analysis_confidence.value,
            "low_confidence_warning": self.analysis_confidence
            == AnalysisConfidence.low,
        }
