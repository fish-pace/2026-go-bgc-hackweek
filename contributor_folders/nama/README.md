# Nadir — CHLA-Z uncertainty quantification

The published CHLA-Z BRT is a **point estimate** (`log10` CHLA). This folder
adds prediction intervals on the **full PACE training table** (12,705 rows from the
November 2026 rebuild; 5,510 in release `2025_11_01`),
plus CQR on the OLCI–PACE overlap.

## Notebook

**[`chla_z_uq.ipynb`](chla_z_uq.ipynb)** — runs anywhere; no Hub / S3 / `/tmp`. Reads the training tables over HTTPS.

1. Load Argo + OOI PACE matchups from fish-pace/fish-pace-datasets (version set by `DATA_RELEASE` in the first code cell)
2. Same merge + biofouling drop as the methods notebook
3. Shared **float / instrument** split (`random_state=42`): Argo `PLATFORM_NUMBER`, OOI instrument id; Argo and OOI groups split separately. 20% of train **groups** are conformal calib
4. Fit, per depth bin:
   - mean BRT (current CHLA-Z style; no UQ)
   - quantile BRT (10 / 50 / 90%) — adaptive width, often undercovers
   - mean BRT + conformal (constant width at that depth)
   - **CQR** — conformalized quantile regression (adaptive + calibrated)
   - **CQR Mondrian** — separate conformal pad for Argo vs OOI
5. Report RMSE, 80% coverage, and interval width (surface, Argo vs OOI, all 20 bins)
6. Coverage vs predicted CHLA (surface and 150–160 m) to check tail validity
7. **Rrs gain Monte Carlo** (5%, spectrally correlated) through the mean BRT vs CQR — input sensitivity, not added to CQR
8. **CQR on the OLCI overlap** (all 11 bands finite): PACE-full vs OLCI-11, new grouped split on that sample

## Data

The Argo and OOI PACE matchups are read over the network from a tagged release
of [fish-pace/fish-pace-datasets](https://github.com/fish-pace/fish-pace-datasets/releases),
set by `DATA_RELEASE` in each notebook's first code cell:

```text
https://raw.githubusercontent.com/fish-pace/fish-pace-datasets/<DATA_RELEASE>/datasets/chla_z/data/
  CHLA_argo_profiles_plus_PACE.parquet
  CHLA_ooi_profiles_plus_PACE.parquet
```

The saved outputs use `DATA_RELEASE = "chla-z-rebuild"`: the November 2026 rebuild
on the fish-pace-datasets PR branch (fish-pace/fish-pace-datasets#4), with
ascending-only Argo, QC applied before binning, OOI depth and duplicate fixes, the
Sauzède correction, PACE V3.2 and data to 2026-10-31. Switch to the release tag
once that release exists.

`2025_11_01` is the pre-hackweek data, byte-identical to `fish-pace/chla-z`
`brt_training_data/`. That is what these notebooks read at the hackweek.
(Before 2026-11-05 they read a local `chla-z` checkout.)

Local file: `contributor_folders/nama/olci_l3_matchups.parquet`, written by
`olci_l3_matchups.ipynb` from the same `DATA_RELEASE`.

Kernel: `gobgc` conda env. Does not import `ml_utils.py` (that module needs `scikit-image`). Solar hour is computed in the notebook.

## Run

```bash
conda activate gobgc
cd /Users/nmamnun/GO-BGC-Workshop/2026-go-bgc-hackweek
jupyter lab contributor_folders/nama/chla_z_uq.ipynb
```
