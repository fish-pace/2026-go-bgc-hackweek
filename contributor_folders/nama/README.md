# Nadir — CHLA-Z uncertainty quantification

The published CHLA-Z BRT is a **point estimate** (`log10` CHLA). This folder
adds prediction intervals on the **full PACE training table** (~5,510 rows),
plus CQR on the OLCI–PACE overlap.

## Notebook

**[`chla_z_uq.ipynb`](chla_z_uq.ipynb)** — local, no Hub / S3 / `/tmp`.

1. Load Argo + OOI PACE matchups from the sibling `chla-z` checkout
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

Expects:

```text
/Users/nmamnun/GO-BGC-Workshop/chla-z/brt_training_data/
  CHLA_argo_profiles_plus_PACE.parquet
  CHLA_ooi_profiles_plus_PACE.parquet

contributor_folders/nama/olci_l3_matchups.parquet
```

Kernel: `gobgc` conda env. Does not import `ml_utils.py` (that module needs `scikit-image`). Solar hour is computed in the notebook.

## Run

```bash
conda activate gobgc
cd /Users/nmamnun/GO-BGC-Workshop/2026-go-bgc-hackweek
jupyter lab contributor_folders/nama/chla_z_uq.ipynb
```
