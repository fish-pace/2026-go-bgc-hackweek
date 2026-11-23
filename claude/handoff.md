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
- #7 status (2026-11-23): **data released** as fish-pace-datasets
  [`2026_11_23`](https://github.com/fish-pace/fish-pace-datasets/releases/tag/2026_11_23)
  (PR fish-pace/fish-pace-datasets#9, merged). OOI rows are 3 h solar-time
  windows; `_plus_OLCI` tables added. Jodi's data work is still unlocated.
- Branch `rebuilt-training-data` here (PR #19): the methods notebook and Nabir's
  three analysis notebooks read `DATA_RELEASE = "2026_11_23"` and ran clean on
  it. `chla_z_uq` and `olci_l3_brt_compare` take OLCI from the release
  `_plus_OLCI` tables; `olci_l3_matchups.ipynb` is superseded (not re-run).
  Results and the Methods draft (counts still to fill in):
  [notes/rebuilt-data-2026-11.md](notes/rebuilt-data-2026-11.md). The tag
  records which data version each result used; the poster uses the corrected
  data.
- Story revised 2026-11-23 (`poster/STORY.md`): terse Methods (#8); data
  leakage and split design is its own block and a main result (#20); block 1
  adds OLCI "more data" vs band-for-band; SOCA near the end, not the focus.
  #2 and #3 closed.
- #6 holds Eli's SOCA/Sauzède references for block #12.
- **Next (Eli, 2026-11-23): start the leakage block, #20.** Compare row vs
  day vs instrument-grouped splits on the same model and release
  `2026_11_23`, with skill by depth bin over repeated seeds. Starting points:
  - the shared evaluation code planned in #8 (`poster/scripts/`);
  - `chla_z_uq.ipynb` for the grouped split.

  Known so far: row-split R² 0.849 vs grouped surface R² 0.62. OOI rows
  dominate the grouped test set (6 instruments, 5,329 rows vs 1,765 Argo),
  so decide on per-platform metrics or instrument weighting.

  A parallel session in fish-pace-datasets (branch `pipeline-notebooks`) is
  turning that repo's notebooks into data retrieval, QC and matchup method
  examples. Don't edit that repo from here.

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
