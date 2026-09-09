#!/usr/bin/env python3
"""
Proof Script 3 — End-to-End Local Pipeline

Runs the complete pipeline locally without a web server:
  video → Gemini analysis → music plan → Lyria → FFmpeg → final MP4

Prerequisites:
    - Run proof_gemini_analysis.py first to confirm Gemini works
    - Run proof_lyria_generation.py first to confirm Lyria works
    - ffmpeg must be installed locally (brew install ffmpeg / apt install ffmpeg)
    - GCS bucket must exist and credentials must be configured

Usage:
    cd backend
    python scripts/proof_end_to_end.py path/to/dance_video.mp4 [--style Afrobeat] [--mood Euphoric]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add backend/ to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="End-to-end pipeline proof script")
    p.add_argument("video", help="Path to dance video file")
    p.add_argument("--style", default="Afrobeat", help="Music style")
    p.add_argument("--mood", default="Euphoric", help="Music mood")
    p.add_argument("--energy", default="high", help="Energy level")
    p.add_argument("--feel", default="Groovy", help="Movement feel")
    p.add_argument("--output", default=None, help="Output MP4 path (default: next to input)")
    return p.parse_args()


def check_prerequisites() -> None:
    import shutil

    errors: list[str] = []
    if not settings.gemini_api_key:
        errors.append("GEMINI_API_KEY is not set")
    if not settings.gcs_temp_bucket:
        errors.append("GCS_TEMP_BUCKET is not set")
    if shutil.which("ffmpeg") is None:
        errors.append(
            "ffmpeg not found on PATH (install: brew install ffmpeg or apt install ffmpeg)"
        )
    if errors:
        print("Prerequisites not met:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


def main() -> None:
    args = parse_args()
    check_prerequisites()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"ERROR: Video file not found: {video_path}")
        sys.exit(1)

    output_path = (
        Path(args.output)
        if args.output
        else video_path.parent / f"{video_path.stem}_with_music.mp4"
    )

    print(f"\n{'='*60}")
    print("MoveScore — End-to-End Pipeline Proof")
    print(f"{'='*60}")
    print(f"Video:    {video_path.name}  ({video_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"Style:    {args.style}")
    print(f"Mood:     {args.mood}")
    print(f"Energy:   {args.energy}")
    print(f"Output:   {output_path}")
    print(f"{'='*60}\n")

    import tempfile

    from schemas.api import UserPreferences
    from services.ffmpeg_service import combine_video_and_audio
    from services.gemini_service import analyze_choreography, plan_music
    from services.lyria_service import generate_music
    from services.storage import make_blob_name, upload_bytes

    suffix = video_path.suffix.lower()
    mime_map = {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}
    mime_type = mime_map.get(suffix, "video/mp4")
    video_bytes = video_path.read_bytes()

    prefs = UserPreferences(
        output_type="instrumental",
        style=args.style,
        mood=args.mood,
        energy=args.energy,
        movement_feel=args.feel,
    )

    # Step 1: Analyze choreography
    print("[1/4] Analyzing choreography (uploading to Gemini Files API)...")
    try:
        choreography = analyze_choreography(video_bytes, mime_type=mime_type)
        print(f"      ✅ {len(choreography.key_moments)} key moments detected")
        print(f"         Confidence: {choreography.analysis_confidence}")
        if choreography.movement_tempo_bpm:
            print(f"         Tempo: ~{choreography.movement_tempo_bpm} BPM")
    except Exception as exc:
        print(f"      FAILED: {exc}")
        sys.exit(1)

    # Step 2: Plan music
    print("\n[2/4] Planning music (Gemini text reasoning)...")
    try:
        music_prompt = plan_music(choreography, prefs)
        print(f"      ✅ Music prompt generated ({len(music_prompt.split())} words)")
        print(f"\n      Prompt preview:\n      {music_prompt[:200]}...")
    except Exception as exc:
        print(f"      FAILED: {exc}")
        sys.exit(1)

    # Step 3: Generate music with Lyria
    print(f"\n[3/4] Generating music with Lyria ({choreography.duration_seconds:.0f}s)...")
    tmp_audio = Path(tempfile.mktemp(suffix=".mp3"))
    try:
        generate_music(music_prompt, choreography.duration_seconds, tmp_audio)
        print(f"      ✅ Audio generated ({tmp_audio.stat().st_size / 1024:.0f} KB)")
    except Exception as exc:
        print(f"      FAILED: {exc}")
        sys.exit(1)

    # Step 4: Upload original video to GCS + combine
    print("\n[4/4] Uploading video to GCS and combining with audio (FFmpeg)...")
    try:
        blob_name = make_blob_name("uploads", suffix.lstrip(".") or "mp4")
        video_gcs_uri = upload_bytes(video_bytes, blob_name, mime_type)
        print(f"      Video uploaded: {video_gcs_uri}")

        signed_url = combine_video_and_audio(video_gcs_uri, tmp_audio)
        print(f"      ✅ Final video ready: {signed_url[:80]}...")
    except Exception as exc:
        print(f"      FAILED: {exc}")
        sys.exit(1)
    finally:
        if tmp_audio.exists():
            tmp_audio.unlink()

    print(f"\n{'='*60}")
    print("✅ END-TO-END PIPELINE COMPLETE")
    print(f"{'='*60}")
    print("\nFinal video signed URL (valid 1h):")
    print(f"  {signed_url}")
    print("\nOpen the URL in a browser to preview and download.")
    print()


if __name__ == "__main__":
    main()
