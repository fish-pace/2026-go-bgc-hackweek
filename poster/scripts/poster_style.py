"""Shared sizes and matplotlib style for poster figures.

Figures are drawn at the size they are printed, so fonts given in points here
are the sizes a visitor sees on the poster. Poster body text is 32 pt.
"""

import matplotlib.pyplot as plt

# One column of a 42 in poster with 3 columns, less the block padding.
# Keep in sync with poster/_extensions/poster/typst-template.typ.
COLUMN_WIDTH_IN = 11.8
DPI = 300


def apply_style():
    plt.rcParams.update(
        {
            "font.size": 26,
            "axes.titlesize": 28,
            "axes.labelsize": 26,
            "xtick.labelsize": 22,
            "ytick.labelsize": 22,
            "legend.fontsize": 22,
            "axes.linewidth": 1.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.constrained_layout.use": True,
        }
    )
