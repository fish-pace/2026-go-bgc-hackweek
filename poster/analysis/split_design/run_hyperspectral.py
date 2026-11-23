"""Does hyperspectral help? PACE-172 vs PACE-11 vs OLCI-11 (issue #10).

Same BRT and leakage-free split as run.py (space-time block, 1° cell x 30 d,
grouped 5-fold CV), on the union of every profile with a PACE and/or an OLCI
match (release tables `_plus_PACE` and `_plus_OLCI`).

Folds are assigned once over that union, so every model below is trained
and scored on the same folds. All models are scored on the same rows: the
held-out profiles that have both sensors (PACE Rrs and all 11 OLCI bands).

  Band for band (trained on profiles with both sensors):
    pace172      all 172 PACE bands
    pace11       the PACE band nearest each OLCI band centre
    olci11       the 11 OLCI bands
  More data (each sensor trained on all of its own matchups):
    pace172_all  PACE-172 trained on every PACE profile
    olci11_all   OLCI-11 trained on every OLCI profile (OLCI matches more)

All models also get solar hour and platform type, as in run.py. Output is
one parquet per (dataset, repeat) in the long format of run.py, with the
model name in the `design` column, so metrics.py and profile_metrics.py work
on it unchanged.

Imports run.py without changing it.
"""

import argparse
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

import run

OLCI_BANDS = [400, 412, 443, 490, 510, 560, 620, 665, 674, 681, 709]
VARIANT = "1deg_30d"
MODELS = ["pace172", "pace11", "olci11", "pace172_all", "olci11_all"]


def load_olci(cache: Path) -> pd.DataFrame:
    parts = []
    for p in ("argo", "ooi"):
        f = cache / f"CHLA_{p}_profiles_plus_OLCI.parquet"
        if not f.exists():
            tmp = f.with_suffix(".part")
            pd.read_parquet(f"{run.DATA_URL}/{f.name}").to_parquet(tmp)
            tmp.rename(f)
        o = pd.read_parquet(f).rename(columns={"LATITUDE": "lat", "LONGITUDE": "lon", "TIME": "time"})
        if p == "argo":
            o["instrument"] = "argo-" + o["PLATFORM_NUMBER"].astype(str)
        else:
            o["instrument"] = o["profile_id"].astype(str).str.replace(r"_\d{8}(T\d{2})?$", "", regex=True)
        o["platform"] = p
        parts.append(o)
    o = pd.concat(parts, ignore_index=True)
    bands = [f"olci_Rrs_{b}" for b in OLCI_BANDS]
    o = o[o[bands].notna().all(axis=1)]
    return o


def build(cache: Path):
    d, feats, chl = run.load(cache)  # PACE rows, biofouling dropped
    o = load_olci(cache)
    bands = [f"olci_Rrs_{b}" for b in OLCI_BANDS]
    deep = [c for c in chl if 100 <= 0.5 * sum(map(int, c.split("_")[1:])) <= 200]
    o = o[~run.flag_deep_biofouling(o, deep)]

    keep = ["profile_id", "platform", "instrument", "time", "lat", "lon"] + chl
    u = pd.concat([d[keep + ["pixel"]], o.loc[~o["profile_id"].isin(d["profile_id"]), keep]], ignore_index=True)
    u = u.merge(o[["profile_id"] + bands], on="profile_id", how="left")
    rrs = [c for c in feats if c.startswith("pace_Rrs_")]
    u = u.merge(d[["profile_id"] + rrs], on="profile_id", how="left")
    u["has_pace"] = u["profile_id"].isin(d["profile_id"])
    u["has_olci"] = u[bands].notna().all(axis=1)
    # OLCI-only OOI rows have no PACE pixel; a rounded position stands in as the site.
    u["pixel"] = u["pixel"].fillna("site-" + u["lat"].round(2).astype(str) + "_" + u["lon"].round(2).astype(str))
    u["solar_hour"] = run.solar_hour(u["time"], u["lon"])
    u["type"] = (u["platform"] == "ooi").astype(int)
    u["days"] = (pd.to_datetime(u["time"], utc=True) - pd.Timestamp("2024-01-01", tz="UTC")).dt.total_seconds() / 86400
    u["lon180"] = ((u["lon"].astype(float) + 180) % 360) - 180

    wl = np.array([int(c.rsplit("_", 1)[1]) for c in rrs])
    pace11 = [rrs[int(np.argmin(np.abs(wl - b)))] for b in OLCI_BANDS]
    extra = ["solar_hour", "type"]
    sets = {
        "pace172": (rrs + extra, "both"), "pace11": (pace11 + extra, "both"), "olci11": (bands + extra, "both"),
        "pace172_all": (rrs + extra, "pace"), "olci11_all": (bands + extra, "olci"),
    }
    return u.reset_index(drop=True), sets, chl, pace11


def run_unit(u, sets, bins, dataset, rep, out_dir: Path, n_jobs):
    sub = u if dataset == "both" else u[u["platform"] == dataset]
    sub = sub.reset_index(drop=True)
    seed = 1000 + rep
    folds = run.folds_for(sub, "spacetime", VARIANT, seed)
    overlap = (sub["has_pace"] & sub["has_olci"]).to_numpy()
    train_ok = {"both": overlap, "pace": sub["has_pace"].to_numpy(), "olci": sub["has_olci"].to_numpy()}
    Xs = {m: sub[f].to_numpy(dtype=float) for m, (f, _) in sets.items()}

    def one(m, f, b):
        y = sub[b].to_numpy(dtype=float)
        r = run.fit_predict(Xs[m], y, (folds != f) & train_ok[sets[m][1]], (folds == f) & overlap, seed)
        if r is None:
            return None
        idx, yt, yp = r
        return pd.DataFrame({"row": idx, "bin": b, "fold": f, "design": m,
                             "y": yt.astype("float32"), "yhat": yp.astype("float32")})

    tasks = [(m, f, b) for m in sets for f in range(run.N_FOLDS) for b in bins]
    parts = Parallel(n_jobs=n_jobs)(delayed(one)(*t) for t in tasks)
    p = pd.concat([x for x in parts if x is not None], ignore_index=True)
    meta = sub[["profile_id", "platform", "instrument", "pixel"]].iloc[p["row"]].reset_index(drop=True)
    p = pd.concat([p, meta], axis=1).assign(dataset=dataset, variant=VARIANT, repeat=rep)
    p["group"] = run.groups_for(sub, "spacetime", VARIANT)[p["row"]]
    for m, g in p.groupby("design"):
        f = out_dir / f"{dataset}__{m}__{VARIANT}__r{rep}.parquet"
        g.to_parquet(f.with_suffix(".part"))
        f.with_suffix(".part").rename(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=run.DEFAULT_OUT / "runs" / "hyperspectral")
    ap.add_argument("--datasets", nargs="+", default=["argo", "ooi", "both"])
    ap.add_argument("--bins", choices=["all", "every-other"], default="all")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--n-jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()

    u, sets, chl, pace11 = build(run.DEFAULT_CACHE)
    print("PACE bands used for PACE-11:", pace11, flush=True)
    for p in ("argo", "ooi"):
        s = u[u["platform"] == p]
        print(f"{p}: pace {int(s.has_pace.sum())}, olci {int(s.has_olci.sum())}, both {int((s.has_pace & s.has_olci).sum())}",
              flush=True)
    bins = chl if args.bins == "all" else chl[::2]
    out = args.out / "preds"
    out.mkdir(parents=True, exist_ok=True)
    for ds in args.datasets:
        for r in range(args.repeats):
            if all((out / f"{ds}__{m}__{VARIANT}__r{r}.parquet").exists() for m in MODELS):
                continue
            t0 = time.time()
            run_unit(u, sets, bins, ds, r, out, args.n_jobs)
            print(f"{ds} r{r}: {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
