# Rebuilt training data (November 2026)

The notebooks on branch `rebuilt-training-data` read the tables rebuilt in
fish-pace/fish-pace-datasets#4 (branch `chla-z-rebuild`), via
`DATA_RELEASE = "chla-z-rebuild"`. When Eli cuts the release, replace that
value with the tag in all five notebooks. Build details, decisions and the
before/after tables live in fish-pace-datasets
`claude/notes/chla-z-rebuild-2026-11.md`.

## Draft Methods wording (for the poster, issue #8)

This replaces the earlier #8 comment, which described pooling descending and
ascending levels. That is no longer done. It has not been posted to #8.

> **Data.** BGC-Argo profiles (March 2024 – October 2026) were taken from the
> Ifremer ERDDAP server with argopy 1.5.0 in expert mode (snapshot
> 2026-11-06). Only ascending profiles were used. Adjusted chlorophyll
> (`CHLA_ADJUSTED`) levels with QC flags 1, 2, 5 or 8 were averaged in 10 m
> pressure bins from 0 to 200 m. OOI fluorometer data (30 profilers and fixed
> instruments) were taken from the OOI ERDDAP server, kept where the
> aggregate QC flag was 1, and averaged per instrument and day in the same 10 m
> bins. Fixed-depth instruments were assigned their known depth. OOI
> fluorescence was converted to chlorophyll with the regional
> fluorescence:chlorophyll ratios of Sauzède et al., putting it on the same
> basis as Argo `CHLA_ADJUSTED`. Each profile was matched to PACE OCI Level-3
> daily 4 km V3.2 remote-sensing reflectance (172 bands), chlorophyll-a and
> Kd(490) at the nearest grid cell, from the file whose day covers the profile
> time, using standard files before near-real-time ones. Profiles with no valid
> Rrs (cloud, glint) were dropped, as were 24 OOI profiles with uniformly high
> chlorophyll from 100 to 200 m (likely biofouling). The training set has
> 12,705 profiles: 9,542 Argo from 831 floats and 3,163 OOI from 30
> instruments.

Split counted from the tables with the notebook's Rrs and biofouling rules.
All 24 flagged profiles are OOI.

## How the results changed (methods notebook, same code, new data)

| | `2025_11_01` | rebuild |
|---|---:|---:|
| training rows (after biofouling drop) | 5,510 | 12,705 |
| biofouling-flagged profiles | 20 | 24 |
| train / test rows | 4,408 / 1,102 | 10,164 / 2,541 |
| test R² (all bins, log10) | 0.821 | 0.778 |
| test RMSE (log10) | 0.303 | 0.318 |
| test bias (log10) | −0.016 | 0.000 |
| cell 49 profile-shape metrics: N | 485 | 1,983 |
| cell 49 r2_log / rmse_log | 0.367 / 0.326 | 0.356 / 0.361 |

The methods notebook still uses a random row split (the leakage the poster's
methods block fixes). These numbers compare data versions with the split held
fixed. They are not the poster's skill numbers.

`chla_z_uq.ipynb` (grouped split by float/instrument, surface bin): coverage of
the 80% intervals moves toward nominal with the larger table. CQR 0.68 → 0.78,
CQR Mondrian 0.68 → 0.81, mean BRT + conformal 0.72 → 0.79. Per-bin CQR
coverage is 0.81–0.86 below the surface (was 0.76–0.94).

`chla_z_uq.ipynb`, CQR on the OLCI overlap (all 11 bands finite, surface bin):
the sample grows from 2,073 to 6,878 rows. PACE-full coverage 0.86 → 0.74,
OLCI-11 0.83 → 0.77, with narrower intervals (0.87 → 0.74 and 0.73 → 0.76).
Coverage below nominal there is worth a look before it goes on the poster.

## OLCI matchups and the hyperspectral question

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
