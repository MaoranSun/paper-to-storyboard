#!/usr/bin/env python3
"""
Make a PNG's background transparent so it blends into a dark webpage.

Usage:
    python3 make_transparent.py <in_png> <out_png> [--mode flood|rembg] [--tol 18]

Modes:
  flood  (default) — Sample the four corners. Treat near-corner-color pixels
                     reachable from the edges via flood-fill as background and
                     set their alpha to 0. Good for plot figures with a uniform
                     near-white background. Lossless for foreground.
  rembg            — Use the rembg package (U2Net). Better for photos and
                     schematics with non-uniform backgrounds. Falls back to
                     flood if rembg isn't installed.
"""

import argparse
import sys
from collections import deque
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install pillow", file=sys.stderr)
    sys.exit(1)


def flood_transparent(img: Image.Image, tol: int = 18) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()

    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    # Reference color = average of the four corners
    rs, gs, bs = 0, 0, 0
    for x, y in corners:
        r, g, b, _ = px[x, y]
        rs += r; gs += g; bs += b
    ref = (rs // 4, gs // 4, bs // 4)

    def close(c):
        return (abs(c[0] - ref[0]) <= tol
                and abs(c[1] - ref[1]) <= tol
                and abs(c[2] - ref[2]) <= tol)

    visited = bytearray(w * h)
    q = deque()
    for x, y in corners:
        r, g, b, _ = px[x, y]
        if close((r, g, b)):
            q.append((x, y))
            visited[y * w + x] = 1

    while q:
        x, y = q.popleft()
        r, g, b, _ = px[x, y]
        px[x, y] = (r, g, b, 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not visited[ny * w + nx]:
                visited[ny * w + nx] = 1
                r2, g2, b2, _ = px[nx, ny]
                if close((r2, g2, b2)):
                    q.append((nx, ny))
    return img


def rembg_transparent(img: Image.Image) -> Image.Image:
    try:
        from rembg import remove
    except ImportError:
        print("WARN: rembg not installed; falling back to flood fill.", file=sys.stderr)
        return flood_transparent(img)
    return remove(img.convert("RGBA"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("in_png", type=Path)
    ap.add_argument("out_png", type=Path)
    ap.add_argument("--mode", choices=["flood", "rembg"], default="flood")
    ap.add_argument("--tol", type=int, default=18,
                    help="Color tolerance for flood mode (0-255)")
    args = ap.parse_args()

    if not args.in_png.exists():
        print(f"ERROR: input not found: {args.in_png}", file=sys.stderr)
        sys.exit(2)

    args.out_png.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(str(args.in_png))
    if args.mode == "rembg":
        out = rembg_transparent(img)
    else:
        out = flood_transparent(img, tol=args.tol)
    out.save(str(args.out_png), format="PNG")
    print(str(args.out_png.resolve()))


if __name__ == "__main__":
    main()
