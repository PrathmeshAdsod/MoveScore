#!/usr/bin/env python3
"""
Proof Script 1 — Gemini Choreography Analysis

Run this script FIRST to validate that Gemini can analyze a dance video
before building any web infrastructure.

Usage:
    cd backend
    python scripts/proof_gemini_analysis.py path/to/dance_video.mp4

Requirements:
    - .env file with GEMINI_API_KEY and GEMINI_MODEL set
    - A real dance video file (10–20 seconds recommended)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add backend/ to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings  # noqa: E402 — after sys.path

if not settings.gemini_api_key:
    print("ERROR: GEMINI_API_KEY is not set. Copy .env.example to .env and fill it in.")
    sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python proof_gemini_analysis.py <path_to_video.mp4>")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"ERROR: File not found: {video_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("Agentic Cinema — Gemini Choreography Analysis Proof")
    print(f"{'='*60}")
    print(f"Model:       {settings.gemini_model}")
    print(f"Video:       {video_path.name}")
    print(f"Size:        {video_path.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"{'='*60}\n")

    # Detect MIME type
    suffix = video_path.suffix.lower()
    mime_map = {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}
    mime_type = mime_map.get(suffix, "video/mp4")

    video_bytes = video_path.read_bytes()

    print("Step 1: Uploading video to Gemini Files API...")
    print("Step 2: Analyzing choreography (this may take 15–30 seconds)...")

    from services.gemini_service import analyze_choreography  # noqa: E402

    try:
        choreography = analyze_choreography(video_bytes, mime_type=mime_type)
    except Exception as exc:
        print(f"\nFAILED: {exc}")
        print("\nTroubleshooting:")
        print("  - Verify GEMINI_API_KEY is correct")
        print(f"  - Verify model '{settings.gemini_model}' is available in your account")
        print("  - Check the video file is valid and not corrupted")
        sys.exit(1)

    print("\n✅ SUCCESS! Choreography analysis complete.\n")
    print(f"Duration:       {choreography.duration_seconds:.1f}s")
    print(f"Overall energy: {choreography.overall_energy}")
    print(f"Tempo (BPM):    {choreography.movement_tempo_bpm or 'Not detected'}")
    print(f"Confidence:     {choreography.analysis_confidence}")
    print(f"Segments:       {len(choreography.segments)}")
    print(f"Key moments:    {len(choreography.key_moments)}")
    print()

    print("Key moments:")
    for km in choreography.key_moments:
        print(f"  {km.time_sec:5.1f}s  [{km.type.value:15s}]  {km.note}")
    print()

    if choreography.analysis_notes:
        print(f"Notes: {choreography.analysis_notes}")
    print()

    print("UI summary (what user sees):")
    summary = choreography.to_ui_summary()
    labels = " → ".join(summary["moment_labels"])
    print(f"  {summary['moment_count']} movement moments detected")
    print(f"  {labels}")

    if choreography.analysis_confidence.value == "low":
        print("\n⚠️  LOW CONFIDENCE — fast movements may have been missed at ~1 FPS sampling.")
        print("   Consider testing with a 0.5x slowed copy of the video.")

    # Save full JSON for inspection
    out_path = video_path.parent / f"{video_path.stem}_choreography.json"
    with open(out_path, "w") as f:
        json.dump(choreography.model_dump(), f, indent=2)
    print(f"\nFull JSON saved to: {out_path}")


if __name__ == "__main__":
    main()
