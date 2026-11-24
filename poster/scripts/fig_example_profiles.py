"""Introduction figure: observed vs predicted CHLA profiles (issue #13).

Eli, 2026-11-24 (poster v2, #22): four panels by water depth, to show what
profiles look like and that the model captures their shape: open ocean, open
ocean with a deep maximum (> 100 m), slope (200-1000 m) and shelf (< 200 m).
v1 showed four open-ocean Argo profiles.

Predictions are out-of-fold from the v2 model used in block 2 (Argo + OOI +
glider, every row predicted as Argo plus a per-depth platform offset;
run_platform.py design "argo_bias", runs/platform-glider), space-time block
split (1° cell x 30 d), repeat 0: each profile was predicted by a model that
saw nothing from its cell within that 30-day block.

Selection (Eli: "middle half of class"): for each panel, the eligible
profiles are ranked by their RMSE of log10 Chl a over the observed bins, and
one is drawn at random (fixed seed) from the 25th-75th percentile. So the
panels are typical of their class, neither the best fits nor the worst.
Eligible: contiguous 10 m bins from the surface; open ocean all 20 bins
(Argo); slope at least 10 bins and shelf at least 5 (shelf water is shallow),
any platform. Water-depth class from ETOPO 2022 (poster/analysis/bathymetry);
the grey band is the seafloor where it is above 200 m. The script prints each
pick and its percentile. Inputs live in ~/shared-public.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from poster_style import COLUMN_WIDTH_IN, DPI, apply_style

SHARED = Path.home() / "shared-public" / "chla-z"
PREDS = SHARED / "split-design" / "runs" / "platform-glider" / "preds" / "both__argo_bias__1deg_30d__r0.parquet"
DEPTH = SHARED / "bathymetry" / "water_depth_2026_11_24.parquet"
OUT = Path(__file__).resolve().parents[1] / "figures" / "fig_example_profiles.png"
SEED = 7
LABEL = {"argo": "Argo", "ooi": "OOI", "glider": "Glider"}

OBS, PRED, SEAFLOOR = "#1f1f1f", "#2a78d6", "#c9c7c1"


def load():
    p = pd.read_parquet(PREDS)
    p["top"] = p["bin"].str.split("_").str[1].astype(int)
    p["z"] = p["top"] + 5
    wd = pd.read_parquet(DEPTH, columns=["profile_id", "depth_class", "water_depth_m"])
    p = p.merge(wd, on="profile_id", how="left")
    g = p.groupby("profile_id").agg(
        first=("top", "min"), last=("top", "max"), n=("top", "nunique"),
        rmse=("y", lambda s: np.sqrt(((p.loc[s.index, "yhat"] - s) ** 2).mean())))
    g = g[(g["first"] == 0) & (g["n"] == g["last"] // 10 + 1)]
    peak = p.loc[p.groupby("profile_id")["y"].idxmax(), ["profile_id", "z"]].set_index("profile_id")["z"]
    g["peak"] = peak
    meta = p.drop_duplicates("profile_id").set_index("profile_id")[["platform", "depth_class", "water_depth_m"]]
    return p, g.join(meta)


def main():
    apply_style()
    p, g = load()
    open_ = g[(g["depth_class"] == "open ocean") & (g["platform"] == "argo") & (g["n"] == 20)]
    panels = [
        ("Open ocean", open_[open_["peak"] <= 70]),
        ("Open ocean", open_[open_["peak"] > 100]),
        ("Slope", g[(g["depth_class"] == "slope") & (g["n"] >= 10)]),
        ("Shelf", g[(g["depth_class"] == "shelf") & (g["n"] >= 5)]),
    ]
    rng = np.random.default_rng(SEED)
    picked = []
    for title, pool in panels:
        lo, hi = pool["rmse"].quantile([0.25, 0.75])
        mid = pool[pool["rmse"].between(lo, hi)]
        pid = rng.choice(sorted(mid.index))
        pct = 100 * (pool["rmse"] < pool.loc[pid, "rmse"]).mean()
        print(f"{title:10s} {pid}  RMSE {pool.loc[pid, 'rmse']:.2f}  percentile {pct:.0f} of {len(pool)}")
        picked.append(pid)

    fig, axs = plt.subplots(1, len(panels), figsize=(COLUMN_WIDTH_IN, 5.0), sharey=True)
    for ax, (title, _), pid in zip(axs, panels, picked):
        d = p[p["profile_id"] == pid].sort_values("z")
        ax.plot(10 ** d["y"], d["z"], color=OBS, lw=3, label="Observed")
        ax.plot(10 ** d["yhat"], d["z"], color=PRED, lw=3, ls="--", label="Predicted")
        bottom = g.loc[pid, "water_depth_m"]
        if bottom < 200:
            ax.axhspan(bottom, 200, color=SEAFLOOR, zorder=0)
        ax.set_xlim(left=0)
        ax.xaxis.set_major_locator(plt.MaxNLocator(3))
        ax.set_title(f"{title}\n{LABEL[g.loc[pid, 'platform']]}, {bottom:,.0f} m", fontsize=19)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=18)
    axs[0].set_ylim(0, 200)
    axs[0].invert_yaxis()
    axs[0].set_ylabel("Depth (m)")
    fig.supxlabel("Chl $a$ (mg m$^{-3}$)", fontsize=22)
    axs[0].legend(loc="lower right", frameon=False, fontsize=18)
    fig.savefig(OUT, dpi=DPI)


if __name__ == "__main__":
    main()
