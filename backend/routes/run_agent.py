"""
Run Agent route — POST /run-agent

Triggers the ChoreographyMusicAgent with a video GCS URI and user preferences.
Returns the choreography summary, music prompt, and final signed video URL.

Synchronous — the request blocks until the full pipeline completes.
Cloud Run timeout must be set to 600s to accommodate model latency.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from agent.workflow import ChoreographyMusicAgent
from schemas.api import ChoreographySummary, RunAgentRequest, RunAgentResponse
from services import storage as gcs
from utils.errors import AgenticCinemaError

logger = logging.getLogger(__name__)
router = APIRouter()

_agent = ChoreographyMusicAgent()


@router.post("/run-agent", response_model=RunAgentResponse)
async def run_agent(request: RunAgentRequest) -> RunAgentResponse:
    """
    Run the complete choreography → music → video pipeline.

    Supports Generate Again optimizations:
    - cached_choreography: re-use previous analysis, skip re-analysis
    - cached_music_prompt: re-use previous music prompt, skip re-planning
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

    # Download video bytes from GCS (needed for Gemini Files API upload)
    # Only download if we need to re-analyze (no cached choreography)
    video_bytes: bytes = b""
    video_mime_type: str = "video/mp4"

    if request.cached_choreography is None:
        try:
            import tempfile
            from pathlib import Path
            import shutil

            tmp_path = Path(tempfile.mktemp(suffix=".mp4"))
            gcs.download_to_file(gcs_uri, tmp_path)
            video_bytes = tmp_path.read_bytes()
            tmp_path.unlink(missing_ok=True)
        except AgenticCinemaError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message)
        except Exception as exc:
            logger.error("Failed to download video for analysis: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to retrieve uploaded video.")

    # Run the agent
    try:
        result = _agent.run(
            video_bytes=video_bytes,
            video_mime_type=video_mime_type,
            video_gcs_uri=gcs_uri,
            user_preferences=preferences,
            cached_choreography=request.cached_choreography,
            cached_music_prompt=request.cached_music_prompt,
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
