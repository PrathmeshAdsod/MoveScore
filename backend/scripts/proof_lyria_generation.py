#!/usr/bin/env python3
"""
Proof Script 2 — Lyria Music Generation

Run this script to validate Lyria access before building UI infrastructure.

Usage:
    cd backend
    python scripts/proof_lyria_generation.py [optional: path/to/choreography.json]

If a choreography JSON file is provided (from proof_gemini_analysis.py output),
it will be used to build a real music prompt. Otherwise a test prompt is used.

Requirements:
    - .env file with GEMINI_API_KEY and LYRIA_MODEL set
    - Lyria model accessible in your Google account
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
    sys.exit(1)

# Test prompt if no choreography JSON provided
TEST_MUSIC_PROMPT = """\
18-second upbeat Afrobeat track. Start with a restrained, groove-based intro \
from [0:00-0:03] featuring light percussion and bass. Around 0:03, add a strong \
drum accent to mark a movement hit. Build energy from [0:03-0:07] with rising \
rhythm and melodic phrases. Around 0:07, include a swirling transition element. \
Around 0:10, briefly pause the rhythm for one beat — a freeze moment. \
From [0:11-0:18] open into a full high-energy drop with full arrangement. \
End with a strong conclusive hit at around 0:18 for the final pose. \
Euphoric mood. Groovy movement feel. Instrumental only. BPM around 108.
"""


def main() -> None:
    print(f"\n{'='*60}")
    print(f"Agentic Cinema — Lyria Music Generation Proof")
    print(f"{'='*60}")
    print(f"Model:  {settings.lyria_model}")
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
            from prompts.music_plan import build_music_plan_prompt
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

    print("Music Prompt:")
    print(f"{'─'*50}")
    print(music_prompt)
    print(f"{'─'*50}\n")

    output_path = Path("./test_output_music.mp3")
    print(f"Generating music (duration: {duration_seconds:.0f}s)...")
    print("This may take 30–60 seconds...\n")

    from services.lyria_service import generate_music

    try:
        generate_music(music_prompt, duration_seconds, output_path)
    except Exception as exc:
        print(f"\nFAILED: {exc}")
        print("\nTroubleshooting:")
        print(f"  - Verify LYRIA_MODEL='{settings.lyria_model}' is accessible in your account")
        print("  - Check https://ai.google.dev/gemini-api/docs/music-generation for current model IDs")
        print("  - Verify your Gemini API key has Lyria access")
        print("  - Check quota at https://console.cloud.google.com/iam-admin/quotas")
        sys.exit(1)

    size_kb = output_path.stat().st_size / 1024
    print(f"✅ SUCCESS! Music generated.")
    print(f"   Output:   {output_path.resolve()}")
    print(f"   Size:     {size_kb:.1f} KB")
    print(f"\nPlay the file to verify the output sounds correct.")
    print("Then run proof_end_to_end.py for the complete pipeline test.\n")


if __name__ == "__main__":
    main()
