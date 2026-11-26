# For the paper: leakage, split design, and why OOI fails at new sites

Material Eli wants in the paper but **not on the poster** (decided 2026-11-24).
The poster shows only the space-time grouped split, as the way leakage was
handled; no random-split numbers and no out-of-region results.

All numbers: fish-pace-datasets release `2026_11_23`, BRT one model per 10 m
bin (run.py), R² of log10 Chl *a* on held-out data, mean of 5 repeats unless
noted. Runs on `~/shared-public/chla-z/split-design/runs/` (`full/`,
`ooi-windows/`, `window-weights/`); scripts in `poster/analysis/split_design/`.

## 1. Leakage: random rows vs grouped splits (runs/full)

| Data | Split | 0–10 m | 50–60 m | 100–110 m |
|---|---|---:|---:|---:|
| Argo | Random rows (80/20) | 0.76 | 0.58 | 0.39 |
| | Space-time (1° × 30 d) | 0.75 | 0.58 | 0.38 |
| | Instrument (float) | 0.75 | 0.57 | 0.37 |
| | New region (10° box) | 0.74 | 0.56 | 0.35 |
| OOI | Random rows | 0.89 | 0.79 | 0.82 |
| | Space-time | 0.54 | −0.01 | −0.09 |
| | Instrument | 0.44 | −0.10 | −0.22 |
| | Site | 0.43 | −0.08 | −0.20 |
| | New region | 0.10 | −0.24 | −0.74 |
| Argo + OOI | Random rows | 0.85 | 0.69 | 0.46 |
| | Space-time | 0.77 | 0.46 | 0.32 |
| | New region | 0.70 | 0.39 | 0.23 |

Integrated Chl *a* (profile_metrics.py, ≥ 5 contiguous bins): Argo 0.33 / 0.32 /
0.26 and OOI 0.80 / 0.18 / −0.36 for random / space-time / new region.

Reading: for Argo the split makes no difference (each float profile is ~10
days apart and moves). For OOI almost all of the random split's skill is
leakage: up to eight 3 h windows per instrument-day share one daily PACE pixel,
so near-copies land on both sides. Pooling Argo and OOI hides it in one number.

## 2. One window per day (runs/ooi-windows, run_windows.py, 3 repeats)

Keeping one fixed 3 h window per OOI instrument-day (night 00–03 or midday
12–15 solar) gives the same space-time skill as all windows with 1/8 the rows:
surface R² 0.55 (night), 0.55 (midday), 0.54 (all). The random-split R² falls
from 0.89 to 0.58–0.65. Caveat: each variant was scored on its own rows. The
fair comparison (same held-out rows; all / weighted 1/n per day / one random
window per day) is `run_window_weights.py` → `runs/window-weights`.

Result (2026-11-24, QC'd data, 5 repeats, space-time split, R² of log10):
the weighting barely matters. Argo scored inside the Argo + OOI model gains
+0.003 to +0.007 with weighted or one-window training (less OOI dominance);
OOI loses about 0.03 at the surface (0.63 all, 0.60 weighted/one window) and
about 0.01-0.02 at 20-30 m; pooled R² changes by < 0.01. So the extra windows
are not only leakage: under a grouped split they add a little OOI skill and
cost Argo almost nothing. Decision: keep all windows, unweighted.

## 3. Why OOI fails at a new site: per-instrument offsets (surface)

OOI surface Chl *a* tracks PACE `pace_chlor_a` (same pixel and day) about as
well as Argo does, but each site sits at its own offset (median
log10 in situ − log10 PACE chlor_a, 0–10 m bin):

| | n | r | offset |
|---|---:|---:|---:|
| Argo open ocean | 8,983 | 0.80 | −0.18 |
| Argo slope | 180 | 0.85 | −0.34 |
| Argo shelf | 168 | 0.61 | −0.66 |
| OOI Cabled | 1,262 | 0.74 | +0.03 |
| OOI Endurance | 2,064 | 0.71 | +0.10 |
| OOI Pioneer | 6,525 | 0.57 | −0.19 |
| OOI Irminger | 548 | 0.63 | −0.32 |

Per instrument the offset runs from −0.49 (CE01 shelf) to +0.13 (CE04), a
factor of about 4. Papa has no 0–10 m data.

The held-out-region bias matches the sign of each site's offset (Irminger reads
low vs PACE and is over-predicted by +0.36 when held out; Endurance reads high
and is under-predicted by −0.43; Pioneer −0.19 → +0.18).

Diagnostic: subtracting one constant per instrument from the predictions
(computed from the test data itself, so an oracle, not a usable correction):

| OOI | as is | one offset per instrument removed |
|---|---:|---:|
| 0–10 m, space-time | 0.54 | 0.59 |
| 0–10 m, new region | 0.10 | 0.46 |
| 50–60 m, space-time | −0.01 | 0.02 |
| 50–60 m, new region | −0.24 | −0.15 |

So at the surface the new-site failure is mostly a site-level offset between
in situ fluorescence Chl *a* and satellite Rrs. Irminger is open ocean and has
the largest offset, so this is not a coastal effect. Candidate causes, not yet
separated: OOI factory calibration × the regional fluorescence:Chl ratio
(`chla_ratio`, median 1.26) vs Argo's adjusted CHLA; or real local bio-optics.
Practical meaning: a new site needs either consistent calibration or a short
local record to learn its offset.

Per-location surface R² (OOI-only model): space-time / site / new region —
Cabled 0.58 / 0.50 / −0.01; Endurance 0.50 / 0.27 / −0.33; Pioneer
0.31 / 0.22 / −0.21; Irminger 0.19 / −0.27 / −0.27.

## 4. Depth: a coastal effect seen on both platforms

Removing site offsets does not fix 50–60 m, so the loss of skill at depth is a
separate problem. Argo, which has independent instruments and calibration,
shows it too near coasts (Argo-only model, space-time / new region):

| Argo | 0–10 m | 50–60 m |
|---|---:|---:|
| Open ocean (8,998 surface rows) | 0.75 / 0.74 | 0.59 / 0.58 |
| Slope (181) | 0.74 / 0.70 | 0.16 / 0.06 |
| Shelf (171, mostly Baltic) | 0.15 / −0.68 | −0.77 / −3.92 |

Small samples on slope and shelf. Depth class: ETOPO 2022 at the profile
position (`~/shared-public/chla-z/bathymetry/water_depth_2026_11_23.parquet`).

Open (2026-11-24): whether low R² at depth near coasts is low skill or low
variance (R² is small when Chl *a* barely varies). Check RMSE/MAE and the SD
of observed log10 Chl *a* by depth and class, Argo and OOI separately.

## 5. Thin depth bins dropped from the skill-by-depth figure (bloom caveat)

Decided 2026-11-24. `explore_skill_baseline.py` (and the poster Figure 3 built
from it) draws a depth bin only if it has at least 100 rows and at least 10% of
the largest bin's row count in the same line (platform × water-depth class).
On the shelf this drops 10–20 m (332 rows) and 80–110 m (≤ 330), where the
site mix jumps: most shelf bins have ~4,000 rows, mostly Pioneer, but 10–20 m
has no Pioneer data, only the four Endurance shelf profilers off Oregon (161
rows, mostly summer upwelling, up to 32 mg m⁻³) plus Argo shelf floats.

**Caveat (Eli): this may in effect remove outliers.** The dropped 10–20 m shelf
bin holds real summer blooms, and not being able to predict blooms would be a
serious limitation. Model errors there were large (shelf MAE about 1.2 mg m⁻³
at 15 m vs 0.26 at 5 m). Bloom prediction gets its own dedicated test later;
the paper should report it, not hide it behind the bin rule.

Rules tried and rejected: "no single site > 75% of rows" (Pioneer dominates
nearly every shelf bin, so it removed the shelf and kept the 10–20 m spike);
"10% of the median bin" (the many near-empty deep shelf bins pull the median
down to ~330, so the thin bins passed).

## 6. Error reduction from Rrs vs an average profile (paper figure)

Eli, 2026-11-24: for the poster this is summarized in text; the figure goes in
the paper. `figs/error_reduction_vs_average_profile.png` (from
`explore_skill_baseline.py --design all` on `runs/window-weights`: QC'd data,
all OOI windows, Argo + OOI model, space-time split, 5 repeats, thin-bin rule
of section 5). Left: MAE (mg m⁻³) with Rrs vs mean observed Chl *a*. Right:
error reduction = 100 × (1 − MAE with Rrs / MAE of the average profile), where
the average profile is the geometric-mean Chl *a* per depth bin of each fold's
training rows: what is known from past in situ data with no satellite.

Why this metric (Eli): R² compares with local variability, so near-coast
depths look like total failure even where Chl *a* is tiny and the model is
close; 0.002 vs 0.004 mg m⁻³ is a meaningless miss, 0.02 vs 0.2 is not. And a
large % reduction alone could be "improved on horrible, still horrible", hence
the MAE-vs-mean panel.

Error reduction (%), pooled Argo + OOI:

| Depth (m) | Open ocean | Slope | Shelf |
|---:|---:|---:|---:|
| 5 | 47 | 44 | 32 |
| 25 | 49 | 42 | 21 |
| 55 | 31 | 7 | 4 |
| 105 | 24 | 11 | – |
| 155 | 25 | 0 | – |

Pooled vs separate platforms: the pooled line follows Argo in the open ocean
and OOI on the slope and shelf (row counts). At 75–175 m Argo does better than
OOI (open ocean 20–30% vs 0–10%; slope 20–30% vs ~5%); see
`runs/window-weights/figs/skill_baseline_all.png`.

## 7. Is the model just predicting each site's average? (OOI, 2026-11-24)

Model vs two baselines built from the training folds only: each site's
all-year average and each site's calendar-month average (OOI site = array
code; runs/window-weights, Argo + OOI model, all windows). R² of log10:

| OOI | Model | Site average | Site × month |
|---|---:|---:|---:|
| Shelf 0–10 m | 0.54 | 0.09 | 0.38 |
| Shelf 20–30 m | 0.02 | 0.00 | 0.03 |
| Shelf 50–60 m | −0.09 | −0.01 | −0.14 |
| Slope 0–10 m | 0.50 | −0.02 | 0.07 |
| Open ocean 20–30 m | 0.44 | −0.03 | −0.07 |

At the surface Rrs beats even the seasonal climatology (real day-to-day
information). Below ~20 m near the coast the model is no better than the site
average, and the seasonal cycle does not help either. The apparent shelf skill
against a global average profile (section 6) is the model learning the site's
level. Linear-scale view (explore_coastal_depth.py --scale linear): at depth
both errors and Chl *a* are small, so "R² ≈ 0" costs little in mg m⁻³.

## 8. Platform as an input (run_platform.py, runs/platform, 5 repeats)

| R² (log10) | 0–10 m | 20–30 m | 50–60 m | 100–110 m |
|---|---:|---:|---:|---:|
| Argo, with platform input | 0.75 | 0.77 | 0.58 | 0.38 |
| Argo, no platform input | 0.75 | 0.77 | 0.57 | 0.36 |
| Argo, as Argo + OOI offset | 0.75 | 0.77 | 0.58 | 0.38 |
| OOI, with platform input | 0.63 | 0.23 | 0.03 | −0.08 |
| OOI, no platform input | 0.62 | 0.20 | −0.03 | −0.26 |
| OOI, as Argo + OOI offset | 0.61 | 0.17 | −0.08 | −0.46 |

Decision (Eli): the poster uses "as Argo + per-depth OOI offset" (design
`argo_bias`), how a map would be made. For Argo it is identical to the model
with the platform input. For OOI a single offset per depth cannot replace the
flag below the surface because offsets differ by site (section 3).

## 9. SOCA2024 metrics by water depth (poster Table 2)

SOCA2024 validates with all depths pooled: r² and slope of a regression of
predicted on observed log10 Chl *a*, MAPD, RMSD (QUID 015-010 section IV.2;
random 20% of BGC-Argo profiles, 11,340; open ocean only). Ours, `argo_bias`,
space-time split, 5 repeats (scripts/fig_profiles_by_class.py):

| | r² | Slope | MAPD | RMSD | rows (floats/sites) |
|---|---:|---:|---:|---:|---|
| SOCA2024 | 0.83 | 0.82 | 30% | 0.19 | |
| Open ocean | 0.69 | 0.69 | 43% | 0.22 | 13,544 (819) |
| Slope | 0.69 | 0.71 | 45% | 0.60 | 5,331 (43) |
| Shelf | 0.28 | 0.40 | 46% | 0.77 | 11,621 (11) |

Integrated Chl *a* R² (profiles with ≥ 10 observed bins): open 0.40, slope
0.67, shelf −1.20 (92 Argo profiles, 7 floats, mostly Baltic; no OOI shelf
profiler reaches 10 bins). Pooled-depth r² rewards getting the general profile
shape; our per-depth R² is a harder test. The gap to SOCA is mostly inputs and
data (physics, 8-day Rrs median, ~6x more profiles), not the split: for Argo
random and space-time splits give the same skill (section 1).

Peak depth (talk figure, tried for the poster and dropped): open ocean errors
centre on 0 for peaks above 100 m and run ~30 m shallow for deeper peaks; on
the slope and shelf nearly all peaks are at the surface, so the boxes collapse.

## 10. Data notes found while making the poster

- 24 Argo profiles sit at the sensor floor (0.000–0.02 mg m⁻³ at every depth;
  10 from float 2902882). Bad data, but removing them moves open-ocean
  integrated R² only 0.41 → 0.42. Not excluded; a blanket "max < 0.05" rule
  would also drop deep single-depth OOI sensors that are legitimately low.
- The open-ocean integrated scatter shows a second Argo cloud under-predicted
  at high integrals. Not investigated.
- Hyperspectral (block 1) on the QC'd data: unchanged at 2 decimals; PACE-172
  beats OLCI-11 by 0.004–0.035 in every repeat.
- Physics pilot (OOI only, pre-QC, 2 repeats) is not trustworthy on its own.
  The Argo GLORYS12 fetch (physics_pilot/extract_glorys_argo.py →
  ~/shared-public/chla-z/glorys12/argo_profiles) was started 2026-11-24 for a
  rerun on Argo, OOI and both with the QC exclusion and `argo_bias`.

## 11. Gliders as a third platform (poster v2, #22 / PR #25, 2026-11-24)

Release `2026_11_24` (fish-pace-datasets#14; Argo and OOI tables identical to
`2026_11_23`): 2,289 glider training rows, 20 deployments (Rutgers 10 Slocum,
Scripps 5 and WHOI 5 Spray). Run: `runs/platform-glider` (`argo_bias`, one
offset per non-Argo platform). Glider QC scan: 0 of 60 deployment-months
flagged. Glider Chl *a* is Sauzède only, dark offset not subtracted
(fish-pace-datasets `claude/notes/chla-z-glider.md`, "Dark offset").

- **Table 2 barely moves** (v1 → v2 r²: open 0.69 → 0.68, slope 0.69 → 0.67,
  shelf 0.28 → 0.30); the gain is coverage: units shelf 11 → 25, slope 43 → 54.
- **Shelf integrated R² −1.20 → 0.28 is pooling**, not skill: within platform
  Argo −1.30 (92), glider 0.02 (65); the two clusters sit at different levels.
  Slope integrated R² by platform: OOI 0.68, Argo 0.41, glider 0.26. Idea for
  a fairer shelf measure: #24.
- **Offsets are stable** (glider 0–10 m −0.057 ± 0.008 log10 over folds and
  repeats; OOI +0.004). Per-instrument median residual after the offset
  (0–30 m) has SD 0.20 for Argo floats, 0.16 for glider deployments, 0.16 for
  OOI instruments: gliders are not worse calibrated than floats as a group.
  Month-to-month glider changes are mostly which deployments are active.
- **Calibration vs region, a hint:** California Current deployments differ
  from −0.21 to +0.13 within one region, while the three ru34 deployments
  (southern New England) agree (−0.10 to +0.02). With more deployments,
  repeat the new-region test (section 3) with gliders, or hold out one
  deployment at a time.
- **Shelf surface compression** (0–10 m, median predicted/observed): OOI 1.27
  below 0.5 mg m⁻³, 0.44 at 2–5, 0.27 at 5–10, 0.11 above 10; the 62 OOI
  windows above 5 are ~1% of shelf surface rows. Blooms: Next Steps.
- **Example profiles** (new Figure 1): random within the 25th–75th percentile
  of per-profile RMSE in each class; slope and shelf median RMSE (log10) 0.26
  and 0.27. A random shelf draw without that rule landed on bloom profiles
  (76th–95th percentile), which look much worse than typical.

## 12. Glider release 2026_11_26: 280 deployments (#27, 2026-11-26)

Full numbers and figures: #27; code `compare_glider_release.py`, run
`runs/platform-glider-2026_11_26` (set `CHLAZ_DATA_RELEASE=2026_11_26`; the
default stays `2026_11_24`, the printed poster). 21,609 glider windows, 258
deployments, after dropping `deep_offset_flag` rows (12,555) and 7 flagged
deployment-months (not yet reviewed by eye).

- **Pooled class metrics move because gliders are now 42–61% of rows**, not
  because the model changed: r² on Argo + OOI rows alone is unchanged
  (0.69 / 0.70 / 0.30). Gliders score r² ≈ 0.52 pointwise in every class.
  Pooled r² open 0.64, slope 0.61, shelf 0.46; integrated R² 0.32 / 0.54 / 0.29.
- **Shelf is now skill-limited, not data-limited**: 188 glider deployments,
  1,293 whole profiles, glider integrated R² 0.02 → 0.26; predictions still
  compressed (~30–60 mg m⁻² vs 10–500 observed).
- **Glider surface offset** −0.056 → −0.006 log10: with many deployments,
  glider and Argo calibration agree at the surface.
- **Open-question cluster**: open-ocean glider profiles observed at 3–10
  mg m⁻² integrated, predicted ~40 (glider open-ocean integrated R² 0.33 →
  0.14). Check against the release's `scan_check` notes before the paper.

### 12a. Glider dark offset and deep bins (2026-11-26; #27 comments 1–5)

- **The open-ocean drop is the glider bins at 100–200 m** (r² 0.02–0.06;
  Argo 0.33–0.46 there). Gliders read ~4× Argo at 150–200 m. Re-scoring
  with glider bins above 100 m only recovers Argo-level skill. The release's
  `scan_check` notes do not explain it.
- **Argo's method** (QC manual v3.1, July 2026, doi:10.13155/35385):
  - `CHLA_ADJUSTED = (FLUO − DARK') × SCALE`, then NPQ (Xing 2012), then
    ÷ PHYSIO_RATIO (the Sauzède 2025 LUT, replacing factor 2).
  - DARK' = median of the profile minima (running median, > 5 dbar) of the
    first 5 profiles deeper than 950 dbar. It is subtracted at all depths.
  - The release uses Argo QC {1, 2, 5, 8}. Gliders and OOI get Sauzède only.
  - The Argo method on gliders gives the same answer as the release's
    below-300 m dark (night PACE/glider 1.72 vs 1.72).
- **Additive, not a gain bias** (California Current, night):
  - Dark-subtracted PACE/glider grows from 1.6 to 24 as PACE chlor_a falls
    from 0.4–0.8 to < 0.1. Uncorrected it is flat at ~1.
  - Argo in the same box: 0.90 (n 149).
  - In clear water the surface reads about the same as below 300 m
    (0.164 vs 0.159), while there is a clear DCM at ~80 m.
- **Not temperature:** within-profile deep fluorescence rises only ~+0.006
  from 300 to ~950 m in the California Current, ~1/6 of what a
  temperature-dependent dark would need (`glider_dark_depth.py`, 73
  deployments). Temperature was not added to the release.
- **Mostly Spray gliders:**
  - Of 142 deployments with a value (138 never reach 300 m; offset unknown),
    53 have a median > 0.1.
  - Spray: 47 of 65 above 0.1 (median 0.159). Slocum: 5 of 66 (0.033).
    Seaglider: 1 of 10.
  - Slocums in the same Pacific water read ~0.05, so this looks like the
    sensor or setup, not deep organic matter (an idea from comment 4,
    withdrawn in comment 5).
  - Fluorometer model not checked. Region and platform are confounded.
- **Deployment rules don't fix it:** refits dropping offset > 0.1 or all
  Sprays gain only 0.01–0.03 pooled. Glider 100–200 m bins stay at r² ~0.05
  either way, because even small offsets (0.03–0.05) exceed real Chl *a* at
  depth (~0.02). The lever is a **depth rule** for glider bins.
- **OOI deep bins are also unpredictable** (r² ~0.00 at 100–200 m; OOI is
  not dark-corrected). Not yet looked at.

### 12b. Glider bins < 100 m: value of glider data, shelf skill (#27 comment 6)

Run `runs/glider-value-2026_11_26` (`run_glider_value.py`, 3 repeats): glider
bins ≥ 100 m removed on all classes, plus an Argo + OOI-only model on the same
folds and held-out rows. Analysis: `analyze_glider_value.py`.

- **Pooled r²:** open 0.69, slope 0.70, shelf 0.43 (Argo + OOI rows only:
  0.69 / 0.70 / 0.29). Deep glider bins did no harm in training: dropping
  them only from scoring gives the same numbers.
- **Glider data helps where the gliders are** (held-out glider rows, bins
  < 100 m, with vs without gliders):
  - shelf RMSE 0.363 → 0.327, r² 0.43 → 0.51;
  - slope RMSE 0.353 → 0.321, r² 0.49 → 0.54;
  - open ocean, small gain.
  - Not just the platform offset (bias-removed RMSE without gliders: shelf
    0.361, slope 0.345).
  - Little effect on OOI shelf rows (0.24 → 0.26); none on Argo.
  - Caveat: the 1° × 30 d split keeps the same region at other times in
    training. This is "regional coverage" value, not transfer to unsampled
    shelves.
- **The shelf is not harder at equal surface Chl *a*:** per-profile RMSE
  (log10, bins < 100 m) by PACE chlor_a is 0.30–0.34 on the shelf, slope and
  open ocean below 2 mg m⁻³. The model beats a mixed column at the true
  surface value in every class.
  - Above 2 mg m⁻³ error rises everywhere (shelf and slope 0.43, open
    0.36); the shelf has more such water (738 profiles vs 106).
  - Clear shelf water is barely sampled (6 profiles < 0.1, 256 at 0.1–0.2).
- **The low pooled shelf r² is mostly the OOI shelf rows** (31k rows,
  r² 0.26; 50–100 m r² 0.02; inshore fixed instruments and profilers,
  suspect Pioneer data). Next candidate to look at.
