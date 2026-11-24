"""Data block (#9): where the training profiles are, by platform and water depth.

Reads the water-depth table made by poster/analysis/bathymetry/water_depth.py
(and the inset grids from inset_grids.py there) instead of recomputing it, so
this runs in seconds under `make`.

Colour is the water-depth class, marker is the platform. Argo profiles are
small dots; OOI has only a handful of sites, so its instruments are large
outlined diamonds. Eli (2026-11-24): the two coastal insets (Endurance &
Cabled, Pioneer) were dropped as clutter; the legend takes their place on the
right. INSETS and inset_grids.py are kept in case the insets come back.

Poster v2 (#22): glider profiles as small outlined triangles; a glider moves,
so each profile is drawn and the deployments show as short tracks.
"""

from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from poster_style import COLUMN_WIDTH_IN, DPI, apply_style

# v2 (#22): the table with glider rows (run.DATA_TAG_V2); v1 was "2026_11_23".
DATA_RELEASE = "2026_11_23_glider-prerelease"
BATHY = Path.home() / "shared-public" / "chla-z" / "bathymetry"
TABLE = BATHY / f"water_depth_{DATA_RELEASE}.parquet"
OUT = Path(__file__).resolve().parents[1] / "figures" / "fig_data_map.png"
HEIGHT_IN = 3.6

# Categorical slots 1-3 of the dataviz reference palette, in fixed order; the
# first three are the ones that validate for all pairs (scatter/map use).
CLASSES = {
    "open ocean": ("#2a78d6", "Open ocean\n> 1000 m"),
    "slope": ("#eb6834", "Slope\n200–1000 m"),
    "shelf": ("#1baf7a", "Shelf\n< 200 m"),
}
LAND = "#e4e3df"
INK = "#0b0b0b"
INK_2 = "#52514e"

# (title, lon0, lon1, lat0, lat1); boxes lie inside inset_grids.BOXES.
INSETS = {
    "endurance": ("Endurance & Cabled", -130.6, -123.6, 43.9, 47.6),
    "pioneer": ("Pioneer", -75.4, -74.35, 35.6, 36.3),
}
ARRAY_LABELS = [  # (text, array lon, lat, label lon, lat) on the world map
    ("Irminger", -39.6, 59.9, -20, 70),
    ("Papa", -144.5, 50.1, -160, 66),
    ("Endurance", -125.0, 45.0, -148, 28),
    ("Pioneer", -74.9, 36.0, -55, 20),
]


def scatter_argo(ax, a, size):
    # Rare classes drawn last, and larger, so the thousands of open-ocean dots
    # don't hide the few shelf and slope profiles.
    for cls in reversed(list(CLASSES)):
        s = a[a["depth_class"] == cls]
        ax.scatter(s["lon"], s["lat"], s=size * (1 if cls == "open ocean" else 3), c=CLASSES[cls][0], lw=0,
                   transform=ccrs.PlateCarree(), zorder=3)


def scatter_ooi(ax, o, size):
    for cls in reversed(list(CLASSES)):
        s = o[o["depth_class"] == cls]
        ax.scatter(s["lon"], s["lat"], s=size, c=CLASSES[cls][0], marker="D",
                   edgecolors=INK, lw=1.2, transform=ccrs.PlateCarree(), zorder=5)


def scatter_glider(ax, g, size):
    for cls in reversed(list(CLASSES)):
        s = g[g["depth_class"] == cls]
        ax.scatter(s["lon"], s["lat"], s=size, c=CLASSES[cls][0], marker="^",
                   edgecolors=INK, lw=0.6, transform=ccrs.PlateCarree(), zorder=4)


def main():
    apply_style()
    t = pd.read_parquet(TABLE)
    a = t[t["platform"] == "argo"]
    # One marker per OOI instrument position; co-located instruments overlap.
    o = t[t["platform"] == "ooi"].drop_duplicates("instrument")
    g = t[t["platform"] == "glider"]

    fig = plt.figure(figsize=(COLUMN_WIDTH_IN, HEIGHT_IN), layout="none")
    proj = ccrs.PlateCarree()
    # World map on the left, legend on the right.
    ax = fig.add_axes([0.0, 0.0, 0.72, 1.0], projection=proj)
    ax.set_extent([-180, 180, -80, 82], crs=proj)
    ax.add_feature(cfeature.LAND.with_scale("110m"), facecolor=LAND, edgecolor="none", zorder=1)
    ax.coastlines("110m", lw=0.5, color=INK_2, zorder=2)
    ax.spines["geo"].set_edgecolor(INK_2)
    scatter_argo(ax, a, 3)
    scatter_glider(ax, g, 22)
    scatter_ooi(ax, o, 70)
    for text, lon, lat, tlon, tlat in ARRAY_LABELS:
        ax.annotate(text, (lon, lat), (tlon, tlat), xycoords=proj._as_mpl_transform(ax),
                    textcoords=proj._as_mpl_transform(ax), ha="center", va="center",
                    fontsize=20, color=INK, zorder=6,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85),
                    arrowprops=dict(arrowstyle="-", color=INK, lw=1.0, shrinkB=6))

    cls_h = [Line2D([], [], ls="none", marker="s", ms=14, mfc=c, mec="none", label=lab)
             for c, lab in CLASSES.values()]
    plat_h = [
        Line2D([], [], ls="none", marker="o", ms=6, mfc=INK_2, mec="none",
               label="Argo profile"),
        Line2D([], [], ls="none", marker="D", ms=11, mfc="white", mec=INK, mew=1.2,
               label="OOI instrument"),
        Line2D([], [], ls="none", marker="^", ms=8, mfc="white", mec=INK, mew=0.8,
               label="Glider profile"),
    ]
    fig.legend(handles=plat_h + cls_h, loc="center left", bbox_to_anchor=(0.73, 0.5), ncol=1,
               frameon=False, fontsize=19, handletextpad=0.3, borderaxespad=0.1, labelspacing=0.35)
    fig.savefig(OUT, dpi=DPI, facecolor="white")
    plt.close(fig)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
