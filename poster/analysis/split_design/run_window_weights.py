"""Do the OOI 3 h windows add anything beyond leakage? (Eli, 2026-11-24)

The up to 8 windows of an OOI instrument-day share one daily PACE Rrs. Under
the space-time split they stay in one fold, so they cannot leak; the open
question is whether they help or hurt the model. Three training variants, all
on the same folds and all scored on the same held-out rows (every window):

  all       every window, weight 1 (what the poster uses)
  weighted  every window, weight 1/(windows that instrument-day), so each
            OOI instrument-day counts once, as an Argo profile does
  oneday    one window per instrument-day, drawn at random (seeded), so
            solar hour still spans the day across days

Argo rows are always in training with weight 1. An earlier test
(run_windows.py, runs/ooi-windows) kept one fixed window per day but scored
each variant on different rows; this one fixes the test set.

Same BRT, split and seeds as run.py (space-time, 1° x 30 d, 5 folds);
imports run.py without changing it. Output: one parquet per
(dataset, variant, repeat) in run.py's long format, variant name in `design`,
so metrics.py and profile_metrics.py work unchanged. Reruns skip finished units.
"""

import argparse
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.ensemble import HistGradientBoostingRegressor

import run

VARIANT = "1deg_30d"
MODELS = ["all", "weighted", "oneday"]


def fit_predict_w(X, y, train, test, w, seed):
    """run.fit_predict with a sample weight."""
    ok_tr = train & np.isfinite(y) & (y > 0)
    ok_te = test & np.isfinite(y) & (y > 0)
    if ok_tr.sum() < 50 or ok_te.sum() == 0:
        return None
    m = HistGradientBoostingRegressor(random_state=seed, **run.BRT_KW)
    m.fit(X[ok_tr], np.log10(y[ok_tr]), sample_weight=w[ok_tr])
    idx = np.flatnonzero(ok_te)
    return idx, np.log10(y[idx]), m.predict(X[idx])


def run_unit(sub, feats, bins, dataset, rep, out_dir: Path, n_jobs):
    seed = 1000 + rep
    folds = run.folds_for(sub, "spacetime", VARIANT, seed)
    X = sub[feats].to_numpy(dtype=float)
    ooi = (sub["platform"] == "ooi").to_numpy()
    # Instrument-day: the window id without its T<HH> suffix (see run_windows.py).
    day = sub["profile_id"].astype(str).str.replace(r"T\d{2}$", "", regex=True)
    n_win = day.map(day.value_counts()).to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    pick = sub.groupby(day).sample(n=1, random_state=rng).index
    one = ~ooi | np.isin(np.arange(len(sub)), pick)
    setup = {
        "all": (np.ones(len(sub), bool), np.ones(len(sub))),
        "weighted": (np.ones(len(sub), bool), np.where(ooi, 1 / n_win, 1.0)),
        "oneday": (one, np.ones(len(sub))),
    }

    def one_fit(m, f, b):
        keep, w = setup[m]
        y = sub[b].to_numpy(dtype=float)
        r = fit_predict_w(X, y, (folds != f) & keep, folds == f, w, seed)
        if r is None:
            return None
        idx, yt, yp = r
        return pd.DataFrame({"row": idx, "bin": b, "fold": f, "design": m,
                             "y": yt.astype("float32"), "yhat": yp.astype("float32")})

    tasks = [(m, f, b) for m in MODELS for f in range(run.N_FOLDS) for b in bins]
    parts = Parallel(n_jobs=n_jobs)(delayed(one_fit)(*t) for t in tasks)
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
    ap.add_argument("--out", type=Path, default=run.DEFAULT_OUT / "runs" / "window-weights")
    ap.add_argument("--datasets", nargs="+", default=["ooi", "both"])
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--n-jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()

    d, feats, chl = run.load(run.DEFAULT_CACHE)
    out = args.out / "preds"
    out.mkdir(parents=True, exist_ok=True)
    for ds in args.datasets:
        sub = (d if ds == "both" else d[d["platform"] == ds]).reset_index(drop=True)
        for r in range(args.repeats):
            if all((out / f"{ds}__{m}__{VARIANT}__r{r}.parquet").exists() for m in MODELS):
                continue
            t = time.time()
            run_unit(sub, feats, chl, ds, r, out, args.n_jobs)
            print(f"{ds} r{r}: {time.time() - t:.0f} s", flush=True)


if __name__ == "__main__":
    main()
