---
name: paper-to-storyboard
description: Convert an academic PDF paper into a single-page scrollytelling website (index.html + style.css + script.js + extracted figures + optional AI cover) using a fixed dark/light scroll-snap chassis. Use when the user provides a PDF and asks for a "storyboard", "scrollytelling page", "paper-to-web", "narrative website", or "convert paper to webpage".
---

# paper-to-storyboard

Turn an academic paper PDF into a dark, scroll-snap, single-page website with the same chassis as the reference example. The chassis (HTML scaffold, CSS layout/animations, vanilla JS IntersectionObserver) is fixed. Only the color palette and per-section content change per paper.

> **Run this skill on a strong model (Opus).** The hard part isn't the scripts — it's the judgement: mapping a paper onto the 9-slot narrative arc, rewriting body copy to fit display type, picking layouts and a palette, and composing the cover concept. Weaker models (e.g. Sonnet) tend to produce flat narratives, mis-assigned layouts, and verbatim-dumped paragraphs. If you're not on Opus, tell the user to switch with `/model opus` before invoking.

## Inputs

- `pdf_path` (required, absolute path)
- `out_dir` (default: `./storyboard/`)
- `palette` (optional: `warm | cool | earth | clinical | tech`) — if omitted, **ask the user** via AskUserQuestion
- `mode` (optional: `dark | light`) — if omitted, **ask the user**
- `typography` (optional: `editorial | modern | tech | academic`) — if omitted, **ask the user**
- `generate_cover` (optional: `true | false`) — if omitted, **ask the user**
- `title_override`, `subtitle_override` (optional)

When any of `palette`, `mode`, `typography`, `generate_cover` is explicitly supplied by the user when they invoke the skill, skip the corresponding question and use the supplied value.

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

### 4. Ask the user for style choices

Before building the storyboard, read enough of the PDF to draft a 1-sentence topic summary, then use **`AskUserQuestion`** to let the user pick the visual style. Show your recommendation as the first option in each list, label it `(Recommended)`, and explain *why* in its description.

Issue these questions in a **single `AskUserQuestion` call** (batch them — don't ask one at a time):

1. **Palette** — 4 options out of `warm`, `cool`, `earth`, `clinical`, `tech` (recommended first, then 3 sensible alternatives for this paper).
   - Keyword guide for the recommendation: heat/energy/fire → `warm`; water/climate/ocean → `cool`; biology/ecology/agriculture/plants → `earth`; medicine/clinical/health/disease → `clinical`; computing/AI/ML/robotics → `tech`. Urban / cities / sociology papers often fit `cool` or `earth`. Default `warm`.

2. **Mode** — 2 options: `dark`, `light`.
   - Default `dark` (matches the reference chassis identity, more cinematic). Recommend `light` only when the paper is text-heavy with few or busy figures where readability dominates.

3. **Typography** — 4 options: `editorial`, `modern`, `tech`, `academic`.
   - Keyword guide for the recommendation: longform/humanities/policy → `editorial`; product / startup / design → `modern`; CS / AI / engineering → `tech`; medicine / scholarly / journal → `academic`.

4. **Generate cover?** — 2 options: `Generate (~$0.04)`, `Skip`.
   - In the `Generate` option's description, show the 1-sentence cover concept you'd send to the image model so the user can preview what they'd be paying for.
   - Recommend `Generate` if `OPENAI_API_KEY` is set, otherwise `Skip`.

Use the user's answers in the steps below. If the user picks `Skip` for cover, omit step 5 and don't add `cover_image` to the title section.

### 5. (Optional) Generate the title cover image

Only if the user picked `Generate` in step 4. Compose a 1-sentence `--concept` describing the paper:

```
python3 ~/.claude/skills/paper-to-storyboard/scripts/generate_cover.py \
  --concept "<one-sentence paper description>" \
  --palette <chosen palette> \
  --mode <dark|light> \
  --out <out_dir>/cover.png
```

Calls OpenAI `gpt-image-1` (~$0.04 medium, $0.25 high — defaults to medium). To preview the prompt without spending: add `--prompt-only`.

When `cover.png` exists in `out_dir` AND the title section in `storyboard.json` has `"cover_image": "cover.png"`, render.py automatically inlines it as the title-bg with a palette-tinted gradient overlay. If either is missing, the title slot falls back to the default gradient.

If `OPENAI_API_KEY` isn't set, generation will fail with a clear error — fall back to skipping the cover and proceed.

### 6. Map content to storyboard slots

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

### 7. Emit the site

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

### 8. Preview

```
python3 ~/.claude/skills/paper-to-storyboard/scripts/preview.py <out_dir>
```

Prints `http://localhost:8765/` and opens it on macOS.

## Reference

A fully filled `storyboard.json` example ships in this skill: `examples/reference_storyboard.json`. Additional rendered examples live under `examples/` in the repo (https://github.com/MaoranSun/paper-to-storyboard).

## Dependencies

```
pip install pdfplumber pymupdf pillow
# Optional, for background removal of complex figures:
pip install rembg
```
