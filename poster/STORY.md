# Poster story (agreed for #3, 2026-11-04)

## Main message (draft)

A model that uses only ocean color can predict chlorophyll profiles daily at
4 km. Hyperspectral PACE does no better than a few multispectral bands, and
coastal water, which existing 3D products leave out, [is / isn't] within reach.

## Blocks in reading order

| Block | Content | Figure | Source / new work |
| --- | --- | --- | --- |
| Key Points | 3 findings | — | — |
| Introduction | Why vertical structure matters; PACE; the question | — | — |
| Relation to existing approaches | SOCA2024 (Copernicus 3D product): what it needs (32 MLPs; 5-band Rrs + T/S, SLA, ADT, PAR), what it gives (weekly, 0.25°, open ocean > 1000 m, reprocessed, weekly fields end Dec 2023). CHLA-Z: Rrs only, so daily, 4 km, near-real-time, coastal. Mention Tanner et al. 2024 (surface → integrated). | Comparison table | QUID §II.2.1; no new analysis |
| Data | Argo + OOI profiles × PACE L3 4 km Rrs, 10 m bins to 200 m | Map by platform and water depth | chla-z `brt_training_data/`; bathymetry per profile (new) |
| Methods + fixing train/test leakage | One BRT per depth bin. Duplicate OOI rows plus a random row split leaked profiles and floats; fix: deduplicate, split by float/instrument | Skill before vs after the fix | New script (findings from Charlie, Kai, Nabir) |
| 1. Does hyperspectral help? | PACE 172 bands vs PACE cut to the OLCI bands vs real OLCI, on the same profiles, by depth and by region (coastal/open; ocean basin / latitude band) | R² or RMSE by depth; the same split by region | New script from Nabir's OLCI matchups |
| 2. Is there hope for coastal regions? | Skill in shelf/coastal water vs open ocean: profile shape (peak depth, structure) and total CHLA in the water column | Example coastal profiles; integrated CHLA observed vs predicted, coastal vs open | New script; OOI coastal arrays + bathymetry |
| Conclusions | — | — | — |
| Next steps | Physical inputs (Peter: little gain above 60 m, large below); prediction intervals (Nabir); L2 1 km matchups; compare with SOCA when it is reprocessed past 2024 | — | — |
| References, Acknowledgements | Hackweek team | — | — |

## Things to watch

- **Sample sizes by region.** The OLCI overlap is 2,369 profiles (474 in the
  hackweek test split). Splitting by region and depth leaves few per cell, so
  pick broad regions and show uncertainty (e.g. bootstrap or repeated grouped
  splits).
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
