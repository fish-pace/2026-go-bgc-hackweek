#!/usr/bin/env python3
"""
Run the CHLA-Z daily NetCDF pipeline on a local machine.

This is a local-execution counterpart to `notebooks/pipeline_chla_z_netcdfs.ipynb`.
That notebook targets the NASA/NOAA JupyterHub: it requires a Dask-Gateway server,
reads GCP credentials from a hardcoded `/home/jovyan/...` path, and uploads results
to `gs://nmfs_odp_nwfsc` (which requires write access to the NOAA bucket).

This script keeps the science identical -- same BRT bundle, same
`predict_all_depths_for_day`, same `build_chla_profile_dataset` derived metrics,
same NetCDF encoding -- but:

  * writes NetCDFs to a local directory (GCS upload is opt-in via --upload-bucket)
  * runs serially by default, or on a local Dask cluster via --workers
  * takes Earthdata credentials from your own ~/.netrc
  * supports --bbox to process a region instead of the full globe, which makes
    a test run take minutes instead of hours

NOTE ON THE PACE COLLECTION NAME
--------------------------------
NASA retired `PACE_OCI_L3M_RRS` and replaced it with `PACE_OCI_L3M_AOP`.
A CMR query for the old short_name now returns zero collections, so the
pipeline notebooks (which still reference it) find no granules. This script
defaults to the current name; override with --short-name if needed.

Setup
-----
  uv venv --python 3.12 ~/.virtualenvs/chla-z
  uv pip install --python ~/.virtualenvs/chla-z/bin/python -r scripts/requirements-local.txt

Granule access needs a free Earthdata account (https://urs.earthdata.nasa.gov/users/new)
with a matching entry in ~/.netrc:

  machine urs.earthdata.nasa.gov login YOUR_USER password YOUR_PASS

Examples
--------
  # single day, small region -- good first test
  python scripts/run_chla_z_local.py --start 2024-03-05 --end 2024-03-05 \
      --bbox -70 0 -40 20 --outdir ./out

  # a week, full globe, 4 local dask workers
  python scripts/run_chla_z_local.py --start 2024-03-01 --end 2024-03-07 \
      --workers 4 --outdir ./out
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

import numpy as np
import xarray as xr

REPO_ROOT = Path(__file__).resolve().parent.parent

# ml_utils.py lives in a different place in each repo that carries it, so search
# rather than hardcode:
#   2026-go-bgc-hackweek -> repo root
#   chla-z               -> notebooks/
#   the 2i2c hub         -> /home/jovyan/2026-go-bgc-hackweek
_ML_UTILS_CANDIDATES = [
    REPO_ROOT,
    REPO_ROOT.parent,                       # contributor_folders/<name>/ -> repo root
    REPO_ROOT.parent.parent,
    REPO_ROOT / "notebooks",
    Path.home() / "Desktop" / "chla-z" / "notebooks",
    Path("/home/jovyan/2026-go-bgc-hackweek"),
]
for _cand in _ML_UTILS_CANDIDATES:
    if (_cand / "ml_utils.py").is_file():
        sys.path.insert(0, str(_cand))
        ML_UTILS_DIR = _cand
        break
else:
    ML_UTILS_DIR = None

# The BRT bundle is ~6.5 MB and is not committed to the hackweek repo, so there
# is no in-repo default there; fall back to a sibling chla-z checkout.
_BUNDLE_CANDIDATES = [
    REPO_ROOT / "models" / "brt_chla_profiles_bundle.zip",
    Path.home() / "Desktop" / "chla-z" / "models" / "brt_chla_profiles_bundle.zip",
    Path("/home/jovyan/chla-z/models/brt_chla_profiles_bundle.zip"),
]
DEFAULT_BUNDLE = next(
    (p for p in _BUNDLE_CANDIDATES if p.is_file()), _BUNDLE_CANDIDATES[0]
)
DEFAULT_SHORT_NAME = "PACE_OCI_L3M_AOP"
GRANULE_PATTERN = "*.DAY.*.4km.nc"
RRS_VAR = "Rrs"

# Constant (non-Rrs) features the BRT expects. Matches the production notebook.
PREDICT_CONSTS = {"solar_hour": 0, "type": 1}


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Generate daily CHLA-Z NetCDF files locally.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--start", required=True, help="Start date, YYYY-MM-DD")
    p.add_argument("--end", required=True, help="End date, YYYY-MM-DD (inclusive)")
    p.add_argument("--outdir", default="./chla_z_out", help="Local output directory")
    p.add_argument("--bundle", default=str(DEFAULT_BUNDLE), help="Path to the BRT bundle zip")
    p.add_argument("--short-name", default=DEFAULT_SHORT_NAME, help="CMR collection short_name")
    p.add_argument(
        "--bbox", nargs=4, type=float, metavar=("W", "S", "E", "N"), default=None,
        help="Optional lon/lat subset, e.g. --bbox -70 0 -40 20. Full globe if omitted.",
    )
    p.add_argument(
        "--workers", type=int, default=0,
        help="Local Dask workers. 0 = plain serial loop (lowest memory).",
    )
    p.add_argument("--lat-chunk", type=int, default=100, help="NetCDF latitude chunk size")
    p.add_argument("--lon-chunk", type=int, default=100, help="NetCDF longitude chunk size")
    p.add_argument(
        "--pred-lat-chunk", type=int, default=100,
        help="Latitude rows per prediction block (controls peak memory)",
    )
    p.add_argument("--force", action="store_true", help="Reprocess days whose output already exists")
    p.add_argument("--limit", type=int, default=None, help="Process at most N granules (smoke test)")
    p.add_argument(
        "--upload-bucket", default=None,
        help="Optional GCS bucket to upload to. Requires write access; omit to stay local.",
    )
    p.add_argument(
        "--upload-prefix", default="CB/fish-pace-datasets/chla-z/netcdf",
        help="Object prefix used when --upload-bucket is set",
    )
    return p.parse_args(argv)


def earthdata_login():
    """Authenticate to Earthdata, preferring ~/.netrc, then env vars."""
    import earthaccess

    for strategy in ("netrc", "environment"):
        try:
            auth = earthaccess.login(strategy=strategy, persist=False)
            if auth is not None and auth.authenticated:
                print(f"Earthdata: authenticated via {strategy}")
                return auth
        except Exception:
            pass
    raise RuntimeError(
        "Earthdata login failed. Add a machine urs.earthdata.nasa.gov entry to ~/.netrc, "
        "or set EARTHDATA_USERNAME / EARTHDATA_PASSWORD. "
        "Register free at https://urs.earthdata.nasa.gov/users/new"
    )


def day_string(granule):
    """Extract YYYYMMDD from a granule's temporal metadata."""
    import pandas as pd

    iso = granule["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]
    ts = pd.to_datetime(iso)
    # CMR reports UTC-aware timestamps; the published product uses naive
    # datetime64, and mixing the two breaks comparison against --start/--end.
    if ts.tz is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    return ts



# ---------------------------------------------------------------------------
# Fallback copy of build_chla_profile_dataset.
#
# Verbatim from notebooks/pipeline_chla_z_netcdfs.ipynb in fish-pace/chla-z,
# used only when the importable ml_utils.py does not provide it. Do not edit
# this copy independently -- if it needs to change, change it upstream.
# ---------------------------------------------------------------------------
def _build_chla_profile_dataset(CHLA: xr.DataArray) -> xr.Dataset:
    """
    Given CHLA(time, z, lat, lon), compute derived metrics and
    return an xr.Dataset suitable for writing to Zarr/NetCDF.
    """
    # Start from CHLA's own dataset so its coords (including z_start/z_end) win
    ds = CHLA.to_dataset(name="CHLA")

    # ---- Layer thickness (z dimension) ----
    z_start = CHLA.coords.get("z_start", None)
    z_end   = CHLA.coords.get("z_end", None)

    if (z_start is not None) and (z_end is not None):
        z_thick = (z_end - z_start).rename("z_thickness")   # (z)
    else:
        # fallback: uniform layer thickness, e.g. 10 m
        z_thick = xr.full_like(CHLA["z"], 10.0).rename("z_thickness")

    z_center = CHLA["z"]

    # total CHLA in column (used for validity + center-of-mass)
    col_total = CHLA.sum("z")          # (time, lat, lon)
    valid = col_total > 0              # True where there is some CHLA

    # ---- Integrated CHLA (nominal 0–200 m; actual range = z extent) ----
    CHLA_int = (CHLA * z_thick).sum("z")
    CHLA_int = CHLA_int.where(valid)
    CHLA_int.name = "CHLA_int_0_200"

    # ---- Peak value and depth (NaN-safe) ----
    CHLA_filled = CHLA.fillna(-np.inf)
    peak_idx = CHLA_filled.argmax("z")       # (time, lat, lon) integer indices

    CHLA_peak = CHLA.isel(z=peak_idx).where(valid)
    CHLA_peak.name = "CHLA_peak"

    CHLA_peak_depth = z_center.isel(z=peak_idx).where(valid)
    CHLA_peak_depth.name = "CHLA_peak_depth"

    # ---- Depth-weighted mean depth (center of mass) ----
    num = (CHLA * z_center).sum("z")
    den = col_total
    depth_cm = (num / den).where(valid)
    depth_cm.name = "CHLA_depth_center_of_mass"

    # ---- Attach derived fields to the dataset ----
    ds["CHLA_int_0_200"] = CHLA_int
    ds["CHLA_peak"] = CHLA_peak
    ds["CHLA_peak_depth"] = CHLA_peak_depth
    ds["CHLA_depth_center_of_mass"] = depth_cm
    ds["z_thickness"] = z_thick

    # ---- Variable attributes ----
    ds["CHLA"].attrs.setdefault("units", "mg m-3")
    ds["CHLA"].attrs.setdefault("long_name", "Chlorophyll-a concentration")
    ds["CHLA"].attrs.setdefault("standard_name", "mass_concentration_of_chlorophyll_a_in_sea_water")
    ds["CHLA"].attrs.setdefault(
        "description",
        "BRT-derived chlorophyll-a profiles from PACE hyperspectral Rrs",
    )

    ds["CHLA_int_0_200"].attrs.update(
        units="mg m-2",
        long_name="Depth-integrated chlorophyll-a",
        description=(
            "Vertical integral of CHLA over the available depth bins "
            "(nominally 0–200 m; actual range defined by z_start/z_end)."
        ),
    )

    ds["CHLA_peak"].attrs.update(
        units="mg m-3",
        long_name="Peak chlorophyll-a concentration in the water column",
        standard_name="mass_concentration_of_chlorophyll_a_in_sea_water",
        description="Maximum CHLA value over depth at each (time, lat, lon).",
    )

    ds["CHLA_peak_depth"].attrs.update(
        units="m",
        long_name="Depth of peak chlorophyll-a",
        positive="down",
        description=(
            "Depth (bin center) where CHLA is maximal in the water column "
            "at each (time, lat, lon)."
        ),
    )

    ds["CHLA_depth_center_of_mass"].attrs.update(
        units="m",
        long_name="Chlorophyll-a depth center of mass",
        positive="down",
        description=(
            "Depth of the chlorophyll-a center of mass, computed as "
            "sum_z(CHLA * z) / sum_z(CHLA)."
        ),
    )

    ds["z_thickness"].attrs.update(
        units="m",
        long_name="Layer thickness",
        description=(
            "Thickness of each vertical bin used for depth integration. "
            "Derived from z_end - z_start when available; otherwise set to a "
            "uniform nominal thickness."
        ),
    )
    ds["z_thickness"] = ds["z_thickness"].expand_dims(time=ds["time"])

    return ds

def align_wavelengths_to_model(R, feature_cols, atol=0.01):
    """Snap R's wavelength coordinate onto the band centres the BRT expects.

    PACE_OCI_L3M_AOP (V3_2) reports band centres to sub-nm precision
    (e.g. 355.782), while the model's feature names are integers
    (pace_Rrs_356) because the training matchups rounded them.
    `predict_all_depths_for_day` compares the two with atol=0.01, so the raw
    AOP coordinate trips that check even though the bands are identical --
    verified on 2024-03-05: 172 bands, 1:1, max deviation 0.497 nm, every
    band satisfying round(actual) == expected.

    The coordinate is only rewritten when the match is provably 1:1 and every
    band rounds exactly onto an expected value. Anything else raises, so a real
    change in PACE's band set is never silently papered over.
    """
    import numpy as np

    want = np.array(
        [float(c.split("_")[-1]) for c in feature_cols if c.startswith("pace_Rrs_")],
        dtype=float,
    )
    wl = np.asarray(R["wavelength"].values, dtype=float)

    if wl.size != want.size:
        raise ValueError(
            f"Granule has {wl.size} wavelengths but the model expects {want.size}. "
            "The PACE band set has changed; the model needs retraining, not a coordinate fix."
        )
    if np.allclose(wl, want, atol=atol):
        return R  # already compatible, nothing to do
    if np.all(np.round(wl) == want):
        return R.assign_coords(wavelength=want)

    bad = np.where(np.round(wl) != want)[0]
    raise ValueError(
        f"{bad.size} band(s) do not round onto the expected centres, e.g. "
        f"{[(float(want[i]), float(wl[i])) for i in bad[:3]]}. "
        "Refusing to remap -- this is a real band mismatch."
    )


def process_one_granule(granule, cfg):
    """Predict CHLA(z) for one day and write a local NetCDF. Returns a status string."""
    import numpy as np
    import xarray as xr
    import earthaccess
    import ml_utils as mu

    day = day_string(granule)
    day_str = day.strftime("%Y%m%d")
    outdir = Path(cfg["outdir"])
    outdir.mkdir(parents=True, exist_ok=True)
    local_path = outdir / f"chla_z_{day_str}_v2.nc"

    if local_path.exists() and not cfg["force"]:
        return f"[{day_str}] SKIP (exists at {local_path})"

    bundle = mu.load_ml_bundle(cfg["bundle"])

    files = earthaccess.open([granule], pqdm_kwargs={"disable": True})
    rrs_ds = xr.open_dataset(files[0])
    try:
        if "time" in rrs_ds.dims:
            R = rrs_ds[RRS_VAR].sel(time=day).squeeze("time")
        else:
            R = rrs_ds[RRS_VAR]

        bbox = cfg["bbox"]
        if bbox is not None:
            w, s, e, n = bbox
            # PACE L3M grids run north -> south, so lat slices are descending
            R = R.sel(lat=slice(n, s), lon=slice(w, e))
            if R.sizes.get("lat", 0) == 0 or R.sizes.get("lon", 0) == 0:
                return f"[{day_str}] EMPTY after --bbox subset; check W S E N ordering"

        R = R.transpose("lat", "lon", "wavelength")
        R = align_wavelengths_to_model(R, bundle.meta["feature_cols"])

        # Prefer the predict helper stored in the bundle (this is what produced the
        # published product); fall back to the current ml_utils implementation.
        predict = getattr(bundle, "predict", None)
        if predict is None or getattr(bundle, "predict_fn", None) is None:
            predict = mu.predict_all_depths_for_day

        pred = predict(
            R,
            brt_models=bundle.model,
            feature_cols=bundle.meta["feature_cols"],
            consts=PREDICT_CONSTS,
            chunk_size_lat=cfg["pred_lat_chunk"],
            time=day.to_datetime64(),
            z_name="z",
            silent=True,
            linear=True,
        )

        # ml_utils.py in the hackweek repo predates build_chla_profile_dataset
        # (it is still inlined in two chla-z notebooks). Prefer the library
        # version when present so this picks up the upstream one automatically.
        build = getattr(mu, "build_chla_profile_dataset", _build_chla_profile_dataset)
        ds_day = build(pred)

        lat_chunk = min(cfg["lat_chunk"], ds_day.sizes["lat"])
        lon_chunk = min(cfg["lon_chunk"], ds_day.sizes["lon"])
        chunks4d = (1, ds_day.sizes["z"], lat_chunk, lon_chunk)
        chunks3d = (1, lat_chunk, lon_chunk)
        chunks2d = (1, ds_day.sizes["z"])
        enc = {"dtype": "float32", "zlib": True, "complevel": 4}
        encoding = {
            "CHLA": {**enc, "chunksizes": chunks4d},
            "CHLA_int_0_200": {**enc, "chunksizes": chunks3d},
            "CHLA_peak": {**enc, "chunksizes": chunks3d},
            "CHLA_peak_depth": {**enc, "chunksizes": chunks3d},
            "CHLA_depth_center_of_mass": {**enc, "chunksizes": chunks3d},
            "z_thickness": {**enc, "chunksizes": chunks2d},
        }

        ds_day.to_netcdf(local_path, engine="h5netcdf", encoding=encoding)
        msg = f"[{day_str}] WROTE {local_path} ({local_path.stat().st_size / 1e6:.1f} MB)"

        if cfg["upload_bucket"]:
            from google.cloud import storage

            client = storage.Client()
            blob = client.bucket(cfg["upload_bucket"]).blob(
                f"{cfg['upload_prefix']}/chla_z_{day_str}_v2.nc"
            )
            blob.upload_from_filename(str(local_path))
            msg += f" -> gs://{cfg['upload_bucket']}/{cfg['upload_prefix']}/"

        return msg
    finally:
        rrs_ds.close()


def main(argv=None):
    args = parse_args(argv)

    bundle_path = Path(args.bundle)
    if not bundle_path.exists():
        raise SystemExit(f"BRT bundle not found: {bundle_path}")

    import ml_utils  # noqa: F401  -- fail early with a clear message if deps are missing
    import earthaccess

    earthdata_login()

    results = earthaccess.search_data(
        short_name=args.short_name,
        granule_name=GRANULE_PATTERN,
        temporal=(args.start, args.end),
    )
    # CMR temporal ranges are inclusive at both ends and can return the day after
    # `--end`; keep only granules whose own date falls inside the requested window.
    import pandas as pd

    lo, hi = pd.to_datetime(args.start), pd.to_datetime(args.end)
    results = [g for g in results if lo <= day_string(g).normalize() <= hi]
    results.sort(key=day_string)

    if args.limit:
        results = results[: args.limit]

    print(f"Found {len(results)} DAY granules in {args.start}..{args.end}")
    if not results:
        print(
            "Nothing to do. If you overrode --short-name, note that PACE_OCI_L3M_RRS "
            "was retired; the current collection is PACE_OCI_L3M_AOP."
        )
        return 0

    cfg = {
        "outdir": args.outdir,
        "bundle": str(bundle_path),
        "bbox": args.bbox,
        "force": args.force,
        "lat_chunk": args.lat_chunk,
        "lon_chunk": args.lon_chunk,
        "pred_lat_chunk": args.pred_lat_chunk,
        "upload_bucket": args.upload_bucket,
        "upload_prefix": args.upload_prefix,
    }

    ok = err = 0
    n = len(results)

    if args.workers and args.workers > 0:
        from dask.distributed import Client, LocalCluster, as_completed

        # ~3 GB output per global day plus the Rrs working set; give each worker room
        cluster = LocalCluster(
            n_workers=args.workers, threads_per_worker=1, memory_limit="12GiB"
        )
        client = Client(cluster)
        print(f"Local Dask cluster: {args.workers} workers | {client.dashboard_link}")
        try:
            futures = [client.submit(process_one_granule, g, cfg, pure=False) for g in results]
            for fut in as_completed(futures):
                try:
                    print(f"[{ok + err + 1}/{n}] {fut.result()}")
                    ok += 1
                except Exception as e:
                    err += 1
                    print(f"[{ok + err}/{n}] ERROR: {e!r}")
        finally:
            client.close()
            cluster.close()
    else:
        for i, g in enumerate(results, 1):
            try:
                print(f"[{i}/{n}] {process_one_granule(g, cfg)}", flush=True)
                ok += 1
            except Exception as e:
                err += 1
                print(f"[{i}/{n}] ERROR: {e!r}", flush=True)
                traceback.print_exc()

    print(f"Finished. Success={ok}, Errors={err}")
    return 1 if err else 0


if __name__ == "__main__":
    raise SystemExit(main())
