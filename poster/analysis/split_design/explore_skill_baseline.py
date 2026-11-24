"""Exploratory: absolute error against a naive baseline, by depth and water depth.

Eli (2026-11-24): when Chl a is tiny, getting close to tiny is good. 0.002 vs
0.004 mg m^-3 is a meaningless miss; 0.02 vs 0.2 is not. R² cannot show that
(it compares with the local variability), so compare absolute errors with a
baseline that knows nothing about the satellite:

  baseline  one average profile: for each held-out fold and depth bin, the
            geometric mean (mean of log10) of Chl a over that fold's training
            rows, i.e. every row not in the fold, same dataset.
  model     the BRT prediction for the same rows.

Rows (columns = open ocean, slope, shelf by ETOPO 2022 depth):
  1  MAE (mg m^-3), model and baseline
  2  skill vs baseline = 1 - MAE_model / MAE_baseline (0 = no better than
     the average profile, 1 = perfect)
  3  mean observed Chl a (mg m^-3)

Argo and OOI scored separately (one model trained on both). A point needs
>= --min-n rows (100) and >= --min-frac (10%) of the largest bin's row count in
its line (platform x water-depth class). Added 2026-11-24 (Eli) to
drop thin bins whose site mix jumps from the neighbours: on the shelf most
bins have ~4,000 rows (mostly Pioneer), but 10-20 m has 332 (Endurance shelf
profilers in summer upwelling plus Argo, no Pioneer) and 80-110 m ~330 or
fewer. The median (instead of the largest bin) let those through, because
the many near-empty deep shelf bins pull it down to ~330. A first rule (no site > 75% of rows) backfired: Pioneer dominates
nearly every shelf bin, so it removed the shelf and kept the 10-20 m spike.
Caveat, noted for the paper: this can also drop real blooms that few sites
sampled; bloom prediction gets its own test later. Predictions are back-transformed as
10**yhat (median-type; no retransformation-bias correction).
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
COLORS = {"argo": "#1f6fd1", "ooi": "#e4572e", "argo+ooi": "0.2"}
CLASS_COLORS = {"open ocean": "#1f6fd1", "slope": "#e4572e", "shelf": "#2a9d6f"}


def score(p: pd.DataFrame, min_n: int = 100, min_frac: float = 0.1) -> pd.DataFrame:
    # Baseline per (repeat, fold, bin): mean log10 Chl a of the rows NOT in that fold.
    s = p.groupby(["repeat", "bin", "fold"])["y"].agg(["sum", "count"])
    tot = s.groupby(["repeat", "bin"]).transform("sum")
    base = ((tot["sum"] - s["sum"]) / (tot["count"] - s["count"])).rename("ybase")
    p = p.join(base, on=["repeat", "bin", "fold"])
    y, yh, yb = 10 ** p["y"], 10 ** p["yhat"], 10 ** p["ybase"]
    p = p.assign(ae_model=(yh - y).abs(), ae_base=(yb - y).abs(), obs=y)
    rows = []
    for (pl, dc, b, r), g in p.groupby(["platform", "depth_class", "bin", "repeat"]):
        yl, yhl = g["y"], g["yhat"]
        yv, yhv = 10 ** yl, 10 ** yhl
        rows.append(dict(platform=pl, depth_class=dc, z=int(b.split("_")[1]) + 5, repeat=r, n=len(g),
                         mae_model=g["ae_model"].mean(), mae_base=g["ae_base"].mean(), mean_obs=g["obs"].mean(),
                         r2_log=1 - ((yhl - yl) ** 2).sum() / ((yl - yl.mean()) ** 2).sum(),
                         r2_lin=1 - ((yhv - yv) ** 2).sum() / ((yv - yv.mean()) ** 2).sum()))
    m = pd.DataFrame(rows).groupby(["platform", "depth_class", "z"]).mean(numeric_only=True).reset_index()
    typical = m.groupby(["platform", "depth_class"])["n"].transform("max")
    m = m[(m["n"] >= min_n) & (m["n"] >= min_frac * typical)]
    m["skill"] = 1 - m["mae_model"] / m["mae_base"]
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, default=SHARED / "split-design" / "runs" / "window-weights")
    ap.add_argument("--pattern", default="both__*__1deg_30d__r*.parquet")
    ap.add_argument("--design", default="all", help="design value to keep (window-weights: all/weighted/oneday)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--min-n", type=int, default=100)
    ap.add_argument("--min-frac", type=float, default=0.1)
    args = ap.parse_args()

    wd = pd.read_parquet(DEPTH, columns=["profile_id", "depth_class"])
    cols = ["design", "repeat", "fold", "bin", "y", "yhat", "platform", "instrument", "profile_id"]
    p = pd.concat(pd.read_parquet(f, columns=cols) for f in sorted((args.run / "preds").glob(args.pattern)))
    if args.design:
        p = p[p["design"] == args.design]
    p = p.merge(wd, on="profile_id")
    # Pooled line too (Eli: can Argo and OOI be shown together?). The baseline is
    # computed within each scored group, so pooled uses the pooled training mean.
    m = score(pd.concat([p, p.assign(platform="argo+ooi")], ignore_index=True), args.min_n, args.min_frac)
    (args.out or args.run / "figs" / "x").parent.mkdir(parents=True, exist_ok=True)
    m.to_csv((args.out or args.run / "figs" / "x").with_name(f"skill_baseline_{args.design}.csv"), index=False)

    fig, ax = plt.subplots(3, 3, figsize=(12, 13), sharey=True)
    for j, dc in enumerate(CLASSES):
        for pl in ["argo", "ooi", "argo+ooi"]:
            d = m[(m.platform == pl) & (m.depth_class == dc)].sort_values("z")
            if not len(d):
                continue
            lab = {"argo": "Argo", "ooi": "OOI", "argo+ooi": "Argo + OOI"}[pl]
            ax[0, j].plot(d["mae_model"], d["z"], "o-", ms=3, color=COLORS[pl], label=f"{lab} model")
            ax[0, j].plot(d["mae_base"], d["z"], "--", color=COLORS[pl], label=f"{lab} average profile")
            ax[1, j].plot(d["skill"], d["z"], "o-", ms=3, color=COLORS[pl], label=lab)
            ax[2, j].plot(d["mean_obs"], d["z"], "o-", ms=3, color=COLORS[pl], label=lab)
        ax[0, j].set_title(dc)
        ax[0, j].set_xlabel("MAE (mg m$^{-3}$)")
        ax[1, j].set_xlabel("Skill vs average profile")
        ax[1, j].axvline(0, color="0.6", lw=0.8)
        ax[1, j].set_xlim(-0.5, 1)
        ax[2, j].set_xlabel("Mean observed Chl a (mg m$^{-3}$)")
        for i in range(3):
            ax[i, j].grid(alpha=0.3)
            if i != 1:
                ax[i, j].set_xlim(left=0)
    for i in range(3):
        ax[i, 0].set_ylabel("Depth (m)")
    ax[0, 0].invert_yaxis()
    ax[0, 0].legend(fontsize=8)
    ax[1, 0].legend(fontsize=8)
    fig.suptitle(f"{args.run.name}, design={args.design}: Argo + OOI model, space-time split; "
                 "model vs one average profile", fontsize=11)
    fig.tight_layout()
    out = args.out or args.run / "figs" / f"skill_baseline_{args.design}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=90)
    print(out)
    print(m[m.z.isin([5, 25, 55, 105, 155])].round(3).to_string(index=False))

    # Candidate Figure 3: pooled Argo + OOI, one line per water-depth class.
    q = m[m.platform == "argo+ooi"]
    # Eli (2026-11-24): % error reduction alone can hide "improved on horrible but
    # still horrible", so the left panel shows the error itself next to how much
    # Chl a there is (same units, one axis).
    fig, ax = plt.subplots(1, 2, figsize=(11.8, 5.5), sharey=True)
    for dc in CLASSES:
        d = q[q.depth_class == dc].sort_values("z")
        c = CLASS_COLORS[dc]
        ax[0].plot(d["mean_obs"], d["z"], ":", lw=2, color=c, label=f"{dc}: mean Chl $a$")
        ax[0].plot(d["mae_model"], d["z"], "o-", ms=4, color=c, label=f"{dc}: error (MAE)")
        ax[1].plot(100 * d["skill"], d["z"], "o-", ms=4, color=c, label=dc)
    ax[0].set_xlabel("Chl $a$ (mg m$^{-3}$)")
    ax[0].set_xlim(left=0)
    ax[1].axvline(0, color="0.5", lw=0.8)
    ax[1].set_xlabel("Error reduction vs. average profile (%)")
    ax[1].set_xlim(-25, 75)
    ax[0].set_ylabel("Depth (m)")
    ax[0].invert_yaxis()
    ax[0].legend(fontsize=8)
    ax[1].legend(fontsize=8)
    for a in ax:
        a.grid(alpha=0.3)
    fig.tight_layout()
    out2 = (args.out or args.run / "figs" / "x").with_name(f"fig3_candidate_{args.design}.png")
    fig.savefig(out2, dpi=90)
    print(out2)

    # Candidate Figure 3, v2 (Eli, 2026-11-24): 2 x 3, columns = open ocean, slope,
    # shelf; top = MAE with Rrs and mean observed Chl a (mg m^-3); bottom = R², on
    # log10 or on linear Chl a (one file each, to choose). Pooled Argo + OOI.
    for r2col, r2lab in [("r2_log", "R² (log$_{10}$ Chl $a$)"), ("r2_lin", "R² (Chl $a$, mg m$^{-3}$)")]:
        fig, ax = plt.subplots(2, 3, figsize=(11.8, 9), sharey=True)
        for j, dc in enumerate(CLASSES):
            d = q[q.depth_class == dc].sort_values("z")
            c = CLASS_COLORS[dc]
            ax[0, j].plot(d["mean_obs"], d["z"], ":", lw=2.5, color="0.45", label="mean observed")
            ax[0, j].plot(d["mae_model"], d["z"], "o-", ms=4, color=c, label="mean absolute error")
            ax[0, j].set_xlim(left=0)
            ax[0, j].set_xlabel("Chl $a$ (mg m$^{-3}$)")
            ax[0, j].set_title(dc)
            ax[1, j].plot(d[r2col], d["z"], "o-", ms=4, color=c)
            ax[1, j].axvline(0, color="0.5", lw=0.8)
            ax[1, j].set_xlim(-0.5, 1)
            ax[1, j].set_xlabel(r2lab)
            for i in range(2):
                ax[i, j].grid(alpha=0.3)
        for i in range(2):
            ax[i, 0].set_ylabel("Depth (m)")
        ax[0, 0].invert_yaxis()
        ax[0, 0].legend(fontsize=8)
        fig.tight_layout()
        out3 = (args.out or args.run / "figs" / "x").with_name(f"fig3_v2_{r2col}_{args.design}.png")
        fig.savefig(out3, dpi=90)
        print(out3)


if __name__ == "__main__":
    main()
