# Peter — CHLA-Z work

## Start here

**[`PACE_AOP_FINDINGS.md`](PACE_AOP_FINDINGS.md)** — two findings that affect everyone working on
CHLA-Z:

1. `PACE_OCI_L3M_RRS` is retired (returns zero CMR collections); use `PACE_OCI_L3M_AOP`.
2. AOP V3_2 band centres break the BRT's wavelength check — with a verified fix.
3. The published CHLA-Z product **cannot be reproduced** from currently available PACE data.

## `run_chla_z_local.py`

Runs the daily CHLA-Z pipeline **off-hub** — no Dask-Gateway, no GCS write access, no
`/home/jovyan/` paths. Same science as `chla-z/notebooks/pipeline_chla_z_netcdfs.ipynb`: same BRT
bundle, same `predict_all_depths_for_day`, same derived metrics and NetCDF encoding.

Useful if you want to generate CHLA-Z for a region or date the published product doesn't cover, or to
check a retrained model against the operational one.

### Setup

```bash
uv venv --python 3.12 ~/.virtualenvs/chla-z
uv pip install --python ~/.virtualenvs/chla-z/bin/python -r requirements-local.txt
```

You need a free [Earthdata account](https://urs.earthdata.nasa.gov/users/new) in `~/.netrc`:

```
machine urs.earthdata.nasa.gov login YOUR_USER password YOUR_PASS
```

You do **not** need a Google Cloud account — the NOAA bucket is anonymously readable.

You do need the BRT bundle (~6.5 MB, too big for this repo). The script auto-finds it in a sibling
`chla-z` checkout, or pass `--bundle /path/to/brt_chla_profiles_bundle.zip`.

### Run

```bash
# one day, small region -- ~45 seconds
python run_chla_z_local.py --start 2024-03-05 --end 2024-03-05 \
    --bbox -70 0 -40 20 --outdir ./out

# a week, full globe, 4 local workers
python run_chla_z_local.py --start 2024-03-01 --end 2024-03-07 \
    --workers 4 --outdir ./out
```

`--bbox W S E N` is the difference between a 45-second test and a ~3 GB global day. `--workers 0`
(the default) runs serially, which uses the least memory.

### Notes

- Writes locally by default. `--upload-bucket` exists but needs NOAA write access to
  `gs://nmfs_odp_nwfsc`, which we don't have.
- Portable across layouts — finds `ml_utils.py` in this repo's root, a `chla-z` checkout, or
  `/home/jovyan/2026-go-bgc-hackweek` on the hub.
- Carries a fallback copy of `build_chla_profile_dataset` because this repo's `ml_utils.py` predates
  it. Verified bit-identical output either way, across all six variables.

## Reproducing the comparison

The correlation figures in the findings doc come from running the command above, then comparing
against the published store:

```python
mine = xr.open_dataset("out/chla_z_20240305_v2.nc")
pub  = xr.open_zarr("gcs://nmfs_odp_nwfsc/CB/fish-pace-datasets/chla-z/zarr",
                    consolidated=False, storage_options={"token": "anon"}) \
         .sel(time="2024-03-05").sel(lat=slice(20, 0), lon=slice(-70, -40))
```
