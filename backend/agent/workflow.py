"""
MoveScore — Google ADK Workflow Agent

Implements the choreography → music → final video pipeline using the
Google Agent Development Kit (google-adk).

Architecture:
- A real google.adk.Agent with 4 FunctionTools
- The agent uses Gemini to orchestrate the sequential tool calls
- Tools are deterministic Python functions wrapped with FunctionTool
- A simple InMemorySessionService + Runner executes the agent

Pipeline:
    Tool 1: analyze_choreography  (Gemini multimodal video analysis)
    Tool 2: plan_music             (Gemini text reasoning for music direction)
    Tool 3: generate_music         (Lyria 3.5 via Interactions API)
    Tool 4: combine_media          (FFmpeg video+audio combine)

Generate Again logic:
    - cached_choreography + cached_music_prompt: skip tools 1 & 2
    - cached_choreography only: skip tool 1, rerun 2 + 3 + 4
    - fresh run: all four tools

Note: The ADK agent runs synchronously by wrapping the async runner with
asyncio.run(). For production, use the async runner directly.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Optional

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types as genai_types

from schemas.api import UserPreferences
from schemas.choreography import ChoreographySchema
from agent.tools.analyze_choreography import analyze_choreography_tool
from agent.tools.plan_music import plan_music_tool
from agent.tools.generate_music import generate_music_tool
from agent.tools.combine_media import combine_media_tool

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Output from a complete MoveScore pipeline run."""

    choreography: ChoreographySchema
    music_prompt: str
    audio_gcs_uri: str
    final_video_signed_url: str


# ── Pipeline state (shared across tool calls via closure) ─────────────────────

class _PipelineState:
    """Mutable state container shared by tool closures during one pipeline run."""

    def __init__(
        self,
        video_bytes: bytes,
        video_mime_type: str,
        video_gcs_uri: str,
        user_preferences: UserPreferences,
        cached_choreography: Optional[dict],
        cached_music_prompt: Optional[str],
    ) -> None:
        self.video_bytes = video_bytes
        self.video_mime_type = video_mime_type
        self.video_gcs_uri = video_gcs_uri
        self.user_preferences = user_preferences
        self.cached_choreography = cached_choreography
        self.cached_music_prompt = cached_music_prompt

        # Results populated by tools
        self.choreography: Optional[ChoreographySchema] = None
        self.music_prompt_result: Optional[str] = None
        self.audio_gcs_uri: Optional[str] = None
        self.final_video_signed_url: Optional[str] = None


# ── ADK Tool builders ─────────────────────────────────────────────────────────

def _build_adk_tools(state: _PipelineState) -> list:
    """
    Build the four ADK FunctionTools using closures over the pipeline state.
    Each tool is a Python function decorated with google.adk.tools.FunctionTool.
    """

    def analyze_choreography_adk() -> str:
        """
        Analyze the uploaded dance video and extract structured choreography data.

        Returns a JSON summary of detected movement segments, key moments
        (hits, spins, freezes, jumps, buildup, climax, final pose),
        energy levels, tempo, and confidence score.

        Only call this tool when analyzing a new video. If choreography is
        already cached, skip this tool and call plan_music directly.
        """
        if state.cached_choreography is not None:
            # Use cached result — skip re-analysis
            state.choreography = ChoreographySchema.model_validate(
                state.cached_choreography
            )
            logger.info("analyze_choreography: using cached result")
        else:
            logger.info("analyze_choreography: calling Gemini multimodal API")
            state.choreography = analyze_choreography_tool(
                state.video_bytes,
                mime_type=state.video_mime_type,
            )
            logger.info(
                "analyze_choreography: %d segments, %d key moments, confidence=%s",
                len(state.choreography.segments),
                len(state.choreography.key_moments),
                state.choreography.analysis_confidence,
            )

        return json.dumps({
            "status": "ok",
            "duration_seconds": state.choreography.duration_seconds,
            "segment_count": len(state.choreography.segments),
            "key_moment_count": len(state.choreography.key_moments),
            "overall_energy": state.choreography.overall_energy.value,
            "movement_tempo_bpm": state.choreography.movement_tempo_bpm,
            "analysis_confidence": state.choreography.analysis_confidence.value,
            "next_step": "call plan_music",
        })

    def plan_music_adk() -> str:
        """
        Convert the choreography analysis and creator preferences into a
        timestamp-aware music generation prompt for Lyria 3.5.

        This step acts as the music director — translating movement events
        (hits, spins, freezes, buildup, climax, final pose) into musical
        language with approximate timestamp markers.

        Call this tool after analyze_choreography and before generate_music.
        """
        if state.choreography is None:
            return json.dumps({"error": "choreography not yet analyzed — call analyze_choreography first"})

        if state.cached_music_prompt is not None and state.cached_choreography is not None:
            state.music_prompt_result = state.cached_music_prompt
            logger.info("plan_music: using cached music prompt")
        else:
            logger.info("plan_music: generating music plan with Gemini")
            state.music_prompt_result = plan_music_tool(
                state.choreography,
                state.user_preferences,
            )
            logger.info(
                "plan_music: generated %d-word prompt",
                len(state.music_prompt_result.split()),
            )

        return json.dumps({
            "status": "ok",
            "music_prompt_word_count": len(state.music_prompt_result.split()),
            "music_prompt_preview": state.music_prompt_result[:200],
            "next_step": "call generate_music",
        })

    def generate_music_adk() -> str:
        """
        Generate an original music track using Lyria 3.5 based on the music
        direction plan. The music is shaped around the choreography structure
        using approximate timestamp markers as musical directions.

        Uses the Gemini Interactions API (not the real-time/live API).
        Output is an MP3 file uploaded to Google Cloud Storage.

        Call this tool after plan_music and before combine_media.
        """
        if state.choreography is None:
            return json.dumps({"error": "choreography not available"})
        if state.music_prompt_result is None:
            return json.dumps({"error": "music prompt not available — call plan_music first"})

        logger.info("generate_music: calling Lyria 3.5 Interactions API")
        state.audio_gcs_uri = generate_music_tool(
            music_prompt=state.music_prompt_result,
            duration_seconds=state.choreography.duration_seconds,
            bpm=state.choreography.movement_tempo_bpm,
            output_type=state.user_preferences.output_type,
        )
        logger.info("generate_music: audio uploaded to %s", state.audio_gcs_uri)

        return json.dumps({
            "status": "ok",
            "audio_gcs_uri": state.audio_gcs_uri,
            "next_step": "call combine_media",
        })

    def combine_media_adk() -> str:
        """
        Combine the original dance video with the Lyria-generated music track
        using FFmpeg. The video's length determines the final output duration.
        The generated music replaces any original audio in the video.

        Returns a signed URL for the final combined video (valid for 1 hour).

        Call this tool after generate_music. This is the final pipeline step.
        """
        if state.audio_gcs_uri is None:
            return json.dumps({"error": "audio not generated — call generate_music first"})

        logger.info("combine_media: combining video and audio with FFmpeg")
        state.final_video_signed_url = combine_media_tool(
            video_gcs_uri=state.video_gcs_uri,
            audio_gcs_uri=state.audio_gcs_uri,
        )
        logger.info("combine_media: final video ready")

        return json.dumps({
            "status": "ok",
            "final_video_signed_url": state.final_video_signed_url,
            "pipeline_complete": True,
        })

    return [
        FunctionTool(analyze_choreography_adk),
        FunctionTool(plan_music_adk),
        FunctionTool(generate_music_adk),
        FunctionTool(combine_media_adk),
    ]


# ── Agent orchestration ───────────────────────────────────────────────────────

def _build_system_instruction(state: _PipelineState) -> str:
    """Build the agent's system instruction describing the pipeline and cache state."""
    has_choreography = state.cached_choreography is not None
    has_music_prompt = state.cached_music_prompt is not None

    if has_choreography and has_music_prompt:
        cache_note = (
            "CACHE STATE: Both choreography analysis AND music prompt are cached from a previous run. "
            "Skip analyze_choreography AND plan_music. "
            "Call generate_music directly, then combine_media."
        )
    elif has_choreography:
        cache_note = (
            "CACHE STATE: Choreography analysis is cached. "
            "Skip analyze_choreography. "
            "Call plan_music (preferences may have changed), then generate_music, then combine_media."
        )
    else:
        cache_note = (
            "CACHE STATE: No cache available. "
            "Run the full pipeline: analyze_choreography → plan_music → generate_music → combine_media."
        )

    return f"""You are the MoveScore pipeline orchestrator. Your job is to run a deterministic \
4-step pipeline that turns a dance video into an original music track.

{cache_note}

PIPELINE RULES:
1. Always run the steps in order: analyze_choreography → plan_music → generate_music → combine_media
2. Never skip combine_media — the user always needs the final video
3. Never call tools in parallel — each step depends on the previous
4. After combine_media succeeds, respond with exactly: PIPELINE_COMPLETE

Do not add explanations or summaries. Just call the tools in the correct order and respond \
PIPELINE_COMPLETE when done."""


async def _run_agent_async(state: _PipelineState) -> None:
    """Run the ADK agent asynchronously and populate state with results."""
    from config import settings as app_settings

    tools = _build_adk_tools(state)

    agent = Agent(
        name="movescore_pipeline",
        description="Orchestrates the MoveScore dance-to-music pipeline",
        model=app_settings.gemini_model,
        instruction=_build_system_instruction(state),
        tools=tools,
    )

    session_service = InMemorySessionService()
    runner = Runner(
        app_name="movescore",
        agent=agent,
        session_service=session_service,
    )

    user_id = "movescore_user"
    session_id = uuid.uuid4().hex

    await session_service.create_session(
        app_name="movescore",
        user_id=user_id,
        session_id=session_id,
    )

    start_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text="Run the MoveScore pipeline now.")],
    )

    # Run the agent — it orchestrates tool calls until PIPELINE_COMPLETE
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=start_message,
    ):
        if event.is_final_response():
            logger.info("ADK agent final response received")
            break


class ChoreographyMusicAgent:
    """
    MoveScore pipeline agent using Google ADK.

    Uses google.adk.Agent with FunctionTools to orchestrate the full
    dance-to-music pipeline. The agent (backed by Gemini) decides which
    tools to call and in what order based on the system instruction.

    Supports Generate Again via cached_choreography and cached_music_prompt.
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
        Run the complete pipeline via the ADK agent.

        Generate Again logic:
        - cached_choreography + cached_music_prompt: only run tools 3 & 4
        - cached_choreography only (prefs changed): run tools 2, 3, 4
        - No cache: run all four tools
        """
        state = _PipelineState(
            video_bytes=video_bytes,
            video_mime_type=video_mime_type,
            video_gcs_uri=video_gcs_uri,
            user_preferences=user_preferences,
            cached_choreography=cached_choreography,
            cached_music_prompt=cached_music_prompt,
        )

        logger.info(
            "ChoreographyMusicAgent.run: has_choreo_cache=%s, has_prompt_cache=%s",
            cached_choreography is not None,
            cached_music_prompt is not None,
        )

        # Run the async ADK agent synchronously
        # In production on Cloud Run, the event loop is managed by uvicorn;
        # we use asyncio.run() here to avoid blocking the event loop.
        # The FastAPI route should call this in run_in_executor for production.
        try:
            asyncio.run(_run_agent_async(state))
        except RuntimeError as exc:
            # If an event loop is already running (e.g., in tests), use nest_asyncio
            if "already running" in str(exc).lower():
                import nest_asyncio  # type: ignore[import]
                nest_asyncio.apply()
                asyncio.get_event_loop().run_until_complete(_run_agent_async(state))
            else:
                raise

        # Validate that all pipeline steps completed
        if state.choreography is None:
            from utils.errors import ChoreographyAnalysisError
            raise ChoreographyAnalysisError("Pipeline failed: choreography analysis did not complete")
        if state.music_prompt_result is None:
            from utils.errors import MusicPlanError
            raise MusicPlanError("Pipeline failed: music planning did not complete")
        if state.audio_gcs_uri is None:
            from utils.errors import MusicGenerationError
            raise MusicGenerationError("Pipeline failed: music generation did not complete")
        if state.final_video_signed_url is None:
            from utils.errors import MediaCombineError
            raise MediaCombineError("Pipeline failed: media combine did not complete")

        return AgentResult(
            choreography=state.choreography,
            music_prompt=state.music_prompt_result,
            audio_gcs_uri=state.audio_gcs_uri,
            final_video_signed_url=state.final_video_signed_url,
        )
