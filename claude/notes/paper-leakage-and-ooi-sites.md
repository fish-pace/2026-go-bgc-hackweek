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
