"""Skill by depth bin from the saved split-design predictions (run.py).

For each (dataset, design, variant, repeat, bin) the out-of-fold predictions
of all folds are pooled and scored on log10 CHLA: R², RMSE, bias, and the
number of rows and of independent units (Argo floats, OOI sites).

`eval` says which rows were scored: `all`, or, for the model trained on
Argo+OOI ("both"), `argo` / `ooi` only. The "both" model scored on all rows is
dominated by OOI rows; the per-platform rows show what each platform gets.

Writes metrics.csv next to the preds/ folder.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def score(g: pd.DataFrame) -> pd.Series:
    y, p = g["y"].to_numpy(float), g["yhat"].to_numpy(float)
    e = p - y
    sst = ((y - y.mean()) ** 2).sum()
    return pd.Series(
        {
            "n": len(y),
            "n_units": g["pixel"].nunique(),  # Argo float or OOI PACE pixel
            "r2": 1 - (e**2).sum() / sst if sst > 0 else np.nan,
            "rmse": np.sqrt((e**2).mean()),
            "bias": e.mean(),
        }
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path, help="run folder holding preds/")
    args = ap.parse_args()

    rows = []
    for f in sorted((args.run / "preds").glob("*.parquet")):
        p = pd.read_parquet(f)
        keys = ["dataset", "design", "variant", "repeat", "bin"]
        rows.append(p.groupby(keys).apply(score, include_groups=False).reset_index().assign(eval="all"))
        if p["dataset"].iat[0] == "both":
            for plat in ("argo", "ooi"):
                q = p[p["platform"] == plat]
                rows.append(q.groupby(keys).apply(score, include_groups=False).reset_index().assign(eval=plat))
    m = pd.concat(rows, ignore_index=True)
    m["depth_top"] = m["bin"].str.split("_").str[1].astype(int)
    m["depth_mid"] = m["depth_top"] + 5
    m.to_csv(args.run / "metrics.csv", index=False)
    print(f"{len(m)} rows -> {args.run / 'metrics.csv'}")


if __name__ == "__main__":
    main()
