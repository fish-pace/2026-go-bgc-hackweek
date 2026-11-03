"""PLACEHOLDER figure: synthetic observed vs. predicted chlorophyll profiles.

Shows how a figure script feeds the poster. Replace with a real figure.
Writes figures/fig_example_profiles.png, sized to one poster column.

Run from anywhere: python poster/scripts/fig_example_profiles.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from poster_style import COLUMN_WIDTH_IN, DPI, apply_style

OUT = Path(__file__).resolve().parent.parent / "figures" / "fig_example_profiles.png"


def profile(depth, surface, peak, peak_depth, width):
    """Surface background that decays with depth plus a Gaussian deep maximum."""
    background = surface * np.exp(-depth / 60)
    dcm = peak * np.exp(-((depth - peak_depth) ** 2) / (2 * width**2))
    return background + dcm


def main():
    apply_style()
    rng = np.random.default_rng(42)
    depth = np.arange(0, 201, 10)
    cases = [
        ("Open ocean", dict(surface=0.05, peak=0.45, peak_depth=110, width=20)),
        ("Shelf break", dict(surface=0.3, peak=0.8, peak_depth=50, width=15)),
        ("Coastal", dict(surface=1.5, peak=0.4, peak_depth=20, width=10)),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(COLUMN_WIDTH_IN, 6.5), sharey=True)
    for ax, (name, params) in zip(axes, cases):
        truth = profile(depth, **params)
        observed = truth * rng.lognormal(0, 0.15, depth.size)
        predicted = profile(depth, **{k: v * rng.uniform(0.85, 1.15) for k, v in params.items()})
        ax.plot(observed, depth, "o", color="0.35", label="Observed")
        ax.plot(predicted, depth, "-", lw=4, color="#2a9d8f", label="Predicted")
        ax.set_title(name)
        ax.set_xlabel("CHLA (mg m$^{-3}$)")
    axes[0].set_ylabel("Depth (m)")
    axes[0].invert_yaxis()
    axes[0].legend(loc="lower right", frameon=False)
    fig.suptitle("PLACEHOLDER: synthetic data", color="firebrick")

    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, dpi=DPI)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
