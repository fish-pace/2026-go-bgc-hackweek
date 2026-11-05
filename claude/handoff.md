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
- #4 Blocks: split into #7–#16. **#7 (data fixes) comes first.**
- #7 status (2026-11-05): the hackweek fixes were coded but **never applied to
  the data**. The poster still trains on the January tables. Eli decided the
  rebuild happens in fish-pace/fish-pace-datasets as a new release; the full
  work list is **fish-pace/fish-pace-datasets#4**. Where the fix branch
  stands, what's already rebuilt on the hub, and the decisions still open are
  all in that issue. Nothing in this repo or in fish-pace/chla-z changes for
  the rebuild. Jodi's data work is still unlocated.
- PR #18 (open, not merged): the methods notebook and Nabir's four notebooks
  read the training tables from a fish-pace-datasets **release tag**
  (`DATA_RELEASE = "2025_11_01"`), not from `main` or a local path. When the
  new release exists, change that tag in each notebook and re-run. The poster
  is meant to use the **corrected** data. The tag records which data version
  each result used; it isn't there to keep the poster on the old data.
- #6 holds Eli's SOCA/Sauzède references for block #12.

Facts that affect the rebuild (checked 2026-11-05):
- **PACE collections.** `PACE_OCI_L3M_RRS` and `PACE_OCI_L3M_CHL` (and their
  NRT versions) are gone from CMR. Use `PACE_OCI_L3M_AOP`, `_BGC` and `_KD`
  V3.2.
- **Existing release.** fish-pace-datasets release `2025_11_01` is the
  pre-hackweek data, byte-identical to `chla-z/brt_training_data/`.

The story PR (#17, which also brought in Nabir's `nama` branch: OLCI matchups,
PACE-vs-OLCI comparison, prediction intervals) was merged to `main` on 2026-11-05.

Notes:
- [notes/poster.md](notes/poster.md): how the poster is built and why.
- [notes/hackweek-experiments.md](notes/hackweek-experiments.md): what each
  hackweek participant tested and found, where the code is, and the SOCA2024
  facts. SOCA2024 uses 5-band Rrs, not surface Chl, and its weekly fields end
  in Dec 2023, so there is no overlap with PACE.

How to build it: `poster/README.md`.
