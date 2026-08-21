# Charlie Turner — CHLA-Z

## `duplicate_rows_walkthrough.ipynb`

Why `CHLA_ooi_profiles_plus_PACE.parquet` is 42% duplicate rows, worked step by
step from the published file and the notebooks that created it.

**Headline:** the published parquet has 10,989 rows but only 6,415 distinct
`profile_id`s. Every duplicate group is the *same* **Ocean Observatories
Initiative** (OOI) instrument-day joined to a *different* **Plankton, Aerosol,
Cloud, ocean Ecosystem** (PACE) granule — the OOI columns are byte-identical
within a group; only the `pace_*` match-up columns differ.

**Cause:** `ooi.ipynb` stamps every row at midnight UTC (`dt.floor("D")` daily
mean), and `ml_utils.one_file_matches` matches on `[t_start, t_start + 24 h)`.
PACE DAY granules start slightly *before* midnight, so a midnight-stamped OOI
day falls inside two consecutive granule windows. The `nrt` flag does not
explain it — the dominant duplicate pattern is `(False, False)`, two *standard*
granules.

**The fix already exists upstream.** `ooi.ipynb` computes `df_dedup` (keep the
granule closest in time, prefer non-NRT) and then saves `df_merged` instead.
Applying that same logic to the published parquet collapses it to exactly 6,415
rows with no duplicates — reproduced in the last cell. `argo-matchups.ipynb`
merges on `df_dedup` and is unaffected.

## Running it

Self-contained on a bare clone of this repo — no network:

```bash
jupyter lab duplicate_rows_walkthrough.ipynb   # run all
```

| Input | Where it comes from |
|---|---|
| `data/CHLA_ooi_profiles_plus_PACE.parquet` | copied from `fish-pace/chla-z`, `brt_training_data/` (2.4 MB, Apache-2.0) |
| `upstream/ooi.ipynb`, `upstream/argo-matchups.ipynb` | copied from `fish-pace/fish-pace-datasets` @ `9e65251`, `datasets/chla_z/notebooks/`, **outputs stripped** (source only — the notebook reads their code cells) |
| `../../ml_utils.py` | this repo's root copy, byte-identical to `chla-z/notebooks/ml_utils.py` |

Needs `pandas`, `numpy`, `pyarrow`. Verified end to end from this directory:
all 23 code cells execute clean.

## `quad_chart_1min.png`

One-slide summary of the week's data-cleaning work on the CHLA-Z training set, for the
Friday readout (four panels: the argopy standard-mode coverage trap; the June–Aug 2026
Sauzède recalibration rewriting `CHLA_ADJUSTED`; Argo ⇄ OOI match-up population; factory
vs adjusted fluorometer agreement). Built offline from the `drift` project's experiments
26–28; every number on it traces to those experiments' READMEs.
