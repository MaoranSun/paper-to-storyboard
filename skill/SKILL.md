---
name: paper-to-storyboard
description: Convert an academic PDF paper into a single-page scrollytelling website (index.html + style.css + script.js + extracted figures) styled like the reference at /Users/maoransun/GitHub/paper_2_html/reference/. Use when the user provides a PDF and asks for a "storyboard", "scrollytelling page", "paper-to-web", "narrative website", or "convert paper to webpage".
---

# paper-to-storyboard

Turn an academic paper PDF into a dark, scroll-snap, single-page website with the same chassis as the reference example. The chassis (HTML scaffold, CSS layout/animations, vanilla JS IntersectionObserver) is fixed. Only the color palette and per-section content change per paper.

## Inputs

- `pdf_path` (required, absolute path)
- `out_dir` (default: `./storyboard/`)
- `palette` (optional: `warm | cool | earth | clinical | tech`; auto-derived from topic if omitted)
- `mode` (optional: `dark | light`; default `dark`)
- `typography` (optional: `editorial | modern | tech | academic`; default `editorial`)
- `title_override`, `subtitle_override` (optional)

### Style options

- **palette** — color family. Auto-pick from topic keywords; explicit `palette` arg wins.
- **mode** — `dark` keeps the reference chassis (white-on-dark with animated gradient + noise). `light` flips text to near-black, bg to light tints of the palette, button colors, overlays, and animation opacities.
- **typography** — font pairing:
  - `editorial`: Playfair Display + Inter (default — newspaper/longform feel)
  - `modern`: Space Grotesk + Inter (clean, product-design)
  - `tech`: JetBrains Mono + Inter (engineering / lab notebook)
  - `academic`: Crimson Pro + Source Sans (journal / scholarly)

## Workflow

Execute these steps in order. The skill directory is `~/.claude/skills/paper-to-storyboard/`. Run each script with absolute paths.

### 1. Ingest PDF text

```
python3 ~/.claude/skills/paper-to-storyboard/scripts/extract_text.py <pdf_path> <out_dir>/content.json
```

Produces `content.json` with `{title, authors, affiliations, abstract, doi, keywords, sections[], figures_meta[], stats_candidates[]}`.

### 2. Extract figures

```
python3 ~/.claude/skills/paper-to-storyboard/scripts/extract_figures.py <pdf_path> <out_dir>/figures/
```

Produces `figures/figure1.png` … `figureN.png` and `figures/figures.json` with captions, page numbers, bboxes.

### 3. Make figures transparent

For each figure that will appear in the page (typically all of them):

```
python3 ~/.claude/skills/paper-to-storyboard/scripts/make_transparent.py <out_dir>/figures/figureN.png <out_dir>/figureN.png
```

This writes transparent PNGs directly into `out_dir/` (alongside the templates), where the HTML references them. The default mode is corner flood-fill (good for plot figures with white backgrounds). For photos/schematics, pass `--mode rembg`. If `rembg` isn't installed, it falls back to the flood-fill mode with a warning.

### 3b. (Optional) Generate a title cover image

If `OPENAI_API_KEY` is set in the env, generate a stylized data-art cover for the title slot. Compose a 1-sentence `--concept` describing the paper:

```
python3 ~/.claude/skills/paper-to-storyboard/scripts/generate_cover.py \
  --concept "<one-sentence paper description>" \
  --palette <chosen palette> \
  --mode <dark|light> \
  --out <out_dir>/cover.png
```

This calls OpenAI `gpt-image-1` (~$0.04 medium, $0.25 high — defaults to medium). The script wraps the concept into an abstract data-art prompt tinted toward the chosen palette + mode. To preview the prompt without spending: add `--prompt-only`.

When `cover.png` exists in `out_dir` AND the title section in `storyboard.json` has `"cover_image": "cover.png"`, render.py automatically inlines it as the title-bg with a palette-tinted gradient overlay. If either is missing, the title slot falls back to the default gradient.

If `OPENAI_API_KEY` isn't set, skip this step — the title slot still works.

### 4. Map content to storyboard slots

Read `content.json` and `figures/figures.json`. Build a storyboard JSON object matching `schemas/storyboard.schema.json`. Save as `<out_dir>/storyboard.json`.

The schema has **9 fixed slots** (you may skip slot 6 if the paper has only one main result):

| Slot | Suggested layout(s) | Maps to |
|------|---------------------|---------|
| 0 — title | `title` | Paper title (rewritten as a hook), 1-line subtitle from abstract |
| 1 — hook | `split`, `quote` | First paragraph of Introduction ("why now") |
| 2 — problem | `split`, `split_reverse`, `quote` | The gap/limitation paragraph |
| 3 — method | `split`, `split_reverse`, `stacked` | One-line methods + schematic figure |
| 4 — keyFinding | `impact`, `impact_single`, `stats_grid` | Headline number(s) |
| 5 — dataNarrative | `split`, `stacked` | Main results figure + body + insight callout |
| 6 — secondaryFinding | `split_reverse`, `comparison` | Temporal/subgroup result or A-vs-B contrast (skippable) |
| 7 — insight | `insight`, `quote` | Discussion takeaway, call-to-action or pull quote |
| 8 — credits | `credits` | Authors, affiliations, DOI link |

### Layout catalogue

- **`title`** — hero. Big heading + subtitle, optional `cover_image` background.
- **`split`** — text-left, figure-right (default workhorse).
- **`split_reverse`** — figure-left, text-right (alternate to break rhythm).
- **`split_no_image`** — text-only with optional `insight` callout.
- **`stacked`** — figure on top, text below. For wide/panoramic figures.
- **`fullbleed`** — figure fills the section as background, text overlays in a glass panel. **Avoid for paper figures** — most scientific charts don't read well at viewport scale and the glass panel competes with the data. Reserved for the rare atmospheric photo or hero rendering (not for plots/maps/diagrams from a paper).
- **`quote`** — large italic pull-quote with attribution. Lift a striking sentence verbatim.
- **`impact`** — two big numbers vs. each other.
- **`impact_single`** — one big number with a caption.
- **`stats_grid`** — 3–4 metric cards (`stat_items: [{number, label, accent}]`).
- **`comparison`** — two/three side-by-side text columns (`columns: [{heading, body, accent}]`).
- **`insight`** — discussion takeaway with a call-to-action box.
- **`credits`** — authors + affiliations + DOI button.

`accent` modifiers (for `stats_grid` cards and `comparison` columns): `warm`, `cool`, `caution`, `extreme`. Empty = default.

Rules for filling slots:
- Rewrite paper prose into 1–3 short sentences per slot (paper prose is too dense for 1.2rem display type).
- Lift headline numbers and key definitions **verbatim** from the paper.
- For slot 4, the two big numbers should be a meaningful comparison (e.g., baseline vs treatment, outdoor vs indoor). If the paper has no natural comparison, use a single big number and one short descriptor.
- For each split-layout slot, pick a figure from `figures.json` by relevance (use the caption to judge). Same figure should not be reused across slots.
- If the paper has fewer than 4 figures, some split-layout slots become bare (drop the image_content div).

### 5. Pick a theme

Look at `palettes/themes.json`. Choose a palette:
- If `theme_hint` was supplied, use it.
- Otherwise match topic keywords from title/abstract/keywords:
  - heat, energy, fire, combustion → `warm`
  - water, climate, ocean, atmospheric → `cool`
  - biology, ecology, agriculture, plant, soil → `earth`
  - medicine, clinical, health, disease, patient → `clinical`
  - computing, AI, machine learning, software, robotics → `tech`
- Default: `warm`.

### 6. Emit the site

Copy the templates and substitute placeholders:

```
python3 ~/.claude/skills/paper-to-storyboard/scripts/render.py \
  --storyboard <out_dir>/storyboard.json \
  --palette <name> \
  [--mode dark|light] \
  [--typography editorial|modern|tech|academic] \
  --out <out_dir>
```

This writes `index.html`, `style.css`, `script.js` to `out_dir`. The transparent figures (step 3) should already be in `out_dir`.

### 7. Preview

```
python3 ~/.claude/skills/paper-to-storyboard/scripts/preview.py <out_dir>
```

Prints `http://localhost:8765/` and opens it on macOS.

## Reference

The canonical example this chassis is derived from:

- `/Users/maoransun/GitHub/paper_2_html/reference/index.html`
- `/Users/maoransun/GitHub/paper_2_html/reference/style.css`
- `/Users/maoransun/GitHub/paper_2_html/reference/script.js`
- `/Users/maoransun/GitHub/paper_2_html/reference/rsta.2024.0567.pdf`

A fully filled `storyboard.json` example: `examples/reference_storyboard.json`.

## Dependencies

```
pip install pdfplumber pymupdf pillow
# Optional, for background removal of complex figures:
pip install rembg
```
