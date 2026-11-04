# AGU26 poster: decisions

Session A43L, Thursday 10 December 2026, 14:15–17:45 PST, Moscone Halls ABC.
The poster board number arrives by email in mid-November 2026.

## Decisions (Eli, 2026-11-03)

- **Quarto → Typst**, not MyST, HTML/CSS or LaTeX. The source should be plain
  text that renders to a print-ready PDF.
- **Location:** `poster/` in this repo.
- **Figures are reproducible:** each one is made by a script you can read.
  Captions link to the script; the plotting code is not in the `.qmd`.
- **Order of work:** setup (#2), then the story (#3), then Eli works through
  the blocks one at a time (#4).

## Design choices made while building #2

- **42 × 42 in, not the 44 × 44 in maximum:** AGU26 boards are shared between
  two presenters, so leave a margin.
- **Figure scripts are a separate step** (`make figures`), not Quarto
  `pre-render`, because real figure scripts will be slow. Generated figures are
  committed; `poster.pdf` is not.
- **Figures are drawn at printed size** (one column is 11.8 in, at 300 dpi), so
  font sizes in points match the poster. The width is set in
  `scripts/poster_style.py` and has to stay in step with the column math in
  `typst-template.typ`: (42 − 2 margin − 2 × 0.7 gutter) / 3 − 2 × 0.5 inset.
- **Roboto is bundled in `poster/fonts/`.** With system fonts, Typst on the hub
  chose Roboto *Condensed* for "Roboto", and other machines would fall back to
  something else.
- **Hand-written Typst template** in `_extensions/poster/`, not the
  `peace-of-posters` package. It needs no package download at render time and
  is about 100 lines.

## Things that look odd but are deliberate

- `poster.lua` runs `at: pre-ast`. Later than that, Quarto has already turned
  `#fig-` figures into its own node type, and the "Code:" caption link
  silently doesn't appear.
- `poster.lua` passes `qr:` to Typst as raw text, because otherwise pandoc
  escapes `qr_code.svg` to `qr\_code.svg`.
- `biblio.typ` is empty on purpose. The bibliography goes where `::: {#refs}`
  is, inside the References block, not at the end of the document.
- Authors' affiliations in the YAML must use `- ref: <id>`. A bare list like
  `[noaa, uw]` makes new affiliations named "noaa" and "uw".

## Open

- Authors: only Eli is real so far. Whether and how hackweek participants are
  co-authors is Eli's call (#3).
- The sections are the standard set (Key Points, Introduction, Objectives,
  Data, Methods, Results, Conclusions, Next Steps, References,
  Acknowledgements), with dummy text. #3 decides the actual blocks.
- Logos: none yet. The header has a QR code to the CHLA-Z website on the right.
