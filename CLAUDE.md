# paper-to-storyboard

This repo *is* the source of the `paper-to-storyboard` Claude Code Skill. The skill turns an academic PDF into a dark scroll-snap webpage (HTML + CSS + vanilla JS + transparent figures + AI cover).

## Layout

```
paper-to-storyboard/        (this repo — the canonical source of truth)
├── skill/                  # the skill itself; copied/symlinked to ~/.claude/skills/
│   ├── SKILL.md
│   ├── templates/          # index.html.tmpl, style.css.tmpl, script.js.tmpl, section_snippets.html
│   ├── scripts/            # extract_text, extract_figures, make_transparent, generate_cover, render, preview
│   ├── palettes/themes.json
│   ├── schemas/storyboard.schema.json
│   └── examples/reference_storyboard.json
├── examples/               # rendered storyboards (one self-contained dir per paper)
│   └── <paper-shortname>/  # index.html, style.css, script.js, figures, cover
├── install.sh              # copies ./skill/ → ~/.claude/skills/paper-to-storyboard/
├── requirements.txt
├── README.md               # public-facing
├── LICENSE                 # MIT
└── CLAUDE.md               # this file
```

**Edits to the skill should be made in `./skill/` in this repo, then re-installed** via `./install.sh` (or use `./install.sh --symlink` once so edits go live without re-running). Do not edit `~/.claude/skills/paper-to-storyboard/` directly — that's the install target.

## What the skill produces

For any PDF, the pipeline emits:

```
<out_dir>/
├── content.json             # extracted text (sections, abstract, stats, DOI)
├── figures/figureN.png      # raw figures + figures.json (captions, page, bbox)
├── figureN.png              # transparent versions
├── cover.png                # optional AI-generated title cover (OpenAI gpt-image-1)
├── storyboard.json          # 7-9 slot narrative (Claude writes this)
├── index.html               # rendered chassis
├── style.css                # palette + mode + typography injected
└── script.js                # IntersectionObserver, themes map
```

## How to run

```bash
PY=.venv/bin/python3
SKILL=./skill
PDF=/path/to/paper.pdf
OUT=/path/to/out

$PY $SKILL/scripts/extract_text.py    $PDF $OUT/content.json
$PY $SKILL/scripts/extract_figures.py $PDF $OUT/figures/
for f in $OUT/figures/figure*.png; do
  $PY $SKILL/scripts/make_transparent.py "$f" "$OUT/$(basename "$f")"
done
$PY $SKILL/scripts/generate_cover.py --concept "..." --palette cool --mode dark --out $OUT/cover.png
# Claude builds $OUT/storyboard.json from content.json + figures.json
$PY $SKILL/scripts/render.py --storyboard $OUT/storyboard.json --palette cool --mode dark --typography academic --out $OUT
$PY $SKILL/scripts/preview.py $OUT 8765
```

## Style knobs

- **palettes**: `warm | cool | earth | clinical | tech`
- **modes**: `dark | light` (each palette has both)
- **typography**: `editorial` (Playfair + Inter), `modern` (Space Grotesk + Inter), `tech` (JetBrains Mono + Inter), `academic` (Crimson Pro + Source Sans)
- **layouts**: `title`, `split`, `split_reverse`, `split_no_image`, `stacked`, `quote`, `impact`, `impact_single`, `stats_grid`, `comparison`, `insight`, `credits`. (`fullbleed` exists but is reserved for atmospheric photos — **do not use it for paper figures**.)

## Conventions

- **Chassis is fixed.** Per-paper variation = palette + mode + typography + per-section content + AI cover. Do not regenerate `style.css`/`script.js` freeform; always go through `render.py`.
- **Narrative arc** has 9 fixed slots: title → hook → problem → method → keyFinding → dataNarrative → secondaryFinding → insight → credits. Slot 6 is skippable when a paper has only one main result.
- **Figures are transparent PNGs** so they blend into the dark/light section backgrounds. `make_transparent.py` uses corner flood-fill by default; pass `--mode rembg` for photos/schematics.
- **Body copy is rewritten** to fit display type (1.2rem). Headline numbers and key definitions are lifted verbatim from the paper.
- **No fullbleed for paper figures** — scientific charts don't read well at viewport scale; use `split`, `split_reverse`, or `stacked` instead.

## Dependencies

```
pip install -r requirements.txt
# pdfplumber, pymupdf, pillow (required)
# openai (optional, for cover generation)
# rembg (optional, for complex-figure bg removal)
```
