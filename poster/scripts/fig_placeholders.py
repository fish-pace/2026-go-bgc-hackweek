"""Grey placeholder figures at the size each block budgets for.

They hold each block's space while its real figure is made, so the layout can
be checked now. Delete a block's placeholder (here and in figures/) when its
real figure script exists. Sizes are the budget in poster/blocks/README.md.
"""

from pathlib import Path

import matplotlib.pyplot as plt

from poster_style import COLUMN_WIDTH_IN, DPI, apply_style

FIGS = Path(__file__).resolve().parents[1] / "figures"
PLACEHOLDERS = {
    "map": (4.5, "Data: map of profiles by platform and water depth (#9)"),
    "leakage": (6.5, "Leakage: skill by depth under each split design (#20)"),
    "hyperspectral": (6.0, "1. PACE-172 vs PACE-11 vs OLCI-11, skill by depth (#10)"),
    "coastal": (5.5, "2. Coastal vs open ocean skill (#11)"),
}


def main():
    apply_style()
    for name, (h, label) in PLACEHOLDERS.items():
        fig = plt.figure(figsize=(COLUMN_WIDTH_IN, h))
        fig.patch.set_facecolor("#e6e6e6")
        fig.text(0.5, 0.5, f"{label}\n{COLUMN_WIDTH_IN:g} × {h:g} in", ha="center", va="center",
                 fontsize=26, color="#555555")
        fig.savefig(FIGS / f"placeholder_{name}.png", dpi=DPI, facecolor=fig.get_facecolor())
        plt.close(fig)


if __name__ == "__main__":
    main()
