"""
ChoreographyMusicAgent — Google ADK Workflow Agent

A single deterministic workflow agent that orchestrates the
choreography → music → final video pipeline.

This agent satisfies the Agentic Cinema hackathon requirement for
a functional AI agent using Google Cloud Agent Builder / ADK.

Architecture:
  Tool 1: analyze_choreography  (Gemini multimodal)
  Tool 2: plan_music             (Gemini text reasoning)
  Tool 3: generate_music         (Lyria via google-genai)
  Tool 4: combine_media          (FFmpeg)

The agent runs synchronously — each tool must complete before the next begins.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from schemas.api import UserPreferences
from schemas.choreography import ChoreographySchema
from agent.tools.analyze_choreography import analyze_choreography_tool
from agent.tools.plan_music import plan_music_tool
from agent.tools.generate_music import generate_music_tool
from agent.tools.combine_media import combine_media_tool

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Output from a complete agent run."""

    choreography: ChoreographySchema
    music_prompt: str
    audio_gcs_uri: str
    final_video_signed_url: str


class ChoreographyMusicAgent:
    """
    Single deterministic workflow agent for the Agentic Cinema pipeline.

    Each method corresponds to one ADK tool. The run() method orchestrates
    the full sequence and supports selective re-execution for Generate Again:
    - cached_choreography: skip re-analysis if video hasn't changed
    - cached_music_prompt: skip re-planning if only audio needs regeneration
    """

    def run(
        self,
        video_bytes: bytes,
        video_mime_type: str,
        video_gcs_uri: str,
        user_preferences: UserPreferences,
        cached_choreography: Optional[dict] = None,
        cached_music_prompt: Optional[str] = None,
    ) -> AgentResult:
        """
        Run the complete pipeline.

        Generate Again logic:
        - If cached_choreography and cached_music_prompt are provided:
            skip Tools 1 and 2, run only Tools 3 + 4
        - If only cached_choreography is provided (preferences changed):
            skip Tool 1, run Tools 2, 3, 4
        - Otherwise: run all four tools
        """
        # ── Tool 1: Analyze choreography ──────────────────────────────────
        if cached_choreography is not None:
            logger.info("Using cached choreography analysis (skipping Tool 1)")
            choreography = ChoreographySchema.model_validate(cached_choreography)
        else:
            logger.info("Tool 1: Analyzing choreography...")
            choreography = analyze_choreography_tool(video_bytes, mime_type=video_mime_type)
            logger.info(
                "Tool 1 complete: %d segments, %d key moments",
                len(choreography.segments),
                len(choreography.key_moments),
            )

        # ── Tool 2: Plan music ─────────────────────────────────────────────
        if cached_music_prompt is not None and cached_choreography is not None:
            logger.info("Using cached music prompt (skipping Tool 2)")
            music_prompt = cached_music_prompt
        else:
            logger.info("Tool 2: Planning music...")
            music_prompt = plan_music_tool(choreography, user_preferences)
            logger.info("Tool 2 complete: %d-word music prompt", len(music_prompt.split()))

        # ── Tool 3: Generate music ─────────────────────────────────────────
        logger.info("Tool 3: Generating music with Lyria...")
        audio_gcs_uri = generate_music_tool(
            music_prompt=music_prompt,
            duration_seconds=choreography.duration_seconds,
            bpm=choreography.movement_tempo_bpm,
            output_type=user_preferences.output_type,
        )
        logger.info("Tool 3 complete: audio at %s", audio_gcs_uri)

        # ── Tool 4: Combine video + audio ──────────────────────────────────
        logger.info("Tool 4: Combining video and audio...")
        final_video_signed_url = combine_media_tool(
            video_gcs_uri=video_gcs_uri,
            audio_gcs_uri=audio_gcs_uri,
        )
        logger.info("Tool 4 complete: final video ready")

        return AgentResult(
            choreography=choreography,
            music_prompt=music_prompt,
            audio_gcs_uri=audio_gcs_uri,
            final_video_signed_url=final_video_signed_url,
        )
