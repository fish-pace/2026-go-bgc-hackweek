"""Scan the OOI windows for biofouling and other suspect data (Eli, 2026-11-24).

The release's only biofouling test (run.flag_deep_biofouling) looks for a
uniformly high column at 100-200 m, so it cannot see shallow profilers or
fixed single-depth instruments. Found by eye first: both Pioneer offshore
profilers (cp13nopm, cp13sopm) read 4-10 mg m^-3 from 20 to 80 m in Aug-Sep
2026 while PACE chlor_a was about 0.2.

Unit of the scan: instrument x calendar month (fouling and calibration
problems last weeks to months, and a month is long enough for a stable
median). Tests, each on monthly medians:

  sat   the instrument's shallowest bin vs PACE chlor_a at the same pixel and
        day: anomaly = median(log10 in situ - log10 chlor_a) for the month
        minus the instrument's own all-time median. |anomaly| > 0.5 (a factor
        of ~3 away from the instrument's usual relation) flags the month.
        Each instrument is compared with itself, so a site's steady offset
        (see claude/notes/paper-leakage-and-ooi-sites.md) is not flagged.
        Only instruments whose shallowest bin is above 100 m.
  floor bins at 100-200 m: monthly median > 0.5 mg m^-3 flags the month
        (deep Chl a is normally well below that; fouling raises the floor).
  flat  profilers with >= 4 bins in 20-80 m: column within a factor of 1.5
        (max/min of the monthly medians) AND above 1 mg m^-3 AND at least
        3x PACE chlor_a. Winter mixing can make a uniform column, but not one
        far above the surface value.

Gliders (poster v2, #22; `--platform glider`): the same tests, with the
deployment as the instrument. A glider moves, so its "own baseline" is the
deployment's median relation to PACE over the region it covers; deployments
stay within one region (fish-pace-datasets claude/notes/chla-z-glider.md).
The glider release already replaced deployments that looked wrong as a whole,
so this scan is for shorter episodes.

A month needs >= 10 windows to be tested. Output (in the split-design folder,
<platform>-qc/): <platform>_qc_months.csv (all diagnostics),
<platform>_qc_flags.csv (flagged instrument-months), and
<platform>_qc_scan.png (monthly series per instrument, flagged months
shaded) for checking by eye. The reviewed list, <platform>_qc_exclude.csv,
sits next to this script and is read by run.load.
"""

import argparse
import re
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import warnings

import run

warnings.filterwarnings("ignore", message="Mean of empty slice")

SAT_MAX = 0.5
FLOOR_MAX = 0.5
FLAT_RATIO, FLAT_MIN, FLAT_SAT = 1.5, 1.0, 3.0
MIN_N = 10

# Flags checked by eye on ooi_qc_scan.png (Eli asked to drop anything wonky,
# 2026-11-24). These three look natural, so they are kept in the data:
REVIEWED_KEEP = {"ooi": {
    ("ooi-cp10cnsm-rid27-02-flortd000", "202502"):
        "low vs PACE, but all three Pioneer surface moorings read low that month: likely winter satellite bias",
    ("ooi-gi01sumo-rii11-02-flordg032", "202502"):
        "70 m sensor in Irminger winter mixing; in situ and PACE both low",
    ("ooi-cp14nepm-wfp01-04-flortk000", "202408"):
        "20-30 m high vs PACE but 100-200 m floor normal: likely a subsurface maximum",
}, "glider": {}}


def exclude_file(platform: str) -> Path:
    return Path(__file__).with_name(f"{platform}_qc_exclude.csv")


def load(cache: Path, platform: str) -> pd.DataFrame:
    o = run.fetch(cache, [platform])[platform]  # downloads the release tables if not cached
    o["inst"] = o["profile_id"].astype(str).str.replace(r"_\d{8}(T\d{2})?$", "", regex=True)
    o["month"] = o["profile_id"].astype(str).str.extract(r"_(\d{6})\d{2}")[0]
    return o


def scan(o: pd.DataFrame):
    bins = [c for c in o.columns if re.fullmatch(r"CHLA_\d+_\d+", c)]  # not CHLA_FLUOR_* (gliders)
    top = {b: int(b.split("_")[1]) for b in bins}
    rows = []
    for inst, g in o.groupby("inst"):
        have = [b for b in bins if g[b].notna().any()]
        shallow = have[0]
        deep = [b for b in have if top[b] >= 100]
        mid = [b for b in have if 20 <= top[b] < 80]
        ok = (g[shallow] > 0) & (g["pace_chlor_a"] > 0)
        d = np.log10(g.loc[ok, shallow]) - np.log10(g.loc[ok, "pace_chlor_a"])
        base = d.median() if top[shallow] < 100 and len(d) else np.nan
        for m, gm in g.groupby("month"):
            r = dict(inst=inst, month=m, n=len(gm), shallow_bin=shallow,
                     shallow_med=gm[shallow].median(), sat_med=gm["pace_chlor_a"].median())
            okm = ok.loc[gm.index]
            if np.isfinite(base) and okm.sum() >= MIN_N:
                r["sat_anom"] = d.loc[okm[okm].index].median() - base
            if deep and len(gm) >= MIN_N:
                r["floor_med"] = gm[deep].stack().median()
            if len(mid) >= 4 and len(gm) >= MIN_N:
                med = gm[mid].median()
                if med.notna().sum() >= 4 and med.min() > 0:
                    r["flat_ratio"] = med.max() / med.min()
                    r["flat_level"] = med.median()
            rows.append(r)
    m = pd.DataFrame(rows)
    m["flag_sat"] = m["sat_anom"].abs() > SAT_MAX
    m["flag_floor"] = m["floor_med"] > FLOOR_MAX
    m["flag_flat"] = ((m["flat_ratio"] < FLAT_RATIO) & (m["flat_level"] > FLAT_MIN)
                      & (m["flat_level"] > FLAT_SAT * m["sat_med"]))
    m["flag"] = m[["flag_sat", "flag_floor", "flag_flat"]].any(axis=1)
    return m


def plot(m: pd.DataFrame, out: Path, platform: str):
    insts = sorted(m["inst"].unique())
    nc = 5
    nr = int(np.ceil(len(insts) / nc))
    fig, ax = plt.subplots(nr, nc, figsize=(4 * nc, 2.6 * nr), squeeze=False)
    for a, inst in zip(ax.flat, insts):
        g = m[m.inst == inst].sort_values("month")
        x = pd.to_datetime(g["month"], format="%Y%m")
        a.semilogy(x, g["shallow_med"], "o-", ms=2, label=f"in situ {g['shallow_bin'].iat[0]}")
        a.semilogy(x, g["sat_med"], "k-", lw=0.8, label="PACE chlor_a")
        if g["floor_med"].notna().any():
            a.semilogy(x, g["floor_med"], "s-", ms=2, color="tab:red", label="100-200 m")
        for xi, f in zip(x, g["flag"]):
            if f:
                a.axvspan(xi, xi + pd.offsets.MonthEnd(1), color="orange", alpha=0.35)
        a.set_title(inst.replace("ooi-", ""), fontsize=8)
        a.tick_params(labelsize=7)
        a.set_ylim(0.01, 50)
    for a in ax.flat[len(insts):]:
        a.axis("off")
    ax[0, 0].legend(fontsize=6)
    fig.suptitle(f"{platform.upper() if platform == 'ooi' else platform.capitalize()} monthly medians; orange = flagged month", fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=80)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", type=Path, default=run.DEFAULT_CACHE)
    ap.add_argument("--platform", choices=["ooi", "glider"], default="ooi")
    ap.add_argument("--out", type=Path, default=None, help="default: <split-design>/<platform>-qc")
    args = ap.parse_args()
    pf = args.platform
    out = args.out or run.DEFAULT_OUT / f"{pf}-qc"
    out.mkdir(parents=True, exist_ok=True)
    m = scan(load(args.cache, pf))
    m.to_csv(out / f"{pf}_qc_months.csv", index=False)
    f = m[m["flag"]]
    f.to_csv(out / f"{pf}_qc_flags.csv", index=False)
    keep = f.apply(lambda r: (r["inst"], r["month"]) in REVIEWED_KEEP[pf], axis=1)
    ex = f.loc[~keep, ["inst", "month", "n", "flag_sat", "flag_floor", "flag_flat"]]
    ex.to_csv(exclude_file(pf), index=False)  # read by run.load; committed with the code
    print(f"excluded (after review): {len(ex)} instrument-months, {ex['n'].sum()} windows -> {exclude_file(pf).name}")
    plot(m, out / f"{pf}_qc_scan.png", pf)
    cols = ["inst", "month", "n", "shallow_med", "sat_med", "sat_anom", "floor_med", "flat_ratio",
            "flag_sat", "flag_floor", "flag_flat"]
    print(f"{len(f)} of {len(m)} instrument-months flagged; {f['n'].sum()} of {m['n'].sum()} windows")
    print(f[cols].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
