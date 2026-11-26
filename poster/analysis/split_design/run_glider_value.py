"""Does glider data help predict Chl a on the slope and shelf? (#27, Eli 2026-11-26)

Two models per fold and bin, same space-time folds (1 deg x 30 d), same
held-out rows, release run.DATA_RELEASE (use CHLAZ_DATA_RELEASE=2026_11_26):

  argo_bias_cut100  run_platform.py's argo_bias, but glider bins at or below
                    100 m are removed (set missing) for training and scoring,
                    on every water-depth class. Below 100 m glider bins were
                    unpredictable (r^2 0.02-0.06 on shelf, slope and open
                    ocean) because the fluorometer's deep offset (~0.03-0.2)
                    is as large as the real Chl a there (#27 comment 5).
  no_glider_train   the same, trained on Argo + OOI only. Predicts every
                    held-out row as Argo; OOI rows get the OOI offset, glider
                    rows get none (there is no glider data to estimate one).
                    This is "the product without gliders".

Comparing the two on held-out glider rows asks whether glider training data
improves predictions where the gliders are (mostly slope and shelf);
comparing them on Argo + OOI rows asks whether it changes anything else.
Output: one parquet per (design, repeat) like run_platform.py, so
compare_glider_release.py and fig_profiles_by_class.py functions read it.
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
MODELS = ["argo_bias_cut100", "no_glider_train"]
CUT_M = 100  # glider bins with top >= CUT_M are dropped


def run_unit(d, feats, bins, rep, out_dir: Path, n_jobs):
    seed = 1000 + rep
    folds = run.folds_for(d, "spacetime", VARIANT, seed)
    plat = d["platform"].to_numpy()
    X = d[feats].to_numpy(dtype=float)
    X_argo = X.copy()
    X_argo[:, feats.index("type")] = 0

    def fit(tr, ly):
        return HistGradientBoostingRegressor(random_state=seed, **run.BRT_KW).fit(X[tr], ly[tr])

    def one(f, b):
        y = d[b].to_numpy(dtype=float)
        ok = np.isfinite(y) & (y > 0)
        tr, te = (folds != f) & ok, (folds == f) & ok
        tr_ng = tr & (plat != "glider")
        if tr_ng.sum() < 50 or te.sum() == 0:
            return None
        ly = np.log10(np.where(ok, y, np.nan))
        idx = np.flatnonzero(te)
        parts = []
        for name, trm in [("argo_bias_cut100", tr), ("no_glider_train", tr_ng)]:
            m = fit(trm, ly)
            bias = np.zeros(len(idx))
            for k in ("ooi", "glider"):
                trk = trm & (plat == k)
                if trk.any():
                    bias[plat[idx] == k] = (ly[trk] - m.predict(X_argo[trk])).mean()
            yp = m.predict(X_argo[idx]) + bias
            parts.append(pd.DataFrame({"row": idx, "bin": b, "fold": f, "design": name,
                                       "y": ly[idx].astype("float32"), "yhat": yp.astype("float32"),
                                       "platform_bias": bias.astype("float32")}))
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
    ap.add_argument("--out", type=Path, default=run.DEFAULT_OUT / "runs" / f"glider-value-{run.DATA_RELEASE}")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--n-jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()
    d, feats, chl = run.load(run.DEFAULT_CACHE, run.PLATFORMS_V2)
    deep = [b for b in chl if int(b.split("_")[1]) >= CUT_M]
    g = d["platform"] == "glider"
    print(f"glider bins >= {CUT_M} m set missing: {int(d.loc[g, deep].notna().sum().sum())} values")
    d.loc[g, deep] = np.nan
    # Rows that lost every bin cannot be trained on or scored; drop them.
    d = d[d[chl].notna().any(axis=1)].reset_index(drop=True)
    print(f"rows {len(d)}: {d.platform.value_counts().to_dict()}")
    out = args.out / "preds"
    out.mkdir(parents=True, exist_ok=True)
    for r in range(args.repeats):
        if all((out / f"both__{m}__{VARIANT}__r{r}.parquet").exists() for m in MODELS):
            continue
        t = time.time()
        run_unit(d, feats, chl, r, out, args.n_jobs)
        print(f"both r{r}: {time.time() - t:.0f} s", flush=True)


if __name__ == "__main__":
    main()
