"""Introduction figure: observed vs predicted CHLA profiles (issue #13).

Shows the known result the poster builds on: Rrs predicts the open-ocean
profile, including a deep chlorophyll maximum. Predictions are out-of-fold
from the leakage-free evaluation (#20): Argo+OOI model, space-time block
split (1° cell x 30 d), repeat 0, so each profile was predicted by a model
that saw nothing from its cell within that 30-day block.

Profiles are drawn at random (fixed seed) within each panel's category, not
picked for a good fit. Categories by observed peak depth and water depth
(ETOPO 2022, poster/analysis/bathymetry). Inputs live in ~/shared-public.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from poster_style import COLUMN_WIDTH_IN, DPI, apply_style

SHARED = Path.home() / "shared-public" / "chla-z"
PREDS = SHARED / "split-design" / "runs" / "full" / "preds" / "both__spacetime__1deg_30d__r0.parquet"
DEPTH = SHARED / "bathymetry" / "water_depth_2026_11_23.parquet"
OUT = Path(__file__).resolve().parents[1] / "figures" / "fig_example_profiles.png"
SEED = 7

OBS, PRED = "#1f1f1f", "#2a78d6"


def load():
    p = pd.read_parquet(PREDS)
    p["top"] = p["bin"].str.split("_").str[1].astype(int)
    p["z"] = p["top"] + 5
    wd = pd.read_parquet(DEPTH, columns=["profile_id", "depth_class", "lat", "lon"])
    p = p.merge(wd, on="profile_id", how="left")
    full = p.groupby("profile_id")["top"].nunique()
    p = p[p["profile_id"].isin(full[full == 20].index)]
    peak = p.loc[p.groupby("profile_id")["y"].idxmax(), ["profile_id", "z"]].set_index("profile_id")["z"]
    p["peak"] = p["profile_id"].map(peak)
    return p


def main():
    apply_style()
    p = load()
    a = p[(p["platform"] == "argo") & (p["depth_class"] == "open ocean")]
    rng = np.random.default_rng(SEED)
    cats = [
        ("Surface peak", a[a["peak"] <= 15]),
        ("Peak 40–70 m", a[a["peak"].between(40, 70)]),
        ("Peak > 100 m", a[a["peak"] > 100]),
        ("Peak > 100 m", a[a["peak"] > 100]),
    ]
    picked = []
    for title, s in cats:
        ids = [i for i in s["profile_id"].unique() if i not in picked]
        picked.append(rng.choice(ids))
    fig, axs = plt.subplots(1, len(cats), figsize=(COLUMN_WIDTH_IN, 5.0), sharey=True)
    for ax, (title, _), pid in zip(axs, cats, picked):
        g = p[p["profile_id"] == pid].sort_values("z")
        ax.plot(10 ** g["y"], g["z"], color=OBS, lw=3, label="Observed")
        ax.plot(10 ** g["yhat"], g["z"], color=PRED, lw=3, ls="--", label="Predicted")
        ax.set_xlim(left=0)
        ax.xaxis.set_major_locator(plt.MaxNLocator(3))
        lat, lon = g["lat"].iat[0], g["lon"].iat[0]
        ax.set_title(f"{title}\n{abs(lat):.0f}°{'N' if lat >= 0 else 'S'} {abs(lon):.0f}°{'E' if lon >= 0 else 'W'}",
                     fontsize=19)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=18)
    axs[0].invert_yaxis()
    axs[0].set_ylabel("Depth (m)")
    fig.supxlabel("CHLA (mg m$^{-3}$)", fontsize=22)
    axs[0].legend(loc="lower right", frameon=False, fontsize=18)
    fig.savefig(OUT, dpi=DPI)
    print("profiles:", list(picked))


if __name__ == "__main__":
    main()
