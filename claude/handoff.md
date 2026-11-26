# Handoff

Rolling session state for agents working in this repo. Read this first.

## Repo

Materials from the 2026 GO-BGC Hackweek CHLA-Z project (Aug 18–21, 2026), run
by Eli Holmes, and now the AGU26 poster built from that work. The model code
and the CHLA-Z product live in fish-pace/chla-z-modeling and fish-pace/chla-z
(https://fish-pace.github.io/chla-z/). Training data: fish-pace-datasets
release `2026_11_24` (Argo, OOI, IOOS gliders; its Argo and OOI tables are
identical to `2026_11_23`).

## State (2026-11-24)

**AGU26 poster v2 is merged** (PR #25, closes the work of #22): Argo + OOI +
IOOS gliders, Figure 1 = typical profiles by water depth. Build: `make` in
`poster/` (figure scripts, then Quarto); one 42 × 42 in page, printing at
posternerd.com. `poster/requirements.txt` was checked in a clean venv.

- **The poster has no spare line in any column.** Blocks move whole, so one
  extra line pushes the rest onto page 2. Check `pdfinfo poster.pdf` after
  every text edit; cuts of Eli's text are her call.
- Layout and why: [notes/poster.md](notes/poster.md) and each block's header
  comment (numbers, runs, v1 values).
- Model behind the numbers: space-time split (1° × 30 d), QC exclusions
  (`poster/analysis/split_design/{ooi,glider}_qc_exclude.csv`), all OOI
  windows, predicted as Argo plus a per-depth offset per platform
  (`run_platform.py`, design `argo_bias`, `runs/platform-glider`).
  `run.load()` defaults to Argo + OOI so block 1 and older analyses are
  unchanged; v2 scripts ask for gliders.

## Open threads

- **Glider release `2026_11_26`** (280 deployments, #27, branch
  `glider-release-2026-11-26`, not yet a PR): poster story holds, no
  reprint. Then (2026-11-26) a session on glider QC with Eli; she will resume
  that conversation. Findings in [notes/paper-leakage-and-ooi-sites.md](notes/paper-leakage-and-ooi-sites.md)
  §12a–b and #27 comments 1–6:
  - deep glider bins (≥ 100 m) are unpredictable (the deep offset, mostly
    Sprays, is not temperature-driven);
  - with them cut, glider data helps on the shelf and slope;
  - the shelf is not harder at equal surface Chl *a*;
  - the low shelf r² is mostly OOI shelf rows.
  - Undecided: the glider depth rule and the dark offset; OOI shelf and deep
    bins not yet examined.
  - Runs are in `~/shared-public/chla-z/split-design/runs/*2026_11_26*` and
    `glider-value-2026_11_26`.

- **Physics inputs** (#23, Eli later, not for the poster): Argo GLORYS12
  fetch (`physics_pilot/extract_glorys_argo.py`; rerun to resume, then
  `--retry-failed`), then the pilot rerun with the QC'd data.
- **Shelf skill to the bottom** (#24, paper): integrate Chl *a* to the
  seafloor, not to 200 m.
- **Glider dark offset**: not subtracted, an open question (paper; memory
  `glider-chla-sauzede-only`).
- **Bloom prediction test** (Eli): later; paper note §5, §11.
- **OOI QC in the release**: fish-pace/fish-pace-datasets#13.

## Notes

- [notes/paper-leakage-and-ooi-sites.md](notes/paper-leakage-and-ooi-sites.md):
  results for the paper, not on the poster (leakage, OOI site offsets,
  platform test, SOCA metrics; §11 gliders).
- [notes/rebuilt-data-2026-11.md](notes/rebuilt-data-2026-11.md): rebuilt
  training data, OLCI matchups, suspect Pioneer data.
- [notes/hackweek-experiments.md](notes/hackweek-experiments.md): what each
  participant tested; SOCA2024 facts.
- [notes/poster.md](notes/poster.md): how the poster is built.

Facts: `PACE_OCI_L3M_RRS`/`_CHL` are gone from CMR; use `PACE_OCI_L3M_AOP`,
`_BGC`, `_KD` V3.2. A parallel session works in fish-pace-datasets; don't
edit that repo from here. The pre-release glider run is kept as
`runs/platform-glider-prerelease` (agrees with the release run to 0.01).
