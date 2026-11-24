"""Block 2 figure and table: profile skill in open-ocean, slope and shelf water.

Eli (2026-11-24) replaced the skill-by-depth figure with:

  Table (printed, pasted into blocks/coastal.qmd): the SOCA2024 validation
  metrics (Copernicus QUID 015-010, section IV.2), with all depths pooled as
  SOCA does, broken out by water-depth class. SOCA covers only water deeper
  than 1000 m. r² and slope: linear regression of log10 predicted on log10
  observed; MAPD: median absolute percent difference; RMSD: root mean square
  difference in mg m^-3. Mean over repeats.

  Figure, 1 x 3 (open ocean, slope, shelf), after the CHLA-Z talk
  (fish-pace/chla-z docs/text_and_talks/chla_depth_talk_2.qmd, "Integrated
  CHLA"): integrated Chl a, observed vs predicted (log axes), 1:1 and +/-50%.
  A peak-depth row (the talk's "Observed and Predicted Peak Depth") was tried
  and dropped (Eli, 2026-11-24): on the slope and shelf nearly all peaks are at
  the surface, observed and predicted, so the boxes collapse to zero. Peak-depth
  errors are still printed.
  Profiles as in the talk: at least 10 observed bins; integrated = sum of
  Chl a x 10 m over the observed bins; peak from a 3-bin running mean. One
  repeat (r0) is plotted so each profile appears once; the R² printed in each
  panel is the mean over repeats.

Predictions: out-of-fold, Argo + OOI model, space-time split (1° x 30 d), QC'd
data (OOI exclusion, fish-pace-datasets#13), all OOI windows. RUN and DESIGN
below pick the run (predicted as Argo plus a per-depth OOI offset).
Water-depth class: ETOPO 2022 at the profile.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter1d

from poster_style import COLUMN_WIDTH_IN, DPI, apply_style

SHARED = Path.home() / "shared-public" / "chla-z"
# Eli, 2026-11-24: the model as a map would use it. Trained with the platform input,
# every row predicted as Argo, OOI rows then shifted by a per-bin OOI offset
# (run_platform.py, design "argo_bias").
RUN = SHARED / "split-design" / "runs" / "platform"
DESIGN = "argo_bias"
DEPTH = SHARED / "bathymetry" / "water_depth_2026_11_23.parquet"
OUT = Path(__file__).resolve().parents[1] / "figures" / "fig_profiles_by_class.png"
CLASSES = [("open ocean", "Open ocean > 1000 m"), ("slope", "Slope 200–1000 m"), ("shelf", "Shelf < 200 m")]
COLORS = {"argo": "#2a78d6", "ooi": "#eb6834"}
PEAK_BINS = [0, 50, 100, 150, 201]
PEAK_LABELS = ["0–50", "50–100", "100–150", "150–200"]
DEPTHS = np.arange(5, 200, 10)
BINS = [f"CHLA_{a}_{a + 10}" for a in range(0, 200, 10)]


def load():
    wd = pd.read_parquet(DEPTH, columns=["profile_id", "depth_class"])
    cols = ["design", "repeat", "bin", "y", "yhat", "platform", "instrument", "profile_id"]
    p = pd.concat(pd.read_parquet(f, columns=cols) for f in sorted((RUN / "preds").glob(f"both__{DESIGN}__*.parquet")))
    return p[p["design"] == DESIGN].merge(wd, on="profile_id")


def soca_metrics(p):
    def one(g):
        x, y = g["yhat"].to_numpy(), g["y"].to_numpy()
        o, pr = 10 ** y, 10 ** x
        return pd.Series({"r2": np.corrcoef(x, y)[0, 1] ** 2, "slope": np.polyfit(y, x, 1)[0],
                          "MAPD": 100 * np.median(np.abs(pr - o) / o), "RMSD": np.sqrt(((pr - o) ** 2).mean())})
    m = p.groupby(["depth_class", "repeat"]).apply(one, include_groups=False).groupby("depth_class").mean()
    one_rep = p[p["repeat"] == p["repeat"].min()]
    m["profiles"] = one_rep.groupby("depth_class")["profile_id"].nunique()
    site = np.where(one_rep["platform"] == "ooi", one_rep["instrument"].str[4:6], one_rep["instrument"])
    m["floats_or_sites"] = one_rep.assign(site=site).groupby("depth_class")["site"].nunique()
    return m


def profiles(p):
    keys = ["repeat", "profile_id", "platform", "depth_class"]
    y = p.pivot_table(index=keys, columns="bin", values="y").reindex(columns=BINS)
    yh = p.pivot_table(index=keys, columns="bin", values="yhat").reindex(columns=BINS)
    rows = []
    for (k, oy), (_, py) in zip(y.iterrows(), yh.iterrows()):
        ok = oy.notna().to_numpy()
        if ok.sum() < 10:
            continue
        o, pr, z = 10 ** oy.to_numpy()[ok], 10 ** py.to_numpy()[ok], DEPTHS[ok]
        os_, ps_ = uniform_filter1d(o, 3, mode="nearest"), uniform_filter1d(pr, 3, mode="nearest")
        rows.append(dict(zip(keys, k), peak_obs=z[np.argmax(os_)], peak_err=z[np.argmax(ps_)] - z[np.argmax(os_)],
                         int_obs=10 * o.sum(), int_pred=10 * pr.sum()))
    return pd.DataFrame(rows)


def main():
    apply_style()
    p = load()
    m = soca_metrics(p)
    print("SOCA-style metrics, all depths pooled (mean over repeats):")
    print(m.round(2).to_string())
    print("\n| | r² (log10) | Slope | MAPD | RMSD (mg m⁻³) |\n|---|---:|---:|---:|---:|")
    print("| SOCA2024 (open ocean, own validation) | 0.83 | 0.82 | 30% | 0.19 |")
    for dc, title in CLASSES:
        r = m.loc[dc]
        print(f"| {title.split(' ')[0] if dc != 'open ocean' else 'Open ocean'} | {r.r2:.2f} | {r.slope:.2f} | {r.MAPD:.0f}% | {r.RMSD:.2f} |")

    pr = profiles(p)
    li, lp = np.log10(pr["int_obs"]), np.log10(pr["int_pred"])
    r2_int = (pr.assign(li=li, lp=lp).groupby(["depth_class", "repeat"])
              .apply(lambda g: 1 - ((g.lp - g.li) ** 2).sum() / ((g.li - g.li.mean()) ** 2).sum(), include_groups=False)
              .groupby("depth_class").mean())
    peak_summary = pr.groupby("depth_class")["peak_err"].agg(
        median_abs=lambda s: s.abs().median(), within20=lambda s: (s.abs() <= 20).mean())
    print("\nIntegrated Chl a R² (log10), mean over repeats:")
    print(r2_int.round(2).to_string())
    print("\nPeak depth error: median |error| (m), share within 20 m:")
    print(peak_summary.round(2).to_string())

    r0 = pr[pr["repeat"] == pr["repeat"].min()]
    fig, ax = plt.subplots(1, 3, figsize=(COLUMN_WIDTH_IN, 4.6), sharex=True, sharey=True)
    lo, hi = -0.5, 2.8  # log10 mg m^-2; a few open-ocean Argo profiles below 10^-0.5 fall off the axes
    xx = np.logspace(lo, hi, 50)
    for j, (dc, title) in enumerate(CLASSES):
        g = r0[r0["depth_class"] == dc]
        b = ax[j]
        for pl in ["argo", "ooi"]:
            q = g[g["platform"] == pl]
            if len(q):
                b.scatter(q["int_obs"], q["int_pred"], s=4, alpha=0.3, color=COLORS[pl],
                          label="Argo" if pl == "argo" else "OOI", rasterized=True)
        b.plot(xx, xx, "k--", lw=1)
        b.plot(xx, 0.5 * xx, ":", color="0.4", lw=1)
        b.plot(xx, 1.5 * xx, ":", color="0.4", lw=1)
        b.set_xscale("log")
        b.set_yscale("log")
        b.set_xlim(10 ** lo, 10 ** hi)
        b.set_ylim(10 ** lo, 10 ** hi)
        b.set_title(title, fontsize=20)
        b.set_xlabel("Observed (mg m$^{-2}$)", fontsize=18)
        b.tick_params(labelsize=16)
        b.text(0.04, 0.96, f"R² {r2_int.get(dc, np.nan):.2f}\nn {len(g):,}", transform=b.transAxes,
               va="top", fontsize=16)
    ax[0].set_ylabel("Predicted (mg m$^{-2}$)", fontsize=18)
    ax[0].legend(loc="lower right", fontsize=14, markerscale=4)
    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, dpi=DPI)
    print(OUT)


if __name__ == "__main__":
    main()
