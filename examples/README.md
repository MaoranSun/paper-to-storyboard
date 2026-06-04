# Examples

End-to-end outputs of the `paper-to-storyboard` skill — clone, browse, learn from. Each example is a self-contained directory you can open in a browser or serve with `python3 -m http.server`.

## Per-example layout

Each subdirectory should follow this shape:

```
examples/<paper-shortname>/
├── README.md             # 1-paragraph: what the paper is + style choices used
├── index.html            # rendered chassis
├── style.css             # palette + mode + typography injected
├── script.js             # IntersectionObserver
├── cover.png             # AI-generated title cover (optional)
├── figure1.png …         # transparent PNGs lifted from the paper
├── storyboard.json       # the editable narrative — re-render after edits
└── (optional) source.pdf # source paper if license permits
```

The `storyboard.json` + the chosen `--palette` / `--mode` / `--typography` are enough to reproduce the rest:

```bash
../../skill/scripts/render.py \
  --storyboard ./storyboard.json \
  --palette <name> --mode <dark|light> --typography <preset> \
  --out .
```

## Live preview

From the repo root:

```bash
python3 skill/scripts/preview.py examples/<paper-shortname> 8765
# then open http://localhost:8765/
```

## Adding an example

1. Run the skill on a PDF (Claude Code: `convert /path/to/paper.pdf to a storyboard`).
2. Copy the output dir into `examples/<short-name>/`.
3. Strip anything you don't want public (`content.json` / `figures/` raw extraction can be deleted if you just want the polished output).
4. Add a 1-paragraph `README.md` in the example dir noting the style combo and the paper citation.
5. Confirm copyright of any included `source.pdf` before committing.
