"""Poster v2 numbers with the 2026_11_26 glider release (20 -> 280 deployments).

Eli, 2026-11-26: the poster is printed from release 2026_11_24; for the talk,
what does more glider data change? This reruns nothing; it reads two runs of
run_platform.py (design "argo_bias", space-time 1 deg x 30 d, 5 repeats):

  old  runs/platform-glider             + water_depth_2026_11_24 (printed poster)
  new  runs/platform-glider-2026_11_26  + water_depth_2026_11_26

and prints, for both, block 2's table and integrated R² (the same functions
as poster/scripts/fig_profiles_by_class.py, so the numbers match the poster's
by construction), plus the breakdowns the paper note §11 used: by platform
within each water-depth class, the platform offsets, and rows / units per
class. New-release versions of the poster figures go to FIG_DIR, not
poster/figures, so `make` in poster/ still rebuilds the printed poster.

Make the new run first:
  CHLAZ_DATA_RELEASE=2026_11_26 python ooi_qc_scan.py --platform glider
  CHLAZ_DATA_RELEASE=2026_11_26 python ../bathymetry/water_depth.py
  CHLAZ_DATA_RELEASE=2026_11_26 python run_platform.py \
      --out ~/shared-public/chla-z/split-design/runs/platform-glider-2026_11_26
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
import fig_data_map  # noqa: E402
import fig_example_profiles  # noqa: E402
import fig_profiles_by_class as fpc  # noqa: E402

SHARED = Path.home() / "shared-public" / "chla-z"
RUNS = {
    "old (2026_11_24, poster)": ("platform-glider", "2026_11_24"),
    "new (2026_11_26)": ("platform-glider-2026_11_26", "2026_11_26"),
}
FIG_DIR = HERE / "figures_2026_11_26"
ORDER = ["open ocean", "slope", "shelf"]


def r2_log(g):
    return 1 - ((g.lp - g.li) ** 2).sum() / ((g.li - g.li.mean()) ** 2).sum()


def summarize(run, tag):
    fpc.RUN = SHARED / "split-design" / "runs" / run
    fpc.DEPTH = SHARED / "bathymetry" / f"water_depth_{tag}.parquet"
    p = fpc.load()
    m = fpc.soca_metrics(p).reindex(ORDER)

    pr = fpc.profiles(p)
    pr = pr.assign(li=np.log10(pr["int_obs"]), lp=np.log10(pr["int_pred"]))
    r2_int = pr.groupby(["depth_class", "repeat"]).apply(r2_log, include_groups=False).groupby("depth_class").mean()
    m["int_R2"] = r2_int
    # Same Argo + OOI rows in both releases: does adding gliders to training
    # change skill on them, or only the platform mix of the pooled numbers?
    ao = p[p["platform"] != "glider"]
    m["r2_argo_ooi"] = fpc.soca_metrics(ao)["r2"]
    m["int_R2_argo_ooi"] = (pr[pr["platform"] != "glider"].groupby(["depth_class", "repeat"])
                            .apply(r2_log, include_groups=False).groupby("depth_class").mean())
    m["glider_row_share"] = p[p["repeat"] == 0].groupby("depth_class")["platform"].apply(lambda s: (s == "glider").mean())
    by_pl = (pr.groupby(["depth_class", "platform", "repeat"]).apply(r2_log, include_groups=False)
             .groupby(["depth_class", "platform"]).mean().unstack())
    n_int = pr[pr["repeat"] == 0].groupby(["depth_class", "platform"]).size().unstack()

    # Pointwise skill per platform within class (same SOCA metrics, one platform).
    plat = pd.concat({k: fpc.soca_metrics(g)[["r2", "slope", "MAPD", "RMSD"]] for k, g in p.groupby("platform")})
    r0 = p[p["repeat"] == 0]
    units = r0.groupby(["depth_class", "platform"])["instrument"].nunique().unstack()
    rows = r0.groupby(["depth_class", "platform"])["profile_id"].nunique().unstack()
    return dict(m=m, int_by_platform=by_pl, n_int=n_int, plat=plat, units=units, rows=rows)


def offsets(run):
    f = SHARED / "split-design" / "runs" / run / "preds" / "both__argo_bias__1deg_30d__r0.parquet"
    p = pd.read_parquet(f, columns=["bin", "platform", "fold", "platform_bias"])
    p = p[p["platform"] != "argo"]
    o = p.groupby(["platform", "bin", "fold"])["platform_bias"].first().groupby(["platform", "bin"]).agg(["mean", "std"])
    return o.loc[(slice(None), ["CHLA_0_10", "CHLA_50_60", "CHLA_100_110"]), :]


def figures():
    FIG_DIR.mkdir(exist_ok=True)
    new = SHARED / "split-design" / "runs" / RUNS["new (2026_11_26)"][0]
    wd = SHARED / "bathymetry" / "water_depth_2026_11_26.parquet"
    fpc.RUN, fpc.DEPTH, fpc.OUT = new, wd, FIG_DIR / "fig_profiles_by_class.png"
    fpc.main()
    fig_example_profiles.PREDS = new / "preds" / "both__argo_bias__1deg_30d__r0.parquet"
    fig_example_profiles.DEPTH, fig_example_profiles.OUT = wd, FIG_DIR / "fig_example_profiles.png"
    fig_example_profiles.main()
    fig_data_map.TABLE, fig_data_map.OUT = wd, FIG_DIR / "fig_data_map.png"
    fig_data_map.main()


# Glider QC rules (#27, Eli 2026-11-26): refits with run_platform.py
# --glider-rule, 3 repeats each; compared with repeats 0-2 of the full run.
RULES = {
    "all gliders": "platform-glider-2026_11_26",
    "drop deep offset > 0.1": "platform-glider-2026_11_26-large-offset",
    "drop Spray gliders": "platform-glider-2026_11_26-no-spray",
}


def compare_rules(repeats=(0, 1, 2)):
    fpc.DEPTH = SHARED / "bathymetry" / "water_depth_2026_11_26.parquet"
    out = {}
    for name, run in RULES.items():
        fpc.RUN = SHARED / "split-design" / "runs" / run
        p = fpc.load()
        p = p[p["repeat"].isin(repeats)]
        pr = fpc.profiles(p)
        pr = pr.assign(li=np.log10(pr["int_obs"]), lp=np.log10(pr["int_pred"]))
        r = {}
        for dc in ORDER:
            q = p[p["depth_class"] == dc]
            r[("r2 pooled", dc)] = fpc.soca_metrics(q)["r2"].iloc[0]
            r[("r2 Argo+OOI rows", dc)] = fpc.soca_metrics(q[q.platform != "glider"])["r2"].iloc[0]
            gq = q[q.platform == "glider"]
            r[("r2 glider rows", dc)] = fpc.soca_metrics(gq)["r2"].iloc[0] if len(gq) else np.nan
            ip = pr[pr["depth_class"] == dc]
            r[("integrated R2", dc)] = ip.groupby("repeat").apply(r2_log, include_groups=False).mean()
            gi = ip[ip.platform == "glider"]
            r[("integrated R2 glider", dc)] = gi.groupby("repeat").apply(r2_log, include_groups=False).mean() if len(gi) > 2 else np.nan
            r0 = gq[gq["repeat"] == repeats[0]]
            r[("glider deployments", dc)] = r0["instrument"].nunique()
            r[("glider rows", dc)] = r0["profile_id"].nunique()
        out[name] = r
    t = pd.DataFrame(out)
    print(f"Glider QC rules, repeats {list(repeats)}:")
    print(t.round(2).to_string())
    return t


def main():
    pd.set_option("display.width", 160)
    if "--rules" in sys.argv:
        compare_rules()
        return
    for name, (run, tag) in RUNS.items():
        s = summarize(run, tag)
        print(f"\n===== {name}: runs/{run}")
        print("Block 2 table (SOCA metrics, all depths pooled) + integrated R²:")
        print(s["m"].round(2).to_string())
        print("\nIntegrated R² by platform within class (n profiles, repeat 0):")
        print(s["int_by_platform"].round(2).to_string())
        print(s["n_int"].to_string())
        print("\nPointwise SOCA metrics by platform and class:")
        print(s["plat"].round(2).to_string())
        print("\nRows (profiles/windows) and units (floats, OOI instruments, glider deployments):")
        print(s["rows"].to_string())
        print(s["units"].to_string())
        print("\nPlatform offsets (log10; mean, SD over folds, repeat 0):")
        print(offsets(run).round(3).to_string())
    if "--figures" in sys.argv:
        figures()


if __name__ == "__main__":
    main()
