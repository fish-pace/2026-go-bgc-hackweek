"""Physics pilot: does GLORYS12 temperature structure help predict OOI CHLA(z)?

Same BRT, data and leakage-free designs as split_design/run.py, OOI only,
with four input sets:

  rrs       PACE Rrs + solar hour (the current model)
  ctx       rrs + day of year (sin, cos) + lat/lon. Control: at a fixed
            mooring these name the site and its seasonal cycle, so any gain
            from physics beyond this is information about the day, not just
            site climatology.
  phys      rrs + GLORYS12 temperature structure
  ctx+phys  both

Physics features, from the day's GLORYS12 profile at the pixel
(extract_glorys.py): T at 0.5, 25, 50, 100, 200 m (linear in depth between
model levels), T(0.5) - T(50), T(0.5) - T(200), depth of the strongest
downward cooling (max -dT/dz above 200 m), and the model mixed-layer depth
(mlotst). Below the model seafloor (shelf cells) features are NaN, which the
BRT handles.

Matching: the GLORYS daily mean of the row's UTC date, like the L3 daily
match for Rrs.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "split_design"))
import run  # noqa: E402

GLORYS = run.DEFAULT_OUT.parent / "glorys12" / "ooi_pixels"
PHYS = ["T_0", "T_25", "T_50", "T_100", "T_200", "dT_0_50", "dT_0_200", "z_thermo", "mlotst"]
CTX = ["doy_sin", "doy_cos", "lat", "lon180"]


def physics_table() -> pd.DataFrame:
    g = pd.concat(pd.read_parquet(f) for f in sorted(GLORYS.glob("*.parquet")))
    tc = [c for c in g.columns if c.startswith("T_")]
    z = np.array([float(c[2:]) for c in tc])
    T = g[tc].to_numpy(float)
    out = pd.DataFrame({"pixel": g["pixel"].to_numpy(), "date": pd.to_datetime(g["time"]).dt.strftime("%Y-%m-%d")})
    for zz in [0, 25, 50, 100, 200]:
        out[f"T_{zz}"] = [np.interp(max(zz, z[0]), z[np.isfinite(r)], r[np.isfinite(r)], right=np.nan)
                          if np.isfinite(r).sum() > 1 else np.nan for r in T]
    out["dT_0_50"] = out["T_0"] - out["T_50"]
    out["dT_0_200"] = out["T_0"] - out["T_200"]
    dTdz = -np.diff(T, axis=1) / np.diff(z)
    zmid = 0.5 * (z[1:] + z[:-1])
    ok = zmid <= 200
    d = np.where(np.isfinite(dTdz[:, ok]), dTdz[:, ok], -np.inf)
    out["z_thermo"] = np.where(np.isfinite(dTdz[:, ok]).any(axis=1), zmid[ok][d.argmax(axis=1)], np.nan)
    out["mlotst"] = g["mlotst"].to_numpy()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=run.DEFAULT_OUT / "runs" / "physics-pilot")
    ap.add_argument("--designs", nargs="+", default=["spacetime", "site", "region"])
    ap.add_argument("--sets", nargs="+", default=["rrs", "ctx", "phys", "ctx+phys"])
    ap.add_argument("--bins", choices=["all", "every-other"], default="every-other")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--n-jobs", type=int, default=4)
    args = ap.parse_args()
    args.datasets, args.row_repeats = ["ooi"], 0
    args.cell_deg, args.block_days, args.region_deg = [1.0], [30.0], [10.0]

    d, feats, chl = run.load(run.DEFAULT_CACHE)
    d = d[d.platform == "ooi"].copy()
    d["date"] = pd.to_datetime(d["time"], utc=True).dt.strftime("%Y-%m-%d")
    d = d.merge(physics_table(), on=["pixel", "date"], how="left").reset_index(drop=True)
    doy = pd.to_datetime(d["time"], utc=True).dt.dayofyear.to_numpy()
    d["doy_sin"], d["doy_cos"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
    print(f"OOI rows {len(d)}; with physics {d['T_0'].notna().sum()}", flush=True)

    base = [f for f in feats if f != "type"]
    sets = {"rrs": base, "ctx": base + CTX, "phys": base + PHYS, "ctx+phys": base + CTX + PHYS}
    bins = chl if args.bins == "all" else chl[::2]
    for name in args.sets:
        out = args.out / name.replace("+", "_")
        (out / "preds").mkdir(parents=True, exist_ok=True)
        for ds, design, v, r in run.units(args):
            f = out / "preds" / f"{ds}__{design}__{v}__r{r}.parquet"
            if not f.exists():
                run.run_unit(d, sets[name], bins, ds, design, v, r, f, args.n_jobs)
                print(name, "done", f.name, flush=True)


if __name__ == "__main__":
    main()
