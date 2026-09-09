#!/usr/bin/env python3
"""Probe Gemini 3.8 Flash and Lyria 3.5 using a Secret Manager API key."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import tempfile
from pathlib import Path

from google import genai
from google.cloud import secretmanager


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--secret", default="gemini-api-key")
    parser.add_argument("--gemini-model", default="gemini-3.8-flash")
    parser.add_argument("--lyria-model", default="lyria-3.5")
    args = parser.parse_args()

    secret_name = f"projects/{args.project}/secrets/{args.secret}/versions/latest"
    secret_response = secretmanager.SecretManagerServiceClient().access_secret_version(
        request={"name": secret_name}
    )
    api_key = secret_response.payload.data.decode("utf-8").strip()
    client = genai.Client(api_key=api_key)

    gemini_response = client.models.generate_content(
        model=args.gemini_model,
        contents="Reply with exactly MOVESCORE_GEMINI_OK",
    )
    if gemini_response.text.strip() != "MOVESCORE_GEMINI_OK":
        raise RuntimeError("Gemini returned an unexpected probe response")
    print(f"GEMINI_PROBE=ok model={args.gemini_model}")

    interaction = client.interactions.create(
        model=args.lyria_model,
        input=(
            "Create an approximately 10-second instrumental electronic dance music test clip. "
            "No vocals. End with a clear final hit."
        ),
    )
    audio = interaction.output_audio
    if audio is None or not audio.data:
        raise RuntimeError("Lyria returned no audio data")
    audio_bytes = (
        base64.b64decode(audio.data)
        if isinstance(audio.data, str)
        else bytes(audio.data)
    )

    with tempfile.TemporaryDirectory(prefix="movescore-provider-probe-") as tmp:
        audio_path = Path(tmp) / "lyria_probe.mp3"
        audio_path.write_bytes(audio_bytes)
        ffprobe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=format_name,duration:stream=codec_name,sample_rate,channels",
                "-of",
                "json",
                str(audio_path),
            ],
            capture_output=True,
            check=True,
            text=True,
            timeout=30,
        )
        metadata = json.loads(ffprobe.stdout)

    stream = metadata["streams"][0]
    media_format = metadata["format"]
    print(
        "LYRIA_PROBE=ok "
        f"model={args.lyria_model} codec={stream['codec_name']} "
        f"sample_rate={stream['sample_rate']} channels={stream['channels']} "
        f"duration={float(media_format['duration']):.2f}s bytes={len(audio_bytes)}"
    )


if __name__ == "__main__":
    main()
