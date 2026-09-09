"""
Pydantic models for API request/response contracts.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    """Creative preferences selected by the user in the UI."""

    output_type: str = Field(
        "instrumental",
        description="'instrumental' or 'song'",
    )
    style: Optional[str] = Field(None, description="Music style/genre")
    mood: Optional[str] = Field(None, description="Desired mood")
    energy: Optional[str] = Field(None, description="'soft', 'medium', or 'high'")
    movement_feel: Optional[str] = Field(None, description="Movement character")
    custom_instruction: Optional[str] = Field(
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
    cached_choreography: Optional[dict] = Field(
        None,
        description="Previously computed ChoreographySchema JSON — skip re-analysis if provided",
    )
    cached_music_prompt: Optional[str] = Field(
        None,
        description="Previously computed music prompt — skip re-planning if provided",
    )


class ChoreographySummary(BaseModel):
    moment_count: int
    moment_labels: list[str]
    duration_seconds: float
    overall_energy: str
    movement_tempo_bpm: Optional[int]
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
