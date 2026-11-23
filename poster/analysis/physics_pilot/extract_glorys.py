"""Daily GLORYS12 temperature profiles and mixed-layer depth at the OOI pixels.

Physics pilot (Eli, 2026-11-23): does model temperature structure help
predict CHLA below the surface at coastal moorings, where Rrs alone gives
R² near 0 below 20 m under a leakage-free split (issue #20)?

Product: Copernicus Marine GLOBAL_MULTIYEAR_PHY_001_030 (GLORYS12V1),
dataset cmems_mod_glo_phy_my_0.083deg_P1D-m: daily, 1/12°, reanalysis (its
daily series ran to late October 2026 when checked on 2026-11-23). GLORYS12
rather than ARMOR3D (MULTIOBS_GLO_PHY_TSUV_3D_MYNRT_015_012) because it is
daily, finer, a model (so it covers the shelf), and does not interpolate the
Argo T/S of the very floats we score on. A product would need a near-real-time
source; a reanalysis is fine for a pilot.

For each OOI PACE pixel (22 of them, from the release tables via run.py), the
nearest GLORYS cell with water at the surface is taken; at shelf sites the
cell under the pixel can be land or too shallow in the model. One parquet per
pixel, so a failed request is redone alone: rerun the script and finished
pixels are skipped. Needs a Copernicus Marine login (copernicusmarine login).
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "split_design"))
import run  # noqa: E402

DATASET = "cmems_mod_glo_phy_my_0.083deg_P1D-m"
OUT = run.DEFAULT_OUT.parent / "glorys12" / "ooi_pixels"
BOX = 0.15  # degrees around the pixel to search for a water cell
MAX_DEPTH = 230.0


def fetch_pixel(lat, lon, t0, t1):
    import copernicusmarine as cm

    ds = cm.open_dataset(
        dataset_id=DATASET,
        variables=["thetao", "mlotst"],
        minimum_latitude=lat - BOX, maximum_latitude=lat + BOX,
        minimum_longitude=lon - BOX, maximum_longitude=lon + BOX,
        minimum_depth=0, maximum_depth=MAX_DEPTH,
        start_datetime=t0, end_datetime=t1,
        service="arco-time-series",
    )
    surf = ds["thetao"].isel(depth=0, time=0).load()
    la, lo = np.meshgrid(ds.latitude.values, ds.longitude.values, indexing="ij")
    dist = np.hypot(la - lat, (lo - lon) * np.cos(np.radians(lat)))
    dist[~np.isfinite(surf.values)] = np.inf
    i, j = np.unravel_index(np.argmin(dist), dist.shape)
    cell = ds.isel(latitude=i, longitude=j).load()
    t = cell["thetao"].to_pandas()  # time x depth
    t.columns = [f"T_{z:.1f}" for z in t.columns]
    t["mlotst"] = cell["mlotst"].to_pandas()
    t["glorys_lat"], t["glorys_lon"] = float(cell.latitude), float(cell.longitude)
    t["glorys_km"] = float(dist[i, j]) * 111.0
    return t.reset_index()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    d, _, _ = run.load(run.DEFAULT_CACHE)
    o = d[d.platform == "ooi"]
    px = o.groupby("pixel").agg(lat=("pace_Rrs_lat", "first"), lon=("pace_Rrs_lon", "first"),
                                t0=("time", "min"), t1=("time", "max"))
    for name, r in px.iterrows():
        f = args.out / f"{name}.parquet"
        if f.exists():
            continue
        t0 = (pd.Timestamp(r.t0) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        t1 = (pd.Timestamp(r.t1) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        for attempt in range(4):
            try:
                s = time.time()
                t = fetch_pixel(r.lat, r.lon, t0, t1)
                t["pixel"] = name
                t.to_parquet(f.with_suffix(".part"))
                f.with_suffix(".part").rename(f)
                print(f"{name}: {len(t)} days, cell {t.glorys_km.iat[0]:.1f} km away, {time.time() - s:.0f} s",
                      flush=True)
                break
            except Exception as e:  # network drops; retry with backoff
                print(f"{name}: attempt {attempt + 1} failed: {e}", flush=True)
                time.sleep(20 * (attempt + 1))


if __name__ == "__main__":
    main()
