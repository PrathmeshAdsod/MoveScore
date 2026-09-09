"""
Run Agent route — POST /run-agent

Triggers the MoveScore ADK agent with a video GCS URI and user preferences.
Returns the choreography summary, music prompt, and final signed video URL.

The agent is synchronous internally but runs inside asyncio.to_thread() to
avoid blocking the FastAPI event loop.

Cloud Run timeout must be set to 600s to accommodate model latency.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from agent.workflow import ChoreographyMusicAgent
from schemas.api import ChoreographySummary, RunAgentRequest, RunAgentResponse
from utils.errors import AgenticCinemaError

logger = logging.getLogger(__name__)
router = APIRouter()

_agent = ChoreographyMusicAgent()


@router.post("/run-agent", response_model=RunAgentResponse)
async def run_agent(request: RunAgentRequest) -> RunAgentResponse:
    """
    Run the complete choreography → music → video pipeline.

    Supports Generate Again optimizations:
    - cached_choreography: re-use previous analysis, skip Gemini video analysis
    - cached_music_prompt: re-use previous music prompt, skip music planning
    """
    gcs_uri = request.gcs_uri
    preferences = request.user_preferences

    logger.info(
        "run-agent: uri=%s, style=%s, mood=%s, energy=%s, output=%s",
        gcs_uri,
        preferences.style,
        preferences.mood,
        preferences.energy,
        preferences.output_type,
    )

    # Run the ADK agent in a thread to avoid blocking the event loop
    try:
        result = await asyncio.to_thread(
            _agent.run,
            b"",
            "video/mp4",
            gcs_uri,
            preferences,
            request.cached_choreography,
            request.cached_music_prompt,
        )
    except AgenticCinemaError as exc:
        logger.error("Agent error: %s", exc.message)
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        logger.error("Unexpected agent error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during processing. Please try again.",
        )

    # Build response
    summary_dict = result.choreography.to_ui_summary()

    return RunAgentResponse(
        final_video_signed_url=result.final_video_signed_url,
        choreography_summary=ChoreographySummary(**summary_dict),
        music_prompt=result.music_prompt,
        choreography_json=result.choreography.model_dump(),
    )
