#!/usr/bin/env python3
"""
Extract structured text from an academic PDF.

Usage:
    python3 extract_text.py <pdf_path> <out_json_path>

Emits a JSON object:
{
  "title": str,
  "authors": [str],
  "affiliations": [str],
  "abstract": str,
  "doi": str | null,
  "keywords": [str],
  "sections": [{"heading": str, "text": str, "page": int}],
  "figures_meta": [{"label": str, "caption": str, "page": int}],
  "stats_candidates": [{"number": str, "unit": str, "context_sentence": str}],
  "tables": [{
      "label": str, "caption": str, "page": int,
      "header": [str], "rows": [[str]],
      "numeric_columns": [int],   # column indices that are mostly numeric
      "chart_ready": bool         # has >=1 label column AND >=1 numeric column
  }]
}

Section headings are detected via font-size heuristics (pdfplumber). Figure captions
are detected by lines starting with "Figure N." or "Fig. N.". Stats use regex.
Tables are extracted with pdfplumber's ruled-table detector (`find_tables`); the
`chart_ready` / `numeric_columns` hints let the storyboard step build a `chart`
layout from GROUND-TRUTH values (data_source="table") instead of eyeballing a figure.
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
    sys.exit(1)


DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b", re.IGNORECASE)
FIG_CAP_RE = re.compile(r"^\s*(Fig(?:ure)?\.?\s*\d+[A-Za-z]?)\.?\s*[:.—\-]?\s*(.*)", re.IGNORECASE)
STAT_RE = re.compile(
    r"(?P<num>-?\d+(?:\.\d+)?)\s*(?P<unit>%|°C|°F|°C|°F|×|×|fold|p\s*<\s*0?\.\d+|mg|kg|km|m/s)",
    re.IGNORECASE,
)
TABLE_CAP_RE = re.compile(r"^\s*(Table\s*\d+[A-Za-z]?)\b\.?\s*[:.—\-]?\s*(.*)", re.IGNORECASE)
# A cell that reads as a single number: optional comparator/sign, digits, optional %.
NUMCELL_RE = re.compile(r"^[<>~≈±]?\s*[-+]?\d[\d,]*\.?\d*\s*%?$")
SECTION_KEYWORDS = {
    "abstract", "introduction", "background", "methods", "method",
    "materials and methods", "results", "discussion", "conclusion",
    "conclusions", "acknowledgements", "references", "data availability",
    "keywords",
}


def cluster_lines(page):
    """Return [(text, size, top)] per visual line on the page."""
    chars = page.chars
    if not chars:
        return []
    chars = sorted(chars, key=lambda c: (round(c["top"], 1), c["x0"]))
    lines = []
    cur_top = None
    cur = []
    for c in chars:
        if cur_top is None or abs(c["top"] - cur_top) < 2:
            cur.append(c)
            cur_top = c["top"] if cur_top is None else cur_top
        else:
            if cur:
                text = "".join(ch["text"] for ch in cur).strip()
                size = max(ch["size"] for ch in cur)
                lines.append((text, size, cur_top))
            cur = [c]
            cur_top = c["top"]
    if cur:
        text = "".join(ch["text"] for ch in cur).strip()
        size = max(ch["size"] for ch in cur)
        lines.append((text, size, cur_top))
    return lines


def extract_title(all_lines):
    """The first page's largest-text line, near the top."""
    page0 = all_lines[0] if all_lines else []
    if not page0:
        return ""
    # consider top half of first page
    top_lines = [l for l in page0 if l[2] < 350 and l[0]]
    if not top_lines:
        top_lines = page0
    # largest font wins
    max_size = max(l[1] for l in top_lines)
    title_lines = [l[0] for l in top_lines if l[1] >= max_size - 0.5 and len(l[0]) > 4]
    return " ".join(title_lines[:3]).strip()


def is_heading_candidate(text, size, body_size):
    if not text:
        return False
    t = text.strip()
    if len(t) > 120:
        return False
    lower = t.lower().rstrip(":.")
    # Numbered section like "1. Introduction" or "2 Methods"
    if re.match(r"^\d+(\.\d+)*\.?\s+[A-Z]", t):
        return True
    if lower in SECTION_KEYWORDS:
        return True
    # Title case + bigger than body
    if size > body_size + 0.8 and t[0].isupper() and not t.endswith("."):
        word_count = len(t.split())
        if 1 <= word_count <= 12:
            return True
    return False


def extract_sections(pages_lines):
    """Walk all lines; whenever a heading is detected, start a new section."""
    flat = []
    for page_idx, lines in enumerate(pages_lines):
        for text, size, top in lines:
            flat.append((text, size, page_idx + 1))
    if not flat:
        return []
    body_size = sorted([l[1] for l in flat])[len(flat) // 2]

    sections = []
    cur = {"heading": "_preamble", "text": [], "page": 1}
    for text, size, page in flat:
        if is_heading_candidate(text, size, body_size):
            if cur["text"]:
                cur["text"] = " ".join(cur["text"]).strip()
                sections.append(cur)
            cur = {"heading": text.strip(), "text": [], "page": page}
        else:
            cur["text"].append(text)
    if cur["text"]:
        cur["text"] = " ".join(cur["text"]).strip()
        sections.append(cur)
    return sections


def extract_abstract(sections):
    for s in sections:
        if s["heading"].lower().startswith("abstract"):
            return s["text"]
    return ""


def extract_authors_and_affiliations(pages_lines):
    """Heuristic: lines between title and abstract, on page 1."""
    if not pages_lines:
        return [], []
    page0 = pages_lines[0]
    if not page0:
        return [], []
    # Sort by vertical position
    page0_sorted = sorted(page0, key=lambda l: l[2])
    body_size = sorted([l[1] for l in page0_sorted])[len(page0_sorted) // 2]
    # title is largest; skip until size drops
    seen_title = False
    candidates = []
    for text, size, top in page0_sorted:
        if not text:
            continue
        if not seen_title and size > body_size + 1.5:
            seen_title = True
            continue
        if seen_title:
            if text.lower().startswith("abstract"):
                break
            candidates.append(text)
    authors_raw = " ".join(candidates[:3]) if candidates else ""
    affiliations_raw = " ".join(candidates[3:8]) if len(candidates) > 3 else ""
    # Author names: split on commas / "and"
    authors = []
    if authors_raw:
        parts = re.split(r",| and ", authors_raw)
        for p in parts:
            p = p.strip()
            # strip superscript digits commonly attached to names
            p = re.sub(r"\d+$", "", p).strip()
            if 3 < len(p) < 80 and " " in p:
                authors.append(p)
    affiliations = [affiliations_raw.strip()] if affiliations_raw else []
    return authors, affiliations


def extract_doi(pages_lines):
    for lines in pages_lines:
        for text, _, _ in lines:
            m = DOI_RE.search(text)
            if m:
                return m.group(1)
    return None


def extract_keywords(sections):
    for s in sections:
        if "keyword" in s["heading"].lower():
            kws = re.split(r"[,;]", s["text"])
            return [k.strip() for k in kws if 2 < len(k.strip()) < 40][:12]
    return []


def extract_figure_captions(pages_lines):
    figs = []
    for page_idx, lines in enumerate(pages_lines):
        for text, _, _ in lines:
            m = FIG_CAP_RE.match(text)
            if m:
                label = m.group(1).strip().rstrip(".")
                caption = m.group(2).strip()
                figs.append({"label": label, "caption": caption, "page": page_idx + 1})
    return figs


def _clean_cell(c):
    if not c:
        return ""
    return re.sub(r"\s+", " ", str(c)).strip()


def _is_numeric_cell(s):
    return bool(NUMCELL_RE.match(s.strip())) if s else False


def _table_captions(lines):
    """[(label, caption, top)] for 'Table N ...' lines on one page."""
    caps = []
    for text, _, top in lines:
        m = TABLE_CAP_RE.match(text)
        if m:
            caps.append((m.group(1).strip().rstrip("."), m.group(2).strip(), top))
    return caps


def extract_tables(pdf, pages_lines, max_tables=12, max_rows=40, max_cols=12):
    """Pull ruled tables via pdfplumber.find_tables(), tag numeric columns,
    and pair each with the nearest 'Table N' caption on its page."""
    results = []
    for page_idx, page in enumerate(pdf.pages):
        caps = _table_captions(pages_lines[page_idx]) if page_idx < len(pages_lines) else []
        try:
            found = page.find_tables()
        except Exception:
            found = []
        for t in found:
            try:
                raw = t.extract()
            except Exception:
                continue
            rows = [[_clean_cell(c) for c in row] for row in (raw or [])]
            rows = [r for r in rows if any(r)]  # drop fully-empty rows
            if len(rows) < 2:
                continue
            ncols = min(max(len(r) for r in rows), max_cols)
            rows = [(r + [""] * ncols)[:ncols] for r in rows][:max_rows]
            # drop columns that are empty in every row (pdfplumber padding artifacts)
            keep = [ci for ci in range(ncols) if any(r[ci] for r in rows)]
            if not keep:
                continue
            rows = [[r[ci] for ci in keep] for r in rows]
            ncols = len(keep)

            # caption: nearest 'Table N' line to the table's top edge (within ~140pt)
            label, caption = "", ""
            near = [c for c in caps if abs(c[2] - t.bbox[1]) <= 140]
            if near:
                pick = min(near, key=lambda c: abs(c[2] - t.bbox[1]))
                label, caption = pick[0], pick[1]

            # header: first row if it's mostly non-numeric and the rest carries numbers
            header, body = [], rows
            if sum(_is_numeric_cell(c) for c in rows[0]) <= ncols * 0.3:
                header, body = rows[0], rows[1:]
            if not body:
                continue

            numeric_columns = []
            for ci in range(ncols):
                vals = [r[ci] for r in body if r[ci]]
                if vals and sum(_is_numeric_cell(v) for v in vals) >= 0.6 * len(vals):
                    numeric_columns.append(ci)
            text_columns = [ci for ci in range(ncols) if ci not in numeric_columns]

            results.append({
                "label": label,
                "caption": caption,
                "page": page_idx + 1,
                "header": header,
                "rows": body,
                "numeric_columns": numeric_columns,
                "chart_ready": bool(numeric_columns) and bool(text_columns) and len(body) >= 2,
            })
            if len(results) >= max_tables:
                return results
    return results


def extract_stats(sections):
    results = []
    seen = set()
    for s in sections:
        if not s.get("text"):
            continue
        # Split into sentences (crude)
        sentences = re.split(r"(?<=[.!?])\s+", s["text"])
        for sent in sentences:
            for m in STAT_RE.finditer(sent):
                key = (m.group("num"), m.group("unit").lower())
                if key in seen:
                    continue
                seen.add(key)
                results.append({
                    "number": m.group("num"),
                    "unit": m.group("unit"),
                    "context_sentence": sent.strip()[:400],
                })
                if len(results) > 60:
                    return results
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_path", type=Path)
    ap.add_argument("out_json", type=Path)
    args = ap.parse_args()

    if not args.pdf_path.exists():
        print(f"ERROR: PDF not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(2)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)

    with pdfplumber.open(str(args.pdf_path)) as pdf:
        pages_lines = [cluster_lines(p) for p in pdf.pages]
        tables = extract_tables(pdf, pages_lines)

    title = extract_title(pages_lines)
    sections = extract_sections(pages_lines)
    abstract = extract_abstract(sections)
    authors, affiliations = extract_authors_and_affiliations(pages_lines)
    doi = extract_doi(pages_lines)
    keywords = extract_keywords(sections)
    figures_meta = extract_figure_captions(pages_lines)
    stats = extract_stats(sections)

    payload = {
        "title": title,
        "authors": authors,
        "affiliations": affiliations,
        "abstract": abstract,
        "doi": doi,
        "keywords": keywords,
        "sections": sections,
        "figures_meta": figures_meta,
        "stats_candidates": stats,
        "tables": tables,
    }
    args.out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(str(args.out_json.resolve()))


if __name__ == "__main__":
    main()
