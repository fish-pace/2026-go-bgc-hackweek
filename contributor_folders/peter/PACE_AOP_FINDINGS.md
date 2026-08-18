# PACE AOP V3_2 — two findings that affect CHLA-Z work

Peter Mastnak · 2026-08-18

Two things surfaced while getting the CHLA-Z daily pipeline running off-hub. The first will block
anyone predicting from PACE granules today. The second is a product-level issue worth Eli's attention.

---

## 1. `PACE_OCI_L3M_RRS` is retired — use `PACE_OCI_L3M_AOP`

A CMR query for the old short_name returns **zero collections**:

```
https://cmr.earthdata.nasa.gov/search/collections.json?short_name=PACE_OCI_L3M_RRS  ->  0
https://cmr.earthdata.nasa.gov/search/collections.json?short_name=PACE_OCI_L3M_AOP  ->  1
   C4184125822-OB_CLOUD | PACE OCI Level-3 Global Mapped Apparent Optical Properties
```

Only **V3_2** exists. Versions 2.0, 3.0 and 3.1 all return zero collections.

The `*.DAY.*.4km.nc` granule pattern still works — it matches the daily 4 km file and correctly
excludes the 8-day composites and the 0p1deg grids.

Status in our repos:

| Notebook | short_name |
|---|---|
| `2026-go-bgc-hackweek/notebooks/methods_fit_BRT_CHLA_z.ipynb` | `PACE_OCI_L3M_AOP` ✅ (Eli already fixed) |
| `chla-z/notebooks/pipeline_chla_z_netcdfs.ipynb` | `PACE_OCI_L3M_RRS` ❌ finds nothing |
| `chla-z/notebooks/methods_global_daily_netcdf.ipynb` | `PACE_OCI_L3M_RRS` ❌ finds nothing |

---

## 2. AOP band centres trip the model's wavelength check

**Symptom.** Predicting from an AOP granule raises:

```
ValueError: Mismatch between wavelengths implied by feature_cols and the R['wavelength'] coordinate.
First few from feature_cols: [346. 348. 351. 353. 356.]
First few from R.wavelength: [346.017 348.468 350.912 353.344 355.782]
```

**Cause.** AOP V3_2 reports band centres to sub-nm precision. The BRT's feature names are integers
(`pace_Rrs_356`) because the training matchups rounded them. `predict_all_depths_for_day`
(`ml_utils.py:904`) compares the two with `np.allclose(..., atol=0.01)`, and the real offsets reach
0.497 nm — so the check fails even though the bands are the same.

**These are the same bands.** Verified against the 2024-03-05 granule:

| Check | Result |
|---|---|
| Bands in granule | 172 |
| Bands the model wants | 172 |
| Unique nearest-neighbour matches | 172 of 172 |
| `round(actual) == expected` for every band | **True** |
| Max abs deviation | 0.497 nm (418.0↔417.512, 553.0↔552.511, 675.0↔674.503) |
| AOP bands unused by the model | 0 |

**Fix.** `align_wavelengths_to_model()` in `run_chla_z_local.py` snaps the coordinate onto the
integer centres. It only rewrites when the mapping is provably 1:1 and every band rounds exactly;
otherwise it raises, so a genuine band change can never be silently papered over.

Snapping is **value-neutral** — it rewrites coordinate labels only, never data:

```python
np.array_equal(R.values, R_snapped.values, equal_nan=True)   # True
```

---

## 3. The published CHLA-Z cannot be reproduced from AOP V3_2

Ran one day (2024-03-05) over 0–20°N, 70–40°W (`--bbox -70 0 -40 20`) and compared against the
published Zarr store for the same day and region.

**The grid matches exactly** — `lat`, `lon` and `z` all identical. **The values do not:**

| Variable | correlation | mean abs diff |
|---|---|---|
| `CHLA_peak_depth` | 0.939 | 5.94 m |
| `CHLA_int_0_200` | 0.983 | 1.06 mg m⁻² |
| `CHLA_peak` | 0.980 | 0.031 mg m⁻³ |

**This is the input data, not the code.** Three pieces of evidence:

1. My output's valid-pixel mask is **74,786**, which **exactly equals** the input Rrs mask — the
   output mask is entirely inherited from the granule.
2. The published product has **82,120** valid pixels in that region — **7,334 more than AOP V3_2
   even provides**. It was built from different inputs.
3. The PACE version behind the published product is **no longer retrievable** (only V3_2 remains).

**Implications for us**

- CHLA-Z v2 cannot be reproduced byte-for-byte from currently available PACE data.
- Days appended now would sit on a **different PACE reprocessing** than the existing 560 days,
  making the time series internally inconsistent.
- Anyone validating a retrained model against the published product will see this offset and may
  mistake it for a model problem. It isn't.
- The training matchup parquets were built from the old RRS collection, so retraining on fresh AOP
  matchups is not a like-for-like comparison either.

Worth deciding as a team whether the published product gets regenerated on V3_2, or whether we treat
it as a frozen v2 and label anything new as v3.

---

## Environment notes (no dependency manifest exists in either repo)

Two pins are load-bearing and cost me time:

- **`scikit-learn>=1.6,<1.9`** — 1.9.0 fails to unpickle `brt_chla_profiles_bundle.zip` with
  `ModuleNotFoundError: No module named '_loss'`. Verified working on 1.6.1 and 1.7.2.
- **`h5py`** — `h5netcdf` is only a wrapper and won't open anything without it.
- **`scikit-image`** — `ml_utils.py` imports it at module level (line ~1921), so it's required even
  for code paths that never compute SSIM.

See `requirements-local.txt`.

## Footnote: `ml_utils.py` now has three copies

Byte-identical today, guaranteed to drift:

- `2026-go-bgc-hackweek/ml_utils.py`
- `chla-z/notebooks/ml_utils.py`
- `chla-z/docs/text_and_talks/ml_utils.py`

`build_chla_profile_dataset` is separately inlined in two chla-z notebooks and is in none of the three
`ml_utils.py` copies.
