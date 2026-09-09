"""
MoveScore — Gemini Enterprise Agent Platform (Agent Runtime) Module

Defines the static Google ADK Agent and wraps it with vertexai.agent_engines.AdkApp
for deployment to Gemini Enterprise Agent Platform / Agent Runtime.

Pipeline architecture:
    Agent Runtime (Reasoning Engine):
        1. analyze_choreography (Gemini 3.8 Flash)
        2. plan_music (Gemini 3.8 Flash)
        3. generate_music (Lyria 3.5 Interactions API)
        -> Returns structured output: {choreography_json, choreography_summary, music_prompt, audio_gcs_uri}
    FastAPI on Cloud Run:
        4. combine_media via local FFmpeg (H.264/yuv420p + AAC) -> signed URL
"""

from __future__ import annotations

import logging

from google.adk import Agent
from google.adk.tools import FunctionTool
from vertexai import agent_engines

from agent.tools.analyze_choreography import analyze_choreography_tool
from agent.tools.generate_music import generate_music_tool
from agent.tools.plan_music import plan_music_tool
from config import settings

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You are the MoveScore Agent orchestrator on Gemini Enterprise Agent Platform.
Your mission is to orchestrate a deterministic pipeline that turns a creator's dance video into an original soundtrack.

Given a user query containing:
- video_gcs_uri: GCS URI of the uploaded dance video
- preferences: creator choices (style, mood, energy, movement_feel, output_type, custom_instruction)
- cached_choreography: optional previously analyzed ChoreographySchema JSON
- cached_music_prompt: optional previously planned music direction

PIPELINE RULES:
1. Choreography Step:
   - If cached_choreography is provided and valid, reuse it.
   - Otherwise, call analyze_choreography_tool(video_gcs_uri=...).
2. Music Plan Step:
   - If cached_music_prompt is provided and valid, reuse it.
   - Otherwise, call plan_music_tool(choreography_json=..., style=..., mood=..., energy=..., movement_feel=..., output_type=..., custom_instruction=...).
3. Music Generation Step:
   - Call generate_music_tool(music_prompt=..., duration_seconds=..., bpm=..., output_type=...).
4. Final Output:
   - When all steps are done, output a STRICT JSON string matching this structure:
   {
     "status": "ok",
     "choreography_json": <parsed choreography schema dict>,
     "choreography_summary": <summary dict with moment_count, moment_labels, duration_seconds, overall_energy, movement_tempo_bpm, analysis_confidence>,
     "music_prompt": "<generated music prompt>",
     "audio_gcs_uri": "<GCS URI of the generated MP3>"
   }
   Do not add any text before or after the JSON block.
"""

# Static, picklable ADK Agent definition
movescore_agent = Agent(
    name="movescore_agent",
    description="Deterministic dance-to-music pipeline agent for MoveScore",
    model=settings.gemini_model,
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        FunctionTool(analyze_choreography_tool),
        FunctionTool(plan_music_tool),
        FunctionTool(generate_music_tool),
    ],
)

# Exported AdkApp for deployment to Agent Runtime
app = agent_engines.AdkApp(agent=movescore_agent)
