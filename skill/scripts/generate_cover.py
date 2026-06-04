#!/usr/bin/env python3
"""
Generate a title-page cover image via OpenAI gpt-image-1.

Usage:
    python3 generate_cover.py --concept "<paper concept>" --palette <name> \
        [--mode dark|light] [--out cover.png] [--size 1536x1024] [--quality medium]

The caller supplies a one-sentence `--concept` describing what the paper is
about (e.g. "city-scale identification of hard-to-decarbonize houses from
street and aerial imagery"). This script wraps it into a data-art prompt
tinted toward the chosen palette + mode, calls OpenAI, and writes cover.png.

Requires:
    OPENAI_API_KEY env var.
    pip install openai
"""

import argparse
import base64
import os
import sys
from pathlib import Path


PALETTE_HINT = {
    "warm":     "deep reds, oranges, ember glow, magma",
    "cool":     "teal, cyan, navy, ocean blues",
    "earth":    "olive, moss, chartreuse, soft greens with warm earth tones",
    "clinical": "cool blues, cyan accents, occasional red signal",
    "tech":     "violet, electric purple, cyan, neon magenta",
}

MODE_HINT = {
    "dark":  "dark cinematic background, deep shadows, moody atmospheric lighting, low key",
    "light": "light editorial background, airy, soft diffuse light, high key with gentle contrast",
}


def build_prompt(concept: str, palette: str, mode: str) -> str:
    palette_text = PALETTE_HINT.get(palette, PALETTE_HINT["warm"])
    mode_text = MODE_HINT.get(mode, MODE_HINT["dark"])
    return (
        f"Abstract stylized data-art for the cover of a scientific paper about "
        f"{concept}. Translate the concept into generative-art visuals: flowing "
        f"particles, layered topographic contours, soft network filaments, "
        f"luminous data streams, granular noise textures. Compose in a {palette_text} "
        f"color palette. {mode_text}. 16:9 cinematic composition, depth and atmosphere, "
        f"editorial magazine cover quality, subtle film grain. No text, no logos, "
        f"no letters, no numbers, no UI elements, no human faces, no charts with axes."
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--concept", required=True,
                    help="One-sentence description of what the paper studies.")
    ap.add_argument("--palette", required=True,
                    choices=["warm", "cool", "earth", "clinical", "tech"])
    ap.add_argument("--mode", default="dark", choices=["dark", "light"])
    ap.add_argument("--out", type=Path, default=Path("cover.png"))
    ap.add_argument("--size", default="1536x1024",
                    choices=["1024x1024", "1536x1024", "1024x1536"])
    ap.add_argument("--quality", default="medium",
                    choices=["low", "medium", "high"])
    ap.add_argument("--prompt-only", action="store_true",
                    help="Print the assembled prompt and exit without calling the API.")
    args = ap.parse_args()

    prompt = build_prompt(args.concept, args.palette, args.mode)
    if args.prompt_only:
        print(prompt)
        return

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set. To skip cover generation, omit "
              "this step — the title page falls back to the default gradient.",
              file=sys.stderr)
        sys.exit(2)

    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai not installed. Run: pip install openai", file=sys.stderr)
        sys.exit(2)

    client = OpenAI()
    print(f"Calling gpt-image-1 ({args.size}, quality={args.quality})...", file=sys.stderr)
    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size=args.size,
        quality=args.quality,
        n=1,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    image_b64 = result.data[0].b64_json
    args.out.write_bytes(base64.b64decode(image_b64))
    print(str(args.out.resolve()))


if __name__ == "__main__":
    main()
