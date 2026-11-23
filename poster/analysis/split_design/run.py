"""Fit the CHLA-Z boosted regression trees under several train/test split designs.

Issue #20 (data leakage and split design). The same model is fit to the same
data (fish-pace-datasets release DATA_RELEASE), and only the way rows are put
into train and test changes. Every prediction is saved, so the metrics and
figures can be redone without refitting (see metrics.py).

One "unit" is (dataset, design, variant, repeat). Each unit writes its own
parquet file and is skipped if that file exists, so a run can be stopped and
restarted, and units can be spread over machines with --shard i/n.

Designs, from most to least leakage expected:

  row       naive 80/20 random row split, one split per repeat (what you get
            by running a BRT with train_test_split). Predictions on the 20%.
  period    new period: groups are calendar months, all places.
  instrument new instrument: Argo float (PLATFORM_NUMBER), OOI instrument.
            OOI instruments at one site share a PACE pixel, so this still
            leaks across co-located instruments; `site` fixes that.
  site      Argo float, OOI PACE pixel (co-located instruments together).
  spacetime cell x time block: every row in one lat/lon cell during one time
            block is held out together; the same cell at other times can be in
            training. Variant "<deg>deg_<days>d".
  region    new region, all time: lat/lon boxes. Variant "<deg>deg".

All designs except `row` use grouped 5-fold cross-validation, so every row
gets one out-of-fold prediction per repeat. Groups are shuffled per repeat and
assigned to folds greedily by row count, which keeps folds near 20% even when
groups differ a lot in size (OOI sites do).

Model settings and the biofouling filter are those of
contributor_folders/nama/chla_z_uq.ipynb.
"""

import argparse
import os
import time
from pathlib import Path

# One thread per fit; parallelism comes from running fits side by side, which
# is faster than letting each HistGradientBoosting fit use every core.
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.ensemble import HistGradientBoostingRegressor

DATA_RELEASE = "2026_11_23"
DATA_URL = (
    "https://raw.githubusercontent.com/fish-pace/fish-pace-datasets/"
    f"{DATA_RELEASE}/datasets/chla_z/data"
)
TABLES = {
    "argo": "CHLA_argo_profiles_plus_PACE.parquet",
    "ooi": "CHLA_ooi_profiles_plus_PACE.parquet",
}
DEFAULT_CACHE = Path.home() / "shared-public" / "chla-z" / "fish-pace-datasets" / DATA_RELEASE
DEFAULT_OUT = Path.home() / "shared-public" / "chla-z" / "split-design"

BRT_KW = dict(
    max_depth=6,
    learning_rate=0.05,
    max_iter=400,
    validation_fraction=0.1,
    early_stopping=True,
)
N_FOLDS = 5


# --------------------------------------------------------------------- data


def fetch(cache: Path) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    out = {}
    for key, name in TABLES.items():
        p = cache / name
        if not p.exists():
            tmp = p.with_suffix(".part")
            pd.read_parquet(f"{DATA_URL}/{name}").to_parquet(tmp)
            tmp.rename(p)
        out[key] = pd.read_parquet(p)
    return out


def solar_hour(t: pd.Series, lon: pd.Series) -> np.ndarray:
    """Local mean solar hour = UTC hour + lon/15 (as in chla_z_uq)."""
    t = pd.to_datetime(t, utc=True)
    h = t.dt.hour + t.dt.minute / 60.0 + t.dt.second / 3600.0
    lon = ((lon.astype(float) + 180) % 360) - 180
    return ((h + lon / 15.0) % 24.0).to_numpy()


def flag_deep_biofouling(df, deep_bins, min_valid=5, min_chl=1.0, max_spread=2):
    """Uniformly high CHLA from 100 to 200 m: likely biofouling (chla_z_uq)."""
    v = df[deep_bins].to_numpy(dtype=float)
    n = np.isfinite(v).sum(axis=1)
    lo = np.nanmin(np.where(np.isfinite(v), v, np.inf), axis=1)
    hi = np.nanmax(np.where(np.isfinite(v), v, -np.inf), axis=1)
    return (n >= min_valid) & (lo > min_chl) & ((hi - lo) < max_spread)


def load(cache: Path) -> tuple[pd.DataFrame, list, list]:
    t = fetch(cache)
    a = t["argo"].rename(columns={"LATITUDE": "lat", "LONGITUDE": "lon", "TIME": "time"})
    o = t["ooi"]
    rrs = [c for c in o.columns if c.startswith("pace_Rrs_") and c[-1].isdigit()]
    chl = sorted(
        [c for c in o.columns if c.startswith("CHLA_") and c[-1].isdigit()],
        key=lambda c: int(c.split("_")[1]),
    )
    keep = ["profile_id", "time", "lat", "lon", "pace_Rrs_lat", "pace_Rrs_lon"] + rrs + chl

    a = a.assign(platform="argo", instrument="argo-" + a["PLATFORM_NUMBER"].astype(str))
    o = o.assign(
        platform="ooi",
        # profile_id is <instrument>_<YYYYMMDD>T<HH> for the 3 h windows.
        instrument=o["profile_id"].astype(str).str.replace(r"_\d{8}(T\d{2})?$", "", regex=True),
    )
    d = pd.concat([a[keep + ["platform", "instrument"]], o[keep + ["platform", "instrument"]]], ignore_index=True)
    d = d.dropna(subset=rrs, how="all")
    d["solar_hour"] = solar_hour(d["time"], d["lon"])
    d["type"] = (d["platform"] == "ooi").astype(int)

    deep = [c for c in chl if 100 <= 0.5 * sum(map(int, c.split("_")[1:])) <= 200]
    bad = flag_deep_biofouling(d, deep)
    print(f"biofouling flagged: {bad.sum()} of {len(d)}")
    d = d.loc[~bad].reset_index(drop=True)

    # Grouping keys used by the designs.
    d["month"] = pd.to_datetime(d["time"], utc=True).dt.strftime("%Y-%m")
    d["pixel"] = np.where(
        d["platform"] == "ooi",
        "ooi-px-" + d["pace_Rrs_lat"].round(4).astype(str) + "_" + d["pace_Rrs_lon"].round(4).astype(str),
        d["instrument"],
    )
    d["days"] = (pd.to_datetime(d["time"], utc=True) - pd.Timestamp("2024-01-01", tz="UTC")).dt.total_seconds() / 86400
    d["lon180"] = ((d["lon"].astype(float) + 180) % 360) - 180
    return d, rrs + ["solar_hour", "type"], chl


# ------------------------------------------------------------------ designs


def groups_for(d: pd.DataFrame, design: str, variant: str) -> np.ndarray:
    if design == "period":
        return d["month"].to_numpy()
    if design == "instrument":
        return d["instrument"].to_numpy()
    if design == "site":
        return d["pixel"].to_numpy()
    if design == "spacetime":
        deg, days = variant.split("deg_")
        deg, days = float(deg), float(days.rstrip("d"))
        return (
            np.floor(d["lat"] / deg).astype(int).astype(str)
            + "_" + np.floor(d["lon180"] / deg).astype(int).astype(str)
            + "_" + np.floor(d["days"] / days).astype(int).astype(str)
        ).to_numpy()
    if design == "region":
        deg = float(variant.rstrip("deg"))
        return (
            np.floor(d["lat"] / deg).astype(int).astype(str)
            + "_" + np.floor(d["lon180"] / deg).astype(int).astype(str)
        ).to_numpy()
    raise ValueError(design)


def group_folds(groups: np.ndarray, seed: int, k: int = N_FOLDS) -> np.ndarray:
    """Shuffled groups, each given to the fold with fewest rows so far."""
    rng = np.random.default_rng(seed)
    uniq, inv, counts = np.unique(groups, return_inverse=True, return_counts=True)
    order = rng.permutation(len(uniq))
    fold_of_group = np.empty(len(uniq), dtype=int)
    load_ = np.zeros(k)
    for g in order:
        f = int(np.argmin(load_))
        fold_of_group[g] = f
        load_[f] += counts[g]
    return fold_of_group[inv]


def folds_for(d: pd.DataFrame, design: str, variant: str, seed: int) -> np.ndarray:
    """Fold id per row; -1 means train-only (used by the 80/20 row split)."""
    if design == "row":
        rng = np.random.default_rng(seed)
        f = np.full(len(d), -1)
        f[rng.permutation(len(d))[: int(round(0.2 * len(d)))]] = 0
        return f
    return group_folds(groups_for(d, design, variant), seed)


# ---------------------------------------------------------------- fitting


def fit_predict(X, y, train, test, seed):
    ok_tr = train & np.isfinite(y) & (y > 0)
    ok_te = test & np.isfinite(y) & (y > 0)
    if ok_tr.sum() < 50 or ok_te.sum() == 0:
        return None
    m = HistGradientBoostingRegressor(random_state=seed, **BRT_KW)
    m.fit(X[ok_tr], np.log10(y[ok_tr]))
    idx = np.flatnonzero(ok_te)
    return idx, np.log10(y[idx]), m.predict(X[idx])


def run_unit(d, feats, bins, dataset, design, variant, rep, out: Path, n_jobs):
    sub = d if dataset == "both" else d[d["platform"] == dataset]
    sub = sub.reset_index(drop=True)
    seed = 1000 + rep
    folds = folds_for(sub, design, variant, seed)
    X = sub[feats].to_numpy(dtype=float)
    fold_ids = [0] if design == "row" else list(range(N_FOLDS))
    tasks = [(f, b) for f in fold_ids for b in bins]

    def one(f, b):
        y = sub[b].to_numpy(dtype=float)
        r = fit_predict(X, y, folds != f, folds == f, seed)
        if r is None:
            return None
        idx, yt, yp = r
        return pd.DataFrame(
            {"row": idx, "bin": b, "fold": f, "y": yt.astype("float32"), "yhat": yp.astype("float32")}
        )

    parts = Parallel(n_jobs=n_jobs)(delayed(one)(f, b) for f, b in tasks)
    p = pd.concat([x for x in parts if x is not None], ignore_index=True)
    meta = sub[["profile_id", "platform", "instrument", "pixel"]].iloc[p["row"]].reset_index(drop=True)
    p = pd.concat([p, meta], axis=1)
    p["group"] = (
        groups_for(sub, design, variant)[p["row"]] if design != "row" else p["profile_id"].to_numpy()
    )
    p = p.assign(dataset=dataset, design=design, variant=variant, repeat=rep)
    tmp = out.with_suffix(".part")
    p.to_parquet(tmp)
    tmp.rename(out)


# -------------------------------------------------------------------- main


def units(args):
    for ds in args.datasets:
        for design in args.designs:
            if design == "site" and ds == "argo":
                continue  # identical to `instrument` for Argo
            if design == "row":
                variants, reps = ["80-20"], args.row_repeats
            elif design == "spacetime":
                variants = [f"{c:g}deg_{b:g}d" for c in args.cell_deg for b in args.block_days]
                reps = args.repeats
            elif design == "region":
                variants, reps = [f"{r:g}deg" for r in args.region_deg], args.repeats
            else:
                variants, reps = ["-"], args.repeats
            for v in variants:
                for r in range(reps):
                    yield ds, design, v, r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT / "runs" / "full")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--datasets", nargs="+", default=["argo", "ooi", "both"])
    ap.add_argument(
        "--designs", nargs="+", default=["row", "period", "instrument", "site", "spacetime", "region"]
    )
    ap.add_argument("--bins", choices=["all", "every-other"], default="all")
    ap.add_argument("--repeats", type=int, default=5, help="repeats of grouped 5-fold CV")
    ap.add_argument("--row-repeats", type=int, default=5, help="repeats of the 80/20 row split")
    ap.add_argument("--cell-deg", type=float, nargs="+", default=[1.0])
    ap.add_argument("--block-days", type=float, nargs="+", default=[30.0])
    ap.add_argument("--region-deg", type=float, nargs="+", default=[10.0])
    ap.add_argument("--n-jobs", type=int, default=os.cpu_count())
    ap.add_argument("--shard", default="0/1", help="i/n: run every n-th unit starting at i")
    args = ap.parse_args()

    d, feats, chl = load(args.cache)
    bins = chl if args.bins == "all" else chl[::2]
    (args.out / "preds").mkdir(parents=True, exist_ok=True)
    print(f"rows {len(d)}: argo {sum(d.platform == 'argo')}, ooi {sum(d.platform == 'ooi')}; bins {len(bins)}")

    i, n = map(int, args.shard.split("/"))
    todo = list(units(args))[i::n]
    for k, (ds, design, v, r) in enumerate(todo, 1):
        f = args.out / "preds" / f"{ds}__{design}__{v}__r{r}.parquet"
        if f.exists():
            continue
        t0 = time.time()
        run_unit(d, feats, bins, ds, design, v, r, f, args.n_jobs)
        print(f"[{k}/{len(todo)}] {f.name}  {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
