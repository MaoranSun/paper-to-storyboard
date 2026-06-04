#!/usr/bin/env python3
"""
Render storyboard.json + palette/mode/typography into index.html + style.css + script.js.

Usage:
    python3 render.py --storyboard <storyboard.json> --palette <name> \
        [--mode dark|light] [--typography editorial|modern|tech|academic] --out <dir>

Templates live in ../templates/; presets live in ../palettes/themes.json.
"""

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "templates"
PRESETS_FILE = SKILL_ROOT / "palettes" / "themes.json"


def load_snippets():
    raw = (TEMPLATES / "section_snippets.html").read_text()
    pattern = re.compile(
        r"<!-- LAYOUT: (\w+) -->\s*(.*?)\s*<!-- END LAYOUT: \1 -->",
        re.DOTALL,
    )
    return {m.group(1): m.group(2) for m in pattern.finditer(raw)}


def fill(template: str, mapping: dict) -> str:
    """Replace {{KEY}} with mapping[key]; unknown keys raise."""
    def sub(m):
        key = m.group(1).strip()
        if key not in mapping:
            raise KeyError(f"Unfilled placeholder: {{{{{key}}}}}")
        return str(mapping[key])
    return re.sub(r"\{\{(\w+)\}\}", sub, template)


ACCENT_CYCLE = ["warm", "extreme", "cool", "caution"]


def _stat_items_html(items):
    out = []
    for it in items or []:
        modifier = (it.get("accent") or "").strip()
        cls = "stat-item" + (f" {modifier}" if modifier else "")
        out.append(
            f'            <div class="{cls}">\n'
            f'                <span class="stat-number">{it.get("number","")}</span>\n'
            f'                <span class="stat-label">{it.get("label","")}</span>\n'
            f'            </div>'
        )
    return "\n".join(out)


def _columns_html(columns):
    out = []
    for i, c in enumerate(columns or []):
        modifier = (c.get("accent") or ACCENT_CYCLE[i % len(ACCENT_CYCLE)]).strip()
        cls = f"comparison-column {modifier}".strip()
        out.append(
            f'            <div class="{cls}">\n'
            f'                <h3>{c.get("heading","")}</h3>\n'
            f'                <p>{c.get("body","")}</p>\n'
            f'            </div>'
        )
    return "\n".join(out)


def render_section(snippets, section, idx, out_dir):
    layout = section.get("layout", "split")
    if layout not in snippets:
        raise ValueError(f"Unknown layout: {layout}")
    tmpl = snippets[layout]
    m = {
        "N": str(idx),
        "THEME": section.get("theme", "warm"),
        "HEADING": section.get("heading", ""),
        "SUBTITLE": section.get("subtitle", ""),
        "BODY": section.get("body", ""),
        "FIGURE": section.get("figure", ""),
        "FIGURE_ALT": section.get("figure_alt", section.get("heading", "")),
        "IMAGE_CLASS": section.get("image_class", "content-image"),
        "DEFINITION": section.get("definition", ""),
        "BIG_NUMBER_A": section.get("big_number_a", ""),
        "STAT_DESC_A": section.get("stat_desc_a", ""),
        "BIG_NUMBER_B": section.get("big_number_b", ""),
        "STAT_DESC_B": section.get("stat_desc_b", ""),
        "CAPTION": section.get("caption", ""),
        "CTA": section.get("cta", ""),
        "QUOTE": section.get("quote", ""),
        "ATTRIBUTION": section.get("attribution", ""),
        "STAT_ITEMS": _stat_items_html(section.get("stat_items", [])),
        "COLUMNS": _columns_html(section.get("columns", [])),
        "AUTHORS": section.get("authors", ""),
        "AFFILIATIONS": section.get("affiliations", ""),
        "DOI_URL": section.get("doi_url", ""),
    }
    if "INSIGHT_BLOCK" in tmpl:
        insight = section.get("insight", "")
        m["INSIGHT_BLOCK"] = (
            f'<div class="key-insight animate-text delay-2">{insight}</div>'
            if insight else ""
        )
    if "COVER_STYLE" in tmpl:
        cover = section.get("cover_image", "")
        if cover and (out_dir / cover).exists():
            m["COVER_CLASS"] = " has-cover"
            m["COVER_STYLE"] = (
                f' style="background-image: linear-gradient('
                f'var(--title-overlay-from), var(--title-overlay-to)), '
                f"url('{cover}'); background-size: cover; background-position: center;\""
            )
        else:
            m["COVER_CLASS"] = ""
            m["COVER_STYLE"] = ""
    return fill(tmpl, m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--storyboard", type=Path, required=True)
    ap.add_argument("--palette", required=True,
                    choices=["warm", "cool", "earth", "clinical", "tech"])
    ap.add_argument("--mode", default="dark", choices=["dark", "light"])
    ap.add_argument("--typography", default="editorial",
                    choices=["editorial", "modern", "tech", "academic"])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    if not args.storyboard.exists():
        print(f"ERROR: storyboard not found: {args.storyboard}", file=sys.stderr)
        sys.exit(2)
    args.out.mkdir(parents=True, exist_ok=True)

    storyboard = json.loads(args.storyboard.read_text())
    presets = json.loads(PRESETS_FILE.read_text())
    palettes = presets["palettes"]
    if args.palette not in palettes:
        print(f"ERROR: unknown palette: {args.palette}", file=sys.stderr)
        sys.exit(2)
    palette = palettes[args.palette]
    mode_bgs = palette[args.mode]
    mode_chassis = presets["modes"][args.mode]
    typo = presets["typography"][args.typography]

    snippets = load_snippets()

    doi_url = storyboard.get("doi_url", "")
    for s in storyboard.get("sections", []):
        if s.get("layout") == "credits" and "doi_url" not in s:
            s["doi_url"] = doi_url

    sections_html = "\n".join(
        "        " + render_section(snippets, s, i, args.out).replace("\n", "\n        ")
        for i, s in enumerate(storyboard["sections"])
    )

    # index.html
    html_tmpl = (TEMPLATES / "index.html.tmpl").read_text()
    html = fill(html_tmpl, {
        "PAGE_TITLE": storyboard.get("page_title", "Paper Storyboard"),
        "FONTS_URL": typo["fonts_url"],
        "SECTIONS": sections_html,
    })
    (args.out / "index.html").write_text(html)

    # style.css
    css_tmpl = (TEMPLATES / "style.css.tmpl").read_text()
    css = fill(css_tmpl, {
        # palette bg
        "BG_TITLE":      mode_bgs["bg_title"],
        "BG_WARM":       mode_bgs["bg_warm"],
        "BG_NEUTRAL":    mode_bgs["bg_neutral"],
        "BG_TECH":       mode_bgs["bg_tech"],
        "BG_DATA":       mode_bgs["bg_data"],
        "BG_ALERT":      mode_bgs["bg_alert"],
        "BG_INSIGHT":    mode_bgs["bg_insight"],
        "BG_GLOW_INNER": mode_bgs["bg_glow_inner"],
        "BG_GLOW_BAND":  mode_bgs["bg_glow_band"],
        # palette accents (same across modes)
        "ACCENT_WARM":    palette["accent_warm"],
        "ACCENT_COOL":    palette["accent_cool"],
        "ACCENT_CAUTION": palette["accent_caution"],
        "ACCENT_EXTREME": palette["accent_extreme"],
        # mode chassis
        "TEXT_PRIMARY":       mode_chassis["text_primary"],
        "TEXT_SECONDARY":     mode_chassis["text_secondary"],
        "SUBTITLE_COLOR":     mode_chassis["subtitle_color"],
        "OVERLAY_SOFT":       mode_chassis["overlay_soft"],
        "OVERLAY_MED":        mode_chassis["overlay_med"],
        "OVERLAY_LITE":       mode_chassis["overlay_lite"],
        "OVERLAY_BORDER":     mode_chassis["overlay_border"],
        "TITLE_OVERLAY_FROM": mode_chassis["title_overlay_from"],
        "TITLE_OVERLAY_TO":   mode_chassis["title_overlay_to"],
        "BTN_BG":             mode_chassis["btn_bg"],
        "BTN_FG":             mode_chassis["btn_fg"],
        "NOISE_OPACITY":      mode_chassis["noise_opacity"],
        "SHIMMER_FROM":       mode_chassis["shimmer_from"],
        "SHIMMER_TO":         mode_chassis["shimmer_to"],
        "PANEL_BG":           mode_chassis["panel_bg"],
        "PANEL_BORDER":       mode_chassis["panel_border"],
        # typography
        "FONT_DISPLAY":  typo["display"],
        "FONT_BODY":     typo["body"],
    })
    (args.out / "style.css").write_text(css)

    # script.js — themes map keyed by section-N → bg color for chosen mode
    themes_map = {}
    palette_themes = mode_bgs["themes"]
    for i, s in enumerate(storyboard["sections"]):
        theme = s.get("theme", "warm")
        themes_map[f"section-{i}"] = palette_themes.get(theme, mode_bgs["bg_warm"])

    js_tmpl = (TEMPLATES / "script.js.tmpl").read_text()
    js = fill(js_tmpl, {
        "THEMES_JSON": json.dumps(themes_map, indent=8)[:-1] + "    }"
    })
    (args.out / "script.js").write_text(js)

    print(str(args.out.resolve()))
    print(f"palette={args.palette} mode={args.mode} typography={args.typography}")


if __name__ == "__main__":
    main()
