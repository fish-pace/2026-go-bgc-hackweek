# Handoff

Rolling session state for agents working in this repo. Read this first.

## Repo

Materials from the 2026 GO-BGC Hackweek CHLA-Z project (Aug 18–21, 2026), run
by Eli Holmes, and now the AGU26 poster built from that work. The model code
and the CHLA-Z product live in fish-pace/chla-z-modeling and fish-pace/chla-z
(https://fish-pace.github.io/chla-z/). Training data: fish-pace-datasets
release `2026_11_23`.

## State (2026-11-24)

**AGU26 poster: version 1 is done** (Eli: "good enough") on branch
`leakage-split-design` (47 commits ahead of `main`, pushed, **no PR yet**).
Build: `make` in `poster/` (or `quarto render poster.qmd`); one 42 × 42 in
page, printing at posternerd.com (PDF accepted). Eli is doing a close read.

Poster structure, settled with Eli on 2026-11-24 (details and why:
[notes/poster.md](notes/poster.md), the block files' header comments):
Introduction (with the SOCA2024 comparison and its reference) and the data map
| Data, Methods (leakage handled by 1° × 30-day space-time blocks; no random or
out-of-region results on the poster), block 1 hyperspectral | block 2 coastal
(SOCA2024 metrics by open ocean / slope / shelf + integrated Chl *a* figure),
Key Findings, Next Steps | Acknowledgements full width at the foot.

Model choices behind the poster numbers: OOI QC exclusion
(`poster/analysis/split_design/ooi_qc_exclude.csv`, reported as
fish-pace/fish-pace-datasets#13); all OOI 3 h windows, unweighted; predicted
as Argo with a per-depth OOI offset (`run_platform.py`, design `argo_bias`).

## Open threads

- **Physics rerun** (Eli, "in the morning"): Argo GLORYS12 fetch running on
  the hub (`physics_pilot/extract_glorys_argo.py`, log
  `~/shared-public/chla-z/glorys12/argo_fetch.log`; rerun to resume, then
  `--retry-failed`). Then rerun the physics pilot on Argo, OOI and both with
  the QC exclusion and `argo_bias`. Not for the poster; Next Steps only.
- **Bloom prediction test** (Eli): dedicated test later; thin shelf bins
  holding blooms are dropped from depth figures (paper note §5).
- **OOI QC in the release**: fish-pace-datasets#13 (Eli fixes it there).
- **PR** for `leakage-split-design` when Eli says the poster is done.

## Notes

- [notes/paper-leakage-and-ooi-sites.md](notes/paper-leakage-and-ooi-sites.md):
  results for the paper that are not on the poster: leakage tables, window
  test, OOI site offsets, site-average baselines, platform test, SOCA-metric
  comparison, data issues.
- [notes/rebuilt-data-2026-11.md](notes/rebuilt-data-2026-11.md): the rebuilt
  training data, OLCI matchups, the suspect Pioneer data.
- [notes/hackweek-experiments.md](notes/hackweek-experiments.md): what each
  hackweek participant tested; SOCA2024 facts (5-band Rrs, weekly fields end
  Dec 2023).
- [notes/poster.md](notes/poster.md): how the poster is built.

Facts: `PACE_OCI_L3M_RRS`/`_CHL` are gone from CMR; use `PACE_OCI_L3M_AOP`,
`_BGC`, `_KD` V3.2. A parallel session works in fish-pace-datasets; don't edit
that repo from here.
