# Rebuilt training data (November 2026)

The notebooks on branch `rebuilt-training-data` read the tables rebuilt in
fish-pace/fish-pace-datasets#4 (branch `chla-z-rebuild`), via
`DATA_RELEASE = "2026_11_23"` (the release, cut 2026-11-23). Earlier runs read
the PR branch `chla-z-rebuild` (now deleted). Build details, decisions and the
before/after tables live in fish-pace-datasets
`claude/notes/chla-z-rebuild-2026-11.md`.

## Draft Methods wording (for the poster, issue #8)

This replaces the earlier #8 comment, which described pooling descending and
ascending levels. That is no longer done. It has not been posted to #8.

> **Data.** BGC-Argo profiles (March 2024 – October 2026) were taken from the
> Ifremer ERDDAP server with argopy 1.5.0 in expert mode (snapshot
> 2026-11-06). Only ascending profiles were used. Adjusted chlorophyll
> (`CHLA_ADJUSTED`) levels with QC flags 1, 2, 5 or 8 were averaged in 10 m
> pressure bins (A < p <= B) from 0 to 200 m. OOI fluorometer data (30
> profilers and fixed instruments) were taken from the OOI ERDDAP server and
> kept where the aggregate QC flag was 1. Fixed-depth instruments were assigned
> their known depth. OOI instruments sample continuously, so their data were
> averaged in 3 h windows of local mean solar time (00–03, 03–06, … h, where
> solar time = UTC + longitude/15 h for each sample). Within each window and
> instrument, CHLA is the arithmetic mean of all QC-passing samples in each
> 10 m depth bin (same bins as Argo); a profiler window can include several
> casts, and a fixed instrument fills only the bin of its depth. The window's
> time is the mean time of its samples. OOI fluorescence was converted to
> chlorophyll with the regional fluorescence:chlorophyll ratios of Sauzède et
> al., putting it on the same basis as Argo `CHLA_ADJUSTED`.
>
> The satellite data are Level-3 daily 4 km maps, which composite the day's
> Level-2 swaths and carry no per-pixel observation time. Matching is therefore
> not one-to-one in time: each in situ profile or OOI window is paired with the
> daily map that covers its time, at the nearest grid cell. For PACE that is
> OCI V3.2 remote-sensing reflectance (172 bands), chlorophyll-a and Kd(490),
> from the file whose 24 h coverage starts at most 24 h before the profile
> time, using standard files before near-real-time (NRT) ones. Standard V3.2
> files end on 2026-09-30, so October 2026 matches use NRT files. For
> Sentinel-3 OLCI (11 bands, S3A then S3B) it is the map of the profile's UTC
> day. The model estimates CHLA(z) from these daily averaged reflectances.
> Because in situ fluorescence varies with the time of day (daytime quenching
> lowers fluorescence per unit chlorophyll near the surface), the solar hour of
> each in situ sample is a model input, so the model can correct for it. The
> OOI 3 h windows give that correction samples across the whole day.
>
> Profiles with no valid Rrs (cloud, glint) were dropped, as were
> profiles with uniformly high chlorophyll from 100 to 200 m (likely
> biofouling). The training set has N profiles: N Argo from N floats and N
> OOI windows from 30 instruments.

**The counts above are not filled in yet** (next task: the Methods update).
From the methods notebook on `2026_11_23`: 31,782 rows with PACE Rrs (9,542
Argo profiles from 831 floats, 22,240 OOI 3 h windows from 30 instruments);
159 flagged as biofouled; 31,623 training rows.

## How the results changed (methods notebook, same code, new data)

| | `2025_11_01` | rebuild, OOI days | `2026_11_23`, OOI 3 h windows |
|---|---:|---:|---:|
| training rows (after biofouling drop) | 5,510 | 12,705 | 31,623 |
| biofouling-flagged profiles | 20 | 24 | 159 |
| train / test rows | 4,408 / 1,102 | 10,164 / 2,541 | 25,298 / 6,325 |
| test R² (all bins, log10) | 0.821 | 0.778 | 0.849 |
| test RMSE (log10) | 0.303 | 0.318 | 0.256 |
| test bias (log10) | −0.016 | 0.000 | −0.005 |
| cell 49 profile-shape metrics: N | 485 | 1,983 | 2,772 |
| cell 49 r2_log / rmse_log | 0.367 / 0.326 | 0.356 / 0.361 | 0.487 / 0.291 |

**The jump to R² 0.849 with the 3 h windows is the leak, not better skill.**
Under the random row split, windows of one instrument-day that share a pixel
land on both sides. With the split grouped by instrument (`chla_z_uq`), surface
R² on the same release is 0.624. That gap is the #20 leakage result.

The methods notebook still uses a random row split (the leakage the poster's
methods block fixes). These numbers compare data versions with the split held
fixed. They are not the poster's skill numbers.

`chla_z_uq.ipynb` (grouped split by float/instrument, surface bin): coverage of
the 80% intervals moves toward nominal with the larger table. CQR 0.68 → 0.78,
CQR Mondrian 0.68 → 0.81, mean BRT + conformal 0.72 → 0.79. Per-bin CQR
coverage is 0.81–0.86 below the surface (was 0.76–0.94).

On `2026_11_23` (3 h windows): surface CQR 0.78, Mondrian 0.82, mean BRT +
conformal 0.82; surface R² 0.62. The OOI group regex was fixed for the window
ids (`_YYYYMMDDTHH`); before the fix every window would have been its own
group. **The test split has 6 OOI instruments but 5,329 OOI rows vs 1,765
Argo rows** (surface bin), so OOI windows dominate test metrics. Worth
handling in the shared evaluation code (#8), e.g. per-platform metrics or
weighting by instrument.

`chla_z_uq.ipynb`, CQR on the OLCI overlap (all 11 bands finite, surface bin):
the sample grows from 2,073 to 6,878 rows. PACE-full coverage 0.86 → 0.74,
OLCI-11 0.83 → 0.77, with narrower intervals (0.87 → 0.74 and 0.73 → 0.76).
Coverage below nominal there is worth a look before it goes on the poster.

## OLCI matchups and the hyperspectral question

**From 2026-11-23**, `chla_z_uq` and `olci_l3_brt_compare` read OLCI from the
release `_plus_OLCI` tables instead of `olci_l3_matchups.parquet` (whose OOI ids
are daily). `olci_l3_matchups.ipynb` was not re-run and is superseded; its
rules are what the release uses. On `2026_11_23`, `brt_compare` (row split,
leaky) surface R²: PACE-full 0.860, PACE-11 0.848, OLCI-11 0.849, n_test 2,255;
same answer. `chla_z_uq` overlap (grouped split, 18,340 rows): surface RMSE
PACE-full 0.348, OLCI-11 0.352.

The history below is for the daily-OOI rebuild.

`olci_l3_matchups.ipynb` was re-run in full on 2026-11-22 (~4 h, 936 days, 0
failed days). 6,896 of 12,729 profiles have all 11 OLCI bands (Argo 4,936,
OOI 1,960). Delayed-mode OLCI ends 2026-10-01, so October 2026 profiles have no
OLCI match. The old rows could not be reused to save time: every day had new
profiles, and the notebook opens a day's granules if any profile on it is new.

`olci_l3_brt_compare.ipynb`, same profiles for all three, surface bin, test
split by row:

| | 2025_11_01 (n_test 322) | rebuild (n_test 1,144) |
|---|---:|---:|
| PACE-full (172 bands) | R² 0.762, RMSE 0.354 | R² 0.795, RMSE 0.312 |
| PACE-11 (OLCI bands) | R² 0.769, RMSE 0.348 | R² 0.787, RMSE 0.318 |
| OLCI-11 | R² 0.774, RMSE 0.344 | R² 0.793, RMSE 0.314 |

Same answer as the story's finding 1: hyperspectral PACE does no better than
the 11 OLCI bands. Deep bins (100–200 m) improve most with the extra data
(PACE-full R² roughly 0.21–0.41 → 0.30–0.46).

## Suspect OOI data: Pioneer offshore profilers, Aug–Sep 2026 (found 2026-11-24)

`ooi-cp13nopm-wfp01-04-flortk000` and `ooi-cp13sopm-wfp01-04-flortk000` read a
monthly median of 4–10 mg m⁻³ in August and September 2026, nearly the same at
20, 50 and 70 m, while PACE `pace_chlor_a` at the site is about 0.22 mg m⁻³. A
uniform high value through a stratified summer column looks like fouling or a
calibration problem, not a bloom. The release's biofouling flag
(`flag_deep_biofouling`, run.py) only looks at 100–200 m bins, which these
shelf profilers (about 80 m deep at most) don't reach.

360 OOI windows, 5% of shelf rows. In the Argo + OOI space-time run they double
the shelf RMSE at depth in mg m⁻³ (50–60 m: 1.56 with them, 0.74 without;
70–80 m: 1.86 vs 0.74); R² on log10 barely changes. They also explain the
shelf "outlier" Eli saw in the exploratory linear figure
(`explore_coastal_depth.py --scale linear`).

cp13sopm also has uniform ~2 mg m⁻³ columns in Nov–Dec 2024 and Oct 2025;
those could be real winter mixing and were not flagged here.

Not fixed yet. The QC belongs in fish-pace-datasets (not edited from here).
