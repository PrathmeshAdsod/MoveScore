"""
Pydantic models for API request/response contracts.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    """Creative preferences selected by the user in the UI."""

    output_type: str = Field(
        "instrumental",
        description="'instrumental' or 'song'",
    )
    style: str | None = Field(None, description="Music style/genre")
    mood: str | None = Field(None, description="Desired mood")
    energy: str | None = Field(None, description="'soft', 'medium', or 'high'")
    movement_feel: str | None = Field(None, description="Movement character")
    custom_instruction: str | None = Field(
        None,
        max_length=300,
        description="Optional free-text instruction from the user",
    )


class UploadResponse(BaseModel):
    gcs_uri: str
    preview_signed_url: str
    filename: str
    size_bytes: int


class RunAgentRequest(BaseModel):
    gcs_uri: str = Field(..., description="GCS URI of the uploaded video")
    user_preferences: UserPreferences
    cached_choreography: dict | None = Field(
        None,
        description="Previously computed ChoreographySchema JSON — skip re-analysis if provided",
    )
    cached_music_prompt: str | None = Field(
        None,
        description="Previously computed music prompt — skip re-planning if provided",
    )


class ChoreographySummary(BaseModel):
    moment_count: int
    moment_labels: list[str]
    duration_seconds: float
    overall_energy: str
    movement_tempo_bpm: int | None
    analysis_confidence: str
    low_confidence_warning: bool


class RunAgentResponse(BaseModel):
    final_video_signed_url: str
    choreography_summary: ChoreographySummary
    music_prompt: str
    choreography_json: dict  # full schema — stored client-side for Generate Again


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
