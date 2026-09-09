"""
Prompt 1 — Gemini Choreography Analysis

Sent to Gemini with the dance video. Returns structured ChoreographySchema JSON.
"""

from __future__ import annotations

import json

from schemas.choreography import ChoreographySchema

# The full schema is injected at call time so Gemini has the exact structure.
_SCHEMA_JSON = json.dumps(ChoreographySchema.model_json_schema(), indent=2)

CHOREOGRAPHY_ANALYSIS_PROMPT = f"""You are a professional choreography analyst. Analyze this dance video completely from start to finish.

Your job is to produce a STRUCTURED, MACHINE-READABLE choreography analysis only.
Do NOT write prose paragraphs. Do NOT invent movements you cannot clearly see.

RULES:
1. Only describe movements that are clearly visible in the video.
2. If a section is unclear, out-of-frame, too dark, or too fast to analyze confidently, note it in analysis_notes and set analysis_confidence to "medium" or "low".
3. movement_tempo_bpm: estimate the rhythm/tempo you observe from the dancer's physical movements.
   This is NOT a song BPM — the video may have no music. Set null if you cannot confidently estimate it.
4. intensity: use a scale of 1–10 where 1 is complete stillness and 10 is maximum physical exertion.
5. All timestamps must be in seconds as decimal numbers (e.g., 3.5 for 3 seconds 500ms).
6. Segments must cover the entire video duration without gaps.
7. If a movement happens faster than approximately 1 second, note it in analysis_notes — do not fabricate frame-level detail.
8. key_moments: capture only genuine discrete events (accents, spins, freezes, jumps, final pose, climax start).

OUTPUT: Return ONLY valid JSON. No prose. No markdown. No explanation. No code fences.
The JSON must match this exact schema:

{_SCHEMA_JSON}
"""
