#!/usr/bin/env python3
"""
Extract figures from an academic PDF.

Usage:
    python3 extract_figures.py <pdf_path> <out_dir>

Approach:
  1) Try to extract embedded raster images via PyMuPDF (`page.get_images`).
     Filter by min size to skip page-furniture (logos, lines, single icons).
  2) If a page has a "Figure N." caption but no embedded image of meaningful
     size on that page, render the page region above the caption at 2x and
     crop. This captures figures composed of multiple parts or vector content.

Emits:
  <out_dir>/figure1.png ... figureN.png
  <out_dir>/figures.json  (list of {file, label, caption, page, bbox})
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install pymupdf", file=sys.stderr)
    sys.exit(1)


FIG_CAP_RE = re.compile(r"^\s*(Fig(?:ure)?\.?\s*\d+[A-Za-z]?)\.?\s*[:.—\-]?\s*(.*)", re.IGNORECASE)
MIN_W = 200  # pixels — below this we treat as page furniture
MIN_H = 150


def detect_captions(page):
    """Return [(label, caption_text, rect)] for figure captions on this page."""
    out = []
    blocks = page.get_text("blocks")
    for b in blocks:
        x0, y0, x1, y1, text, *_ = b
        text = (text or "").strip()
        if not text:
            continue
        # Caption may span lines — look at the first line
        first_line = text.splitlines()[0]
        m = FIG_CAP_RE.match(first_line)
        if m:
            label = m.group(1).strip().rstrip(".")
            caption = text.replace("\n", " ").strip()
            out.append((label, caption, fitz.Rect(x0, y0, x1, y1)))
    return out


def extract_embedded_images(doc, out_dir):
    """Pull embedded raster images; return [{file, page, bbox, area}]."""
    results = []
    counter = 0
    for page_idx, page in enumerate(doc):
        # get_images() returns metadata; we need rect via get_image_rects (PyMuPDF >=1.18)
        try:
            img_infos = page.get_images(full=True)
        except Exception:
            img_infos = []
        for info in img_infos:
            xref = info[0]
            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []
            if not rects:
                continue
            rect = rects[0]
            try:
                pix = fitz.Pixmap(doc, xref)
            except Exception:
                continue
            if pix.width < MIN_W or pix.height < MIN_H:
                pix = None
                continue
            if pix.alpha or pix.colorspace and pix.colorspace.name == "DeviceCMYK":
                pix = fitz.Pixmap(fitz.csRGB, pix)
            counter += 1
            fname = out_dir / f"figure{counter}.png"
            pix.save(str(fname))
            pix = None
            results.append({
                "file": fname.name,
                "page": page_idx + 1,
                "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                "area": rect.width * rect.height,
            })
    return results


def render_cropped(page, rect, out_path, zoom=2.0):
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=rect, alpha=False)
    pix.save(str(out_path))
    return pix.width, pix.height


def captions_without_embedded(doc, embedded, out_dir, start_counter):
    """For each caption with no embedded image of meaningful size on the same
    page above it, render the region from the page top down to the caption.
    """
    results = []
    counter = start_counter
    for page_idx, page in enumerate(doc):
        caps = detect_captions(page)
        if not caps:
            continue
        page_emb = [e for e in embedded if e["page"] == page_idx + 1]
        for label, caption, cap_rect in caps:
            # Has a meaningful embedded image above the caption already?
            already = any(
                e["bbox"][3] <= cap_rect.y0 + 5 and e["area"] > MIN_W * MIN_H
                for e in page_emb
            )
            if already:
                continue
            # Render the region from previous caption / top of page down to this cap
            top = 40
            # If there are other caps above on the same page, start below them
            higher = [c for c in caps if c[2].y1 < cap_rect.y0]
            if higher:
                top = max(c[2].y1 for c in higher) + 10
            clip = fitz.Rect(20, top, page.rect.width - 20, cap_rect.y0 - 2)
            if clip.height < 80 or clip.width < 100:
                continue
            counter += 1
            fname = out_dir / f"figure{counter}.png"
            render_cropped(page, clip, fname, zoom=2.0)
            results.append({
                "file": fname.name,
                "label": label,
                "caption": caption,
                "page": page_idx + 1,
                "bbox": [clip.x0, clip.y0, clip.x1, clip.y1],
                "rendered": True,
            })
    return results, counter


def pair_captions(embedded, doc):
    """Attach a label + caption to each embedded image by nearest caption below it on the same page."""
    out = []
    for e in embedded:
        page = doc[e["page"] - 1]
        caps = detect_captions(page)
        if not caps:
            e["label"] = None
            e["caption"] = ""
            out.append(e)
            continue
        # nearest caption below the image
        nearest = None
        best_dy = 1e9
        for label, cap, rect in caps:
            dy = rect.y0 - e["bbox"][3]
            if 0 <= dy < best_dy:
                best_dy = dy
                nearest = (label, cap)
        if nearest is None:
            # fallback: nearest above
            for label, cap, rect in caps:
                dy = e["bbox"][1] - rect.y1
                if 0 <= dy < best_dy:
                    best_dy = dy
                    nearest = (label, cap)
        e["label"] = nearest[0] if nearest else None
        e["caption"] = nearest[1] if nearest else ""
        out.append(e)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_path", type=Path)
    ap.add_argument("out_dir", type=Path)
    args = ap.parse_args()

    if not args.pdf_path.exists():
        print(f"ERROR: PDF not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(2)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(args.pdf_path))
    embedded = extract_embedded_images(doc, args.out_dir)
    embedded = pair_captions(embedded, doc)
    extra, _ = captions_without_embedded(doc, embedded, args.out_dir, start_counter=len(embedded))
    all_figs = embedded + extra

    # Clean up bbox lists -> simple types
    for f in all_figs:
        f["bbox"] = [round(x, 2) for x in f["bbox"]]
        if "area" in f:
            del f["area"]

    index = args.out_dir / "figures.json"
    index.write_text(json.dumps(all_figs, indent=2, ensure_ascii=False))
    print(str(args.out_dir.resolve()))
    print(f"Extracted {len(all_figs)} figures.")


if __name__ == "__main__":
    main()
