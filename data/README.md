# data/

`training_data.parquet` is a cached copy of the `dataset` table built in
`notebooks/methods_fit_BRT_CHLA_z.ipynb` (cells 7 and 10), committed
2026-08-18 at the start of the hackweek.

- **Source:** fish-pace/fish-pace-datasets release `2025_11_01`,
  `CHLA_argo_profiles_plus_PACE.parquet` + `CHLA_ooi_profiles_plus_PACE.parquet`,
  with the 20 biofouled profiles removed.
- **Shape:** 5,510 rows, 207 columns, 4,712 unique `profile_id`
  (2,770 Argo rows, 2,740 OOI rows). The OOI rows still include the duplicates
  described in fish-pace/fish-pace-datasets#4.
- **Used by:** `contributor_folders/eli/level-2.ipynb` (only for its points).
  The methods notebook no longer reloads it.

It is **not** updated when a new fish-pace-datasets release comes out. For
results, build the table from a release in the notebook instead of reading this
file.

`data.csv` is a placeholder from the repo's initial commit.
