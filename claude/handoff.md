# Handoff

Rolling session state for agents working in this repo. Read this first.

## Repo

Materials from the 2026 GO-BGC Hackweek CHLA-Z project (Aug 18–21, 2026), run
by Eli Holmes, and now the AGU26 poster built from that work. The hackweek
itself ran on a separate hackweek JupyterHub. Work left uncommitted there was
pushed on 2026-11-03 (`contributor_folders/eli/level-2.ipynb`, the final
presentation, and the AGU abstract in `final_notebooks/`).

The model code and the CHLA-Z product live in other repos: fish-pace/chla-z-modeling
and fish-pace/chla-z (website: https://fish-pace.github.io/chla-z/).

## Current work: AGU26 poster (issue #1)

- #2 Setup: done (PR #5, merged). Build with `make` in `poster/`.
- #3 Story: agreed 2026-11-04, in `poster/STORY.md`. Fix train/test leakage,
  then (1) does hyperspectral help? (no), and (2) is there hope for coastal
  regions? Plus a "relation to existing approaches" block on the Copernicus
  SOCA2024 product.
- #4 Blocks: split into #7–#16. **#7 (data fixes) comes first.** #7 is waiting
  on two answers from Eli: whether the fixes go into fish-pace/fish-pace-datasets
  and fish-pace/chla-z (each needs her OK) or into poster-only tables here, and
  where Jodi's data work lives.
- #6 holds Eli's SOCA/Sauzède references for block #12.

The story PR (#17, which also brought in Nabir's `nama` branch: OLCI matchups,
PACE-vs-OLCI comparison, prediction intervals) was merged to `main` on 2026-11-05.

Notes:
- [notes/poster.md](notes/poster.md): how the poster is built and why.
- [notes/hackweek-experiments.md](notes/hackweek-experiments.md): what each
  hackweek participant tested and found, where the code is, and the SOCA2024
  facts. SOCA2024 uses 5-band Rrs, not surface Chl, and its weekly fields end
  in Dec 2023, so there is no overlap with PACE.

How to build it: `poster/README.md`.
