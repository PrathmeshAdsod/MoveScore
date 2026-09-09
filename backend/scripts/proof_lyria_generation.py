#!/usr/bin/env python3
"""
Proof Script 2 — Lyria 3.5 Music Generation

Tests Lyria 3.5 access using the Gemini Interactions API
(client.interactions.create), NOT the real-time live music API.

Usage:
    cd backend
    python scripts/proof_lyria_generation.py [optional: path/to/choreography.json]

If a choreography JSON file is provided (from proof_gemini_analysis.py output),
it will be used to build a real music prompt via Gemini. Otherwise a test prompt
is used directly.

Requirements:
    - .env file with GEMINI_API_KEY set
    - Lyria 3.5 accessible in your Google AI account
      (check: https://ai.google.dev/gemini-api/docs/music-generation)

Output:
    ./test_output_music.mp3  (MP3, 44.1 kHz stereo — Lyria 3.5 standard format)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add backend/ to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings  # noqa: E402

if not settings.gemini_api_key:
    print("ERROR: GEMINI_API_KEY is not set.")
    print("  Set it in backend/.env or as an environment variable.")
    sys.exit(1)

# Test prompt — demonstrates timestamp-aware music direction
TEST_MUSIC_PROMPT = """\
18-second upbeat Afrobeat instrumental track. \
Start with a restrained, groove-based intro from 0:00-0:03 featuring light percussion and bass. \
Around 0:03, add a strong drum accent to mark a movement hit. \
Build energy from 0:03-0:07 with rising rhythm and melodic phrases. \
Around 0:07, include a swirling transition element for a spin. \
Around 0:10, briefly pause the rhythm for one beat — a freeze moment. \
From 0:11 onward, open into a full high-energy section with complete arrangement. \
End with a strong conclusive hit around 0:18 for the final pose. \
Euphoric mood. Groovy movement feel. Instrumental only. BPM approximately 108.\
"""


def main() -> None:
    print(f"\n{'='*60}")
    print("MoveScore — Lyria 3.5 Music Generation Proof")
    print(f"{'='*60}")
    print(f"Model:   {settings.lyria_model}")
    print(f"API:     Gemini Interactions API (NOT Live/RealTime)")
    print(f"Output:  MP3 (44.1 kHz stereo)")
    print(f"{'='*60}\n")

    # Determine music prompt
    music_prompt = TEST_MUSIC_PROMPT
    duration_seconds = 18.0

    if len(sys.argv) > 1:
        choreo_path = Path(sys.argv[1])
        if choreo_path.exists():
            print(f"Loading choreography from: {choreo_path}")
            from schemas.choreography import ChoreographySchema
            from schemas.api import UserPreferences
            from services.gemini_service import plan_music

            with open(choreo_path) as f:
                choreo_dict = json.load(f)
            choreography = ChoreographySchema.model_validate(choreo_dict)
            duration_seconds = choreography.duration_seconds

            prefs = UserPreferences(
                output_type="instrumental",
                style="Afrobeat",
                mood="Euphoric",
                energy="high",
                movement_feel="Groovy",
            )

            print("Generating music plan with Gemini first...")
            try:
                music_prompt = plan_music(choreography, prefs)
                print(f"Music plan generated ({len(music_prompt.split())} words)\n")
            except Exception as exc:
                print(f"Music plan generation failed: {exc}")
                print("Falling back to test prompt.\n")
                music_prompt = TEST_MUSIC_PROMPT
        else:
            print(f"Warning: {choreo_path} not found. Using test prompt.\n")

    print("Music Prompt:")
    print(f"{'─'*50}")
    print(music_prompt)
    print(f"{'─'*50}\n")

    # Output as MP3 (Lyria 3.5 Interactions API output format)
    output_path = Path("./test_output_music.mp3")
    print(f"Generating music (target duration: {duration_seconds:.0f}s)...")
    print("This may take 10-60 seconds depending on API load...\n")

    from services.lyria_service import generate_music

    try:
        generate_music(music_prompt, duration_seconds, output_path)
    except Exception as exc:
        print(f"\nFAILED: {exc}")
        print("\nTroubleshooting:")
        print(f"  - Verify LYRIA_MODEL='{settings.lyria_model}' is accessible")
        print("  - Check https://ai.google.dev/gemini-api/docs/music-generation")
        print("  - Verify your Gemini API key has Lyria 3.5 access")
        print("  - Lyria 3.5 may require allowlist approval for your account")
        print("  - Check quota at https://console.cloud.google.com/iam-admin/quotas")
        sys.exit(1)

    size_kb = output_path.stat().st_size / 1024
    print(f"SUCCESS! Music generated.")
    print(f"   Output:   {output_path.resolve()}")
    print(f"   Size:     {size_kb:.1f} KB")
    print(f"   Format:   MP3 (Lyria 3.5 Interactions API standard output)")
    print(f"\nPlay the file to verify the output sounds correct.")
    print("Then run proof_end_to_end.py for the complete pipeline test.\n")


if __name__ == "__main__":
    main()
