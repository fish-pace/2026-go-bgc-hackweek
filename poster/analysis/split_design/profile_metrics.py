"""Profile-level skill from the saved predictions: integrated CHLA and peak depth.

Eli (2026-11-23): total CHLA in the water column (0-200 m, or to the bottom)
is the most interesting quantity; the depth of the CHLA peak is the second.

Per profile (one row of the release tables) the out-of-fold predictions of all
its bins are put back together. Every design except `row` assigns folds by row
group, so all bins of a profile come from models that never saw its group;
under `row` the 20% test rows are whole profiles too.

Only the contiguous bins from 0-10 m down are used (stop at the first missing
bin), and observed and predicted are summed over the same bins:

  integrated CHLA = sum(CHLA_bin x 10 m), mg m^-2, scored on log10;
  peak depth      = mid-depth of the bin with the highest CHLA, scored as mean
                    absolute error (m) and the share within 20 m (as Kai did).

Subsets: `int5` = at least 5 contiguous bins (0-50 m or deeper), `full` = all
20 bins (0-200 m). Peak depth uses profiles with at least 10 contiguous bins
(to 100 m), else a surface peak is forced by truncation.

OOI note: only the three shallow profilers (CE04 offshore, RS01 slope base,
RS03 Axial) give such columns; Pioneer has none, and the shelf profilers
(CE01/02/06/07) give a few dozen short columns.

Writes profile_metrics.csv next to preds/.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

BINS = [f"CHLA_{a}_{a + 10}" for a in range(0, 200, 10)]
MID = np.arange(5, 200, 10)


def profiles(p: pd.DataFrame) -> pd.DataFrame:
    keys = ["dataset", "design", "variant", "repeat", "profile_id", "platform", "pixel"]
    y = p.pivot_table(index=keys, columns="bin", values="y").reindex(columns=BINS)
    yh = p.pivot_table(index=keys, columns="bin", values="yhat").reindex(columns=BINS)
    ok = y.notna().to_numpy()
    n = np.where(ok.all(axis=1), 20, np.argmin(ok, axis=1))
    n = np.where(ok[:, 0], n, 0)
    mask = np.arange(20)[None, :] < n[:, None]
    Y, YH = 10 ** y.to_numpy(), 10 ** yh.to_numpy()
    out = y.index.to_frame(index=False)
    out["n_bins"] = n
    out["int_obs"] = np.where(mask, Y, 0).sum(axis=1) * 10
    out["int_pred"] = np.where(mask, YH, 0).sum(axis=1) * 10
    big = np.where(mask, Y, -np.inf), np.where(mask, YH, -np.inf)
    out["peak_obs"] = MID[np.argmax(big[0], axis=1)]
    out["peak_pred"] = MID[np.argmax(big[1], axis=1)]
    return out


def score(g: pd.DataFrame) -> pd.Series:
    lo, lp = np.log10(g["int_obs"]), np.log10(g["int_pred"])
    e = lp - lo
    sst = ((lo - lo.mean()) ** 2).sum()
    pk = g[g["n_bins"] >= 10]
    d = (pk["peak_pred"] - pk["peak_obs"]).abs()
    return pd.Series({
        "n": len(g), "n_units": g["pixel"].nunique(),
        "int_r2": 1 - (e ** 2).sum() / sst if sst > 0 else np.nan,
        "int_rmse": np.sqrt((e ** 2).mean()), "int_bias": e.mean(),
        "peak_n": len(pk), "peak_mae_m": d.mean() if len(pk) else np.nan,
        "peak_within20": (d <= 20).mean() if len(pk) else np.nan,
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    args = ap.parse_args()
    rows = []
    for f in sorted((args.run / "preds").glob("*.parquet")):
        pr = profiles(pd.read_parquet(f))
        evals = [("all", pr)]
        if pr["dataset"].iat[0] == "both":
            evals += [(k, pr[pr["platform"] == k]) for k in ("argo", "ooi")]
        for ev, q in evals:
            for sub, s in [("int5", q[q["n_bins"] >= 5]), ("full", q[q["n_bins"] == 20])]:
                if len(s) < 20:
                    continue
                keys = ["dataset", "design", "variant", "repeat"]
                rows.append(s.groupby(keys).apply(score, include_groups=False).reset_index().assign(eval=ev, subset=sub))
    m = pd.concat(rows, ignore_index=True)
    m.to_csv(args.run / "profile_metrics.csv", index=False)
    print(f"{len(m)} rows -> {args.run / 'profile_metrics.csv'}")


if __name__ == "__main__":
    main()
