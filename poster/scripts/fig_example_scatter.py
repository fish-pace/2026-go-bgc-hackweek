"""PLACEHOLDER figure: synthetic predicted vs. observed chlorophyll by depth bin.

Shows how a figure script feeds the poster. Replace with a real figure.
Writes figures/fig_example_scatter.png, sized to one poster column.

Run from anywhere: python poster/scripts/fig_example_scatter.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from poster_style import COLUMN_WIDTH_IN, DPI, apply_style

OUT = Path(__file__).resolve().parent.parent / "figures" / "fig_example_scatter.png"


def main():
    apply_style()
    rng = np.random.default_rng(1)
    n = 600
    depth = rng.uniform(0, 200, n)
    observed = 10 ** rng.normal(-0.8, 0.5, n)
    predicted = observed * 10 ** rng.normal(0, 0.12 + depth / 1000, n)

    fig, ax = plt.subplots(figsize=(COLUMN_WIDTH_IN, 8))
    sc = ax.scatter(observed, predicted, c=depth, cmap="viridis_r", s=60, alpha=0.8)
    lims = [0.005, 10]
    ax.plot(lims, lims, "k--", lw=2)
    ax.set(xscale="log", yscale="log", xlim=lims, ylim=lims)
    ax.set_xlabel("Observed CHLA (mg m$^{-3}$)")
    ax.set_ylabel("Predicted CHLA (mg m$^{-3}$)")
    fig.colorbar(sc, ax=ax, label="Depth (m)")
    ax.set_title("PLACEHOLDER: synthetic data", color="firebrick")

    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, dpi=DPI)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
