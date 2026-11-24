"""Split designs with OOI thinned to one 3 h solar-time window per day.

Eli's test (2026-11-23). The 8 OOI windows of an instrument-day share one
daily PACE Rrs, so (1) they are near-copies under a random row split, and
(2) their fluorescence differs through the day (daytime quenching) while the
inputs do not. Keeping one window per day separates the two:

  - window 0  (00–03 solar): night, no quenching, the cleanest target;
  - window 12 (12–15 solar): around the PACE overpass (~13 h), quenched.

If thinning drops the naive OOI R² toward the grouped one, the 8 windows were
the leak. If grouped R² is clearly better at night than at midday, the
solar-hour correction is part of why OOI skill is low.

Argo is unchanged. The profile_id suffix T<HH> is the window's solar start
hour (checked against solar_hour: an exact match). Reuses run.py unchanged so
the full run on the VM is not affected.
"""

import argparse
from pathlib import Path

import run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=run.DEFAULT_OUT / "runs" / "ooi-windows")
    ap.add_argument("--windows", type=int, nargs="+", default=[0, 12])
    ap.add_argument("--datasets", nargs="+", default=["ooi", "both"])
    ap.add_argument("--designs", nargs="+", default=["row", "site", "spacetime", "region"])
    ap.add_argument("--bins", choices=["all", "every-other"], default="all")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--row-repeats", type=int, default=3)
    ap.add_argument("--n-jobs", type=int, default=4)
    args = ap.parse_args()
    args.cell_deg, args.block_days, args.region_deg = [1.0], [30.0], [10.0]

    d, feats, chl = run.load(run.DEFAULT_CACHE)
    bins = chl if args.bins == "all" else chl[::2]
    win = d["profile_id"].str.extract(r"T(\d{2})$")[0].astype(float)
    for w in args.windows:
        keep = (d["platform"] == "argo") | (win == w)
        dw = d.loc[keep].reset_index(drop=True)
        out = args.out / f"win{w:02d}"
        (out / "preds").mkdir(parents=True, exist_ok=True)
        print(f"window {w:02d}: ooi rows {int((dw.platform == 'ooi').sum())}", flush=True)
        for ds, design, v, r in run.units(args):
            f = out / "preds" / f"{ds}__{design}__{v}__r{r}.parquet"
            if not f.exists():
                run.run_unit(dw, feats, bins, ds, design, v, r, f, args.n_jobs)
                print("  done", f.name, flush=True)


if __name__ == "__main__":
    main()
