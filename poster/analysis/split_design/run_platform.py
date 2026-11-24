"""Platform as a model input: drop it, or predict as Argo and correct (Eli, 2026-11-24).

Until now every model had a `type` input (1 = OOI, 0 = Argo). A map has no
platform, and the OOI flag can stand in for "this is greener coastal water"
(OOI sites are greener), so skill that comes from it would not carry into a
product. Three variants, Argo + OOI data, same folds, same held-out rows:

  with_type   Rrs + solar hour + type (what the poster has used so far)
  no_type     Rrs + solar hour; the model never knows the platform
  argo_bias   trained like with_type, but every row is predicted as Argo
              (type = 0); OOI predictions then get a per-bin offset, the mean
              OOI residual (log10) of those as-Argo predictions on the fold's
              own training rows. This is how a product would be made (as Argo)
              and compared with OOI.

All OOI windows, unweighted (the window test showed weighting barely
matters). QC exclusion applied by run.load. Same BRT, space-time split
(1° x 30 d) and seeds as run.py, which it imports unchanged. Output: one
parquet per (variant, repeat), variant name in `design`, so metrics.py and
explore_skill_baseline.py work on it. Reruns skip finished units.
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
MODELS = ["with_type", "no_type", "argo_bias"]


def run_unit(d, feats, bins, rep, out_dir: Path, n_jobs):
    seed = 1000 + rep
    folds = run.folds_for(d, "spacetime", VARIANT, seed)
    ooi = (d["platform"] == "ooi").to_numpy()
    X = d[feats].to_numpy(dtype=float)
    ti = feats.index("type")
    X_argo = X.copy()
    X_argo[:, ti] = 0
    X_no = np.delete(X, ti, axis=1)

    def one(f, b):
        y = d[b].to_numpy(dtype=float)
        ok = np.isfinite(y) & (y > 0)
        tr, te = (folds != f) & ok, (folds == f) & ok
        if tr.sum() < 50 or te.sum() == 0:
            return None
        ly = np.log10(np.where(ok, y, np.nan))
        idx = np.flatnonzero(te)
        m = HistGradientBoostingRegressor(random_state=seed, **run.BRT_KW).fit(X[tr], ly[tr])
        m0 = HistGradientBoostingRegressor(random_state=seed, **run.BRT_KW).fit(X_no[tr], ly[tr])
        p_with = m.predict(X[idx])
        p_no = m0.predict(X_no[idx])
        p_argo = m.predict(X_argo[idx])
        tro = tr & ooi
        bias = (ly[tro] - m.predict(X_argo[tro])).mean() if tro.any() else 0.0
        p_bias = p_argo + np.where(ooi[idx], bias, 0.0)
        parts = []
        for name, yp in [("with_type", p_with), ("no_type", p_no), ("argo_bias", p_bias)]:
            parts.append(pd.DataFrame({"row": idx, "bin": b, "fold": f, "design": name,
                                       "y": ly[idx].astype("float32"), "yhat": yp.astype("float32"),
                                       "ooi_bias": np.float32(bias)}))
        return pd.concat(parts)

    tasks = [(f, b) for f in range(run.N_FOLDS) for b in bins]
    res = Parallel(n_jobs=n_jobs)(delayed(one)(f, b) for f, b in tasks)
    p = pd.concat([x for x in res if x is not None], ignore_index=True)
    meta = d[["profile_id", "platform", "instrument", "pixel"]].iloc[p["row"]].reset_index(drop=True)
    p = pd.concat([p, meta], axis=1).assign(dataset="both", variant=VARIANT, repeat=rep)
    p["group"] = run.groups_for(d, "spacetime", VARIANT)[p["row"]]
    for m, g in p.groupby("design"):
        f = out_dir / f"both__{m}__{VARIANT}__r{rep}.parquet"
        g.to_parquet(f.with_suffix(".part"))
        f.with_suffix(".part").rename(f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=run.DEFAULT_OUT / "runs" / "platform")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--n-jobs", type=int, default=os.cpu_count())
    ap.add_argument("--bins", type=int, default=None, help="first N bins only (testing)")
    args = ap.parse_args()
    d, feats, chl = run.load(run.DEFAULT_CACHE)
    bins = chl[: args.bins] if args.bins else chl
    out = args.out / "preds"
    out.mkdir(parents=True, exist_ok=True)
    for r in range(args.repeats):
        if all((out / f"both__{m}__{VARIANT}__r{r}.parquet").exists() for m in MODELS):
            continue
        t = time.time()
        run_unit(d, feats, bins, r, out, args.n_jobs)
        print(f"both r{r}: {time.time() - t:.0f} s", flush=True)


if __name__ == "__main__":
    main()
