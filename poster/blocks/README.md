# Poster blocks

Each block's text lives in its own file here, pulled into `../poster.qmd` with
`{{< include blocks/<name>.qmd >}}`. Several people or sessions can write
blocks in parallel without conflicts in `poster.qmd`.

## Space budget (set 2026-11-23 from a render with dummy text)

A column is 11.8 in wide (figures are drawn at that width by
`scripts/poster_style.py`) and about 30.8 in tall below the header. Body text
is 32 pt: about 9 words per line, and 100 words take about 5 in. A block's
title, rule and padding take about 1.5 in, plus a 0.6 in gap between blocks.

| Column | Block | File | Words | Figure (in) | Issue |
|---|---|---|---:|---|---|
| 1 | Key Points | `key-points.qmd` | 3 × 1 line | — | #14 |
| 1 | Introduction | `introduction.qmd` | 70 | — | #13 |
| 1 | Data | `data.qmd` | 50 | 11.8 × 4.5 map | #9 |
| 1 | Methods | `methods.qmd` | 90 | — | #8 |
| 2 | Data leakage and split design | `leakage.qmd` | 90 | 11.8 × 6.5 | #20 |
| 2 | 1. Does hyperspectral help? | `hyperspectral.qmd` | 90 | 11.8 × 6.0 | #10 |
| 3 | 2. Is there hope for coastal regions? | `coastal.qmd` | 70 | 11.8 × 5.5 | #11 |
| 3 | Relation to existing approaches | `existing-approaches.qmd` | 30 + 6-row table | — | #12 |
| 3 | Next Steps | `next-steps.qmd` | 50 | — | #15 |
| 3 | References | in `poster.qmd` | — | — | #16 |
| 3 | Acknowledgements | `acknowledgements.qmd` | 25 | — | #16 |

Columns 1 and 2 fill exactly. **Column 3 is about 5 in over** once References and
Acknowledgements are included, and the real reference list will be longer than
the two placeholder entries. Not yet decided (Eli). Ways to make room:

- a two-line title (the header spans all columns, so each column gains about 2 in);
- Acknowledgements as one line in the footer;
- a short reference list, with the full list behind the QR code / website.

`conclusions.qmd` is kept but left out of `poster.qmd`: Key Points carry the
conclusions (Eli to decide).

## Rules

- Keep within the budget, then render (`make poster`) and check that
  `poster.pdf` is one page (`pdfinfo poster.pdf | grep Pages`).
- Figures come from a script in `../scripts/`, drawn at the budgeted size.
  When a block's real figure exists, point the block at it and remove its
  placeholder from `scripts/fig_placeholders.py` and `figures/`.
- The table in `existing-approaches.qmd` renders in Typst's default style
  (small, boxed); it needs styling when the real table goes in.
