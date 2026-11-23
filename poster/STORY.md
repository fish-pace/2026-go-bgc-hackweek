# Poster story (agreed for #3, 2026-11-04; revised 2026-11-23)

Eli may tweak this as each result comes in and the numbers are known.

## Main message (draft)

A model that uses only ocean color can predict chlorophyll profiles daily at
4 km. Hyperspectral PACE does no better than a few multispectral bands, and
coastal water, which existing 3D products leave out, [is / isn't] within reach.
Honest skill numbers need train/test splits that respect how in situ
instruments sample.

## Blocks in reading order

| Block | Content | Figure | Source / new work |
| --- | --- | --- | --- |
| Key Points | 3 findings | — | — |
| Introduction | Why vertical structure matters; PACE; the question | — | — |
| Data | Argo + OOI profiles × PACE L3 4 km Rrs, and × OLCI L3 4 km Rrs; 10 m bins to 200 m | Map by platform and water depth | fish-pace-datasets release `2026_11_23` (fish-pace/fish-pace-datasets#4; Mar 2024 – Oct 2026); bathymetry per profile (new) |
| Methods (terse) | One BRT per depth bin on Rrs. Solar hour is a model input, to account for the bias it causes in in situ fluorescence (daytime quenching). Matching to L3 daily maps (not 1:1 in time) | — | Methods draft in `claude/notes/rebuilt-data-2026-11.md` |
| Data leakage and split design (own block, a main result) | Instruments that sample one space-time region (Argo floats, moorings, gliders) give rows that are not independent: a float's consecutive profiles, a mooring's 3 h windows that share one satellite pixel. Random row splits leak and inflate skill. Compare row vs day vs instrument-grouped splits on the same model | Skill (R²/RMSE by depth) under each split design | New script (findings from Charlie, Kai, Nabir) |
| 1. Does hyperspectral help? OLCI vs PACE | (a) Band for band, same profiles: PACE 172 bands vs PACE cut to the OLCI bands vs real OLCI. (b) More data: OLCI matches more profiles than PACE (Argo 21.8% vs 16.0%), and only 40–60% of each sensor's valid profiles are valid in the other. Is OLCI trained on all its matches better because of more data? By depth and by region (coastal/open; ocean basin / latitude band) | R² or RMSE by depth for (a) and (b); the same by region | Release `_plus_OLCI` tables (`pace_Rrs_valid` flag) |
| 2. Is there hope for coastal regions? | Skill in shelf/coastal water vs open ocean: profile shape (peak depth, structure) and total CHLA in the water column | Example coastal profiles; integrated CHLA observed vs predicted, coastal vs open | New script; OOI coastal arrays + bathymetry |
| Relation to existing approaches (near the end, not the focus) | SOCA2024 (Copernicus 3D product): what it needs (32 MLPs; 5-band Rrs + T/S, SLA, ADT, PAR), what it gives (weekly, 0.25°, open ocean > 1000 m, reprocessed, weekly fields end Dec 2023). CHLA-Z: Rrs only, so daily, 4 km, near-real-time, coastal. Can a simpler approach do as well as SOCA? Acknowledge it as an important question; the questions here do not need the SOCA approach. Mention Tanner et al. 2024 (surface → integrated) | Comparison table | QUID §II.2.1; no new analysis |
| Conclusions | — | — | — |
| Next steps | Physical inputs (Peter: little gain above 60 m, large below); prediction intervals (Nabir); L2 1 km matchups; compare with SOCA when it is reprocessed past 2024 | — | — |
| References, Acknowledgements | Hackweek team | — | — |

## Things to watch

- **Sample sizes** (release `2026_11_23`, before the biofouling drop):
  - PACE Rrs: 9,542 Argo profiles and 22,240 OOI 3 h windows from 30
    instruments.
  - OLCI and PACE both valid (March 2024 – September 2026): 4,935 Argo and
    13,484 OOI windows.
  - The OOI windows are not independent: a median of 5 windows per
    instrument-day share one pixel. Count instruments, not rows.
  - Splitting by region and depth leaves few per cell, so pick broad regions
    and show uncertainty (e.g. bootstrap or repeated grouped splits).
  - Training counts after cleaning come from the re-run methods notebook.
- **"Coastal" needs a definition.** Water depth from bathymetry (e.g. < 200 m
  shelf, 200–1000 m slope, > 1000 m open ocean) is cleaner than platform. Few
  Argo floats are on the shelf, so the coastal sample is mostly OOI (Endurance,
  Pioneer). That means few independent instruments, and (Charlie) OOI and Argo
  fluorometers are calibrated differently. Say so on the poster.
- **Total CHLA on the shelf.** Shelf water can be shallower than 200 m, so
  integrate over the bins that exist and compare observed vs predicted over the
  same bins.
- **Hyperspectral might matter more on the coast**, in optically complex water.
  Experiment 1 split by region tests this directly. It's worth saying either way.

## Open

- Authors: Eli plus the hackweek team (slide 1 lists 8 people)?
