# AGU26 poster

Poster for AGU26, session A43L (Thursday 10 December 2026, 14:15–17:45 PST,
Moscone Center Halls ABC). Planning is in issue #1.

The poster is written in plain Markdown in `poster.qmd` and rendered by Quarto
through Typst to a 42 × 42 in PDF. The AGU maximum is 44 × 44 in, and boards are
shared, so we leave a margin. Every figure is made by a script in `scripts/`, and
its caption links to that script.

## Build

You need [Quarto](https://quarto.org) 1.5 or later, which includes Typst; no LaTeX
is needed. For the figure scripts, you also need the Python packages in
`requirements.txt`.

```bash
cd poster
pip install -r requirements.txt   # once
make                              # run the figure scripts, then render poster.pdf
make poster                       # render only, using the figures already in figures/
```

To rebuild one figure, run its script, e.g. `python scripts/fig_example_profiles.py`.

The generated figures are committed, so the poster renders without rerunning
slow scripts. `poster.pdf` is not committed.

## Files

| Path | What it is |
| --- | --- |
| `poster.qmd` | The poster: title, authors and settings in the YAML header, then one block per section |
| `scripts/` | One script per figure. `poster_style.py` holds the shared figure size and fonts |
| `figures/` | Output of `scripts/`, embedded by `poster.qmd` |
| `references.bib` | References cited with `[@key]` |
| `fonts/` | Roboto (Apache-2.0), bundled so the poster looks the same on any machine |
| `_extensions/poster/` | The Typst layout (`typst-template.typ`) and the filter that turns the Markdown below into it (`poster.lua`) |

## Writing the poster

```markdown
::: {.block title="Methods"}
Text, lists, citations [@sauzede2015], and figures go inside a block.
:::

::: {.block .highlight title="Key Points"}
An accent-colored block.
:::

::: {.colbreak}
:::
```

- Blocks flow down a column. A block never splits across columns. Use
  `::: {.colbreak}` to start the next column.
- To add a figure, write a script in `scripts/` that saves it to `figures/`,
  then embed it:

  ```markdown
  ![Caption.](figures/fig_x.png){#fig-x script="scripts/fig_x.py" width="100%"}
  ```

  The `script=` attribute adds "Code: scripts/fig_x.py" to the caption, linked
  to the script on GitHub (`code-base-url` in the YAML header). Refer to the
  figure in the text with `@fig-x`.
- Draw figures at their printed size so their fonts match the poster. One column
  is 11.8 in wide (`COLUMN_WIDTH_IN` in `scripts/poster_style.py`). Poster text
  is 32 pt, and figure labels are about 22–28 pt.
- References go wherever `::: {#refs}` is placed, in AGU style.
- Poster size, number of columns and body font size can be set in the YAML header
  with `poster-width`, `poster-height`, `poster-columns` and `fontsize`. Colors
  are set at the top of `_extensions/poster/typst-template.typ`.
