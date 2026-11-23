"""Block 2 figure: skill by water depth class (issue #11).

Left: R² of log10 CHLA in each 10 m bin, for profiles in open ocean
(> 1000 m), slope (200-1000 m) and shelf (< 200 m) water (ETOPO 2022 depth at
the profile, poster/analysis/bathymetry). Right: observed vs predicted
integrated CHLA (sum over the contiguous bins from the surface, at least 5).

Predictions are out-of-fold from the leakage-free evaluation (#20): Argo+OOI
model, space-time block split (1° cell x 30 d), mean over 5 repeats with the
min-max range shaded. A bin is drawn only when it has at least MIN_UNITS
independent units (Argo floats or OOI sites) and MIN_ROWS rows in that class,
so a handful of instruments cannot make a point.
"""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from poster_style import COLUMN_WIDTH_IN, DPI, apply_style

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis" / "split_design"))
import profile_metrics as pm  # noqa: E402

SHARED = Path.home() / "shared-public" / "chla-z"
PREDS = sorted((SHARED / "split-design" / "runs" / "full" / "preds").glob("both__spacetime__1deg_30d__r*.parquet"))
DEPTH = SHARED / "bathymetry" / "water_depth_2026_11_23.parquet"
OUT = Path(__file__).resolve().parents[1] / "figures" / "fig_coastal_skill.png"
CLASSES = [("open ocean", "Open ocean > 1000 m", "#2a78d6"),
           ("slope", "Slope 200–1000 m", "#eb6834"),
           ("shelf", "Shelf < 200 m", "#1baf7a")]
MIN_UNITS, MIN_ROWS = 3, 100


def r2(g):
    e = g["yhat"] - g["y"]
    return 1 - (e ** 2).sum() / ((g["y"] - g["y"].mean()) ** 2).sum()


def main():
    apply_style()
    wd = pd.read_parquet(DEPTH, columns=["profile_id", "depth_class"])
    per_bin, integ = [], []
    for f in PREDS:
        p = pd.read_parquet(f).merge(wd, on="profile_id")
        p["z"] = p["bin"].str.split("_").str[1].astype(int) + 5
        g = p.groupby(["depth_class", "z"])
        s = g.apply(r2, include_groups=False).rename("r2").to_frame()
        s["units"], s["rows"] = g["pixel"].nunique(), g.size()
        per_bin.append(s.reset_index().assign(rep=f.stem))
        pr = pm.profiles(p.drop(columns=["z", "depth_class"])).merge(wd, on="profile_id")
        integ.append(pr[pr["n_bins"] >= 5].assign(rep=f.stem))
    b = pd.concat(per_bin)
    b = b[(b["units"] >= MIN_UNITS) & (b["rows"] >= MIN_ROWS)]
    b = b.groupby(["depth_class", "z"])["r2"].agg(["mean", "min", "max"]).reset_index()
    ii = pd.concat(integ)
    ii = ii[ii["rep"] == ii["rep"].min()]

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(COLUMN_WIDTH_IN, 5.5), width_ratios=[1.35, 1])
    for key, lab, c in CLASSES:
        d = b[b["depth_class"] == key]
        ax.fill_betweenx(d["z"], d["min"], d["max"], color=c, alpha=0.2, lw=0)
        ax.plot(d["mean"], d["z"], color=c, lw=3, marker="o", ms=6, label=lab)
        q = ii[ii["depth_class"] == key]
        bx.scatter(q["int_obs"], q["int_pred"], s=10 if key == "open ocean" else 22, color=c, alpha=0.35 if key == "open ocean" else 0.8,
                   lw=0, label=f"{lab} (n={len(q)})")
    ax.axvline(0, color="0.4", lw=1)
    ax.set_xlim(-0.7, 1)
    ax.invert_yaxis()
    ax.set_xlabel("R² (log10 Chl $a$)")
    ax.set_ylabel("Depth (m)")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left", frameon=False, fontsize=16, borderaxespad=0.2, handlelength=1.2)
    lims = [ii[["int_obs", "int_pred"]].min().min() * 0.8, ii[["int_obs", "int_pred"]].max().max() * 1.2]
    bx.plot(lims, lims, color="0.3", lw=1, ls="--")
    bx.set(xscale="log", yscale="log", xlim=lims, ylim=lims)
    bx.set_xlabel("Observed (mg m$^{-2}$)")
    bx.set_ylabel("Predicted (mg m$^{-2}$)")
    bx.set_title("Integrated Chl $a$", fontsize=22)
    bx.grid(alpha=0.3)
    fig.savefig(OUT, dpi=DPI)
    print(b.pivot(index="z", columns="depth_class", values="mean").round(2).to_string())
    print(ii.groupby("depth_class").apply(lambda q: pd.Series({
        "n": len(q), "units": q["pixel"].nunique(),
        "r2_log": 1 - ((np.log10(q.int_pred) - np.log10(q.int_obs)) ** 2).sum()
        / ((np.log10(q.int_obs) - np.log10(q.int_obs).mean()) ** 2).sum()}), include_groups=False).round(2))


if __name__ == "__main__":
    main()
