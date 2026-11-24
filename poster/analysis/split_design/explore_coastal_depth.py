"""Exploratory (not a poster figure): is coastal skill at depth low, or is
there just little to explain? And do Argo and OOI tell the same story?

Eli (2026-11-24): R² may be low near coasts because Chl a barely varies at
depth there. Plots, by depth and water-depth class (ETOPO 2022), for Argo and
OOI scored separately:

  row 1  R² of log10 Chl a
  row 2  RMSE of log10 Chl a (0.3 = a factor of 2)
  row 3  SD of observed log10 Chl a (what R² is measured against)

Predictions: an existing run, Argo + OOI model, space-time split (1° x 30 d),
all repeats. Default is runs/full (all OOI windows, unweighted); pass
--run/--design to use the window-weights run once it exists. A point is drawn
only with at least 30 rows and 3 instruments.

--scale linear (Eli, 2026-11-24): the same in mg m^-3, since a log10 RMSE of
0.3 (a factor of 2) means little at 0.002 mg m^-3 and a lot at 2. Rows: RMSE,
SD of observed, mean observed. Predictions are back-transformed with 10**yhat
(a median-type estimate; no retransformation-bias correction).
"""

import argparse
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SHARED = Path.home() / "shared-public" / "chla-z"
DEPTH = SHARED / "bathymetry" / "water_depth_2026_11_23.parquet"
CLASSES = ["open ocean", "slope", "shelf"]
COLORS = {"argo": "#1f6fd1", "ooi": "#e4572e"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, default=SHARED / "split-design" / "runs" / "full")
    ap.add_argument("--pattern", default="both__spacetime__1deg_30d__r*.parquet")
    ap.add_argument("--design", default=None, help="keep only this design value (window-weights run)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--scale", choices=["log", "linear"], default="log")
    args = ap.parse_args()

    wd = pd.read_parquet(DEPTH, columns=["profile_id", "depth_class"])
    rows = []
    for f in sorted((args.run / "preds").glob(args.pattern)):
        p = pd.read_parquet(f, columns=["design", "repeat", "bin", "y", "yhat", "platform", "instrument", "profile_id"])
        if args.design:
            p = p[p["design"] == args.design]
        p = p.merge(wd, on="profile_id")
        for (pl, dc, b, r), g in p.groupby(["platform", "depth_class", "bin", "repeat"]):
            if len(g) < 30 or g["instrument"].nunique() < 3:
                continue
            y, yh = (g["y"], g["yhat"]) if args.scale == "log" else (10 ** g["y"], 10 ** g["yhat"])
            e = yh - y
            rows.append(dict(platform=pl, depth_class=dc, z=int(b.split("_")[1]) + 5, repeat=r, n=len(g),
                             r2=1 - (e ** 2).mean() / y.var(ddof=0), rmse=np.sqrt((e ** 2).mean()),
                             sd=y.std(), mean=y.mean()))
    m = pd.DataFrame(rows).groupby(["platform", "depth_class", "z"])[["n", "r2", "rmse", "sd", "mean"]].mean().reset_index()
    if args.scale == "log":
        panels = [("r2", "R² (log10 Chl a)"), ("rmse", "RMSE (log10 Chl a)"), ("sd", "SD of observed log10 Chl a")]
    else:
        panels = [("rmse", "RMSE (mg m$^{-3}$)"), ("sd", "SD of observed (mg m$^{-3}$)"),
                  ("mean", "Mean observed (mg m$^{-3}$)")]
    xmax = 0.8

    fig, ax = plt.subplots(3, 3, figsize=(12, 13), sharey=True)
    for j, dc in enumerate(CLASSES):
        for i, (col, lab) in enumerate(panels):
            a = ax[i, j]
            for pl in ["argo", "ooi"]:
                d = m[(m.platform == pl) & (m.depth_class == dc)].sort_values("z")
                if len(d):
                    a.plot(d[col], d["z"], "o-", ms=3, color=COLORS[pl], label=f"{pl.upper() if pl == 'ooi' else 'Argo'}")
            if i == 0:
                a.set_title(dc)
            if col == "r2":
                a.axvline(0, color="0.6", lw=0.8)
                a.set_xlim(-1, 1)
            elif args.scale == "log":
                a.set_xlim(0, xmax)
            else:
                a.set_xlim(left=0)  # own scale per panel: shelf values are 5-10x open ocean
            a.set_xlabel(lab)
            a.grid(alpha=0.3)
            if j == 0:
                a.set_ylabel("Depth (m)")
    ax[0, 0].invert_yaxis()
    ax[0, 0].legend()
    fig.suptitle(f"{args.run.name} ({args.scale}): Argo + OOI model, space-time split; Argo and OOI scored separately", fontsize=11)
    fig.tight_layout()
    out = args.out or args.run / "figs" / f"explore_coastal_depth_{args.scale}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=90)
    print(out)
    print(m[m.z.isin([5, 55, 105])].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
