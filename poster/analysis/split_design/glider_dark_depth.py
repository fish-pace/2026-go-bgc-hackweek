"""Does the glider deep fluorescence reading change with depth below 300 m? (#27)

Eli, 2026-11-26: before fetching temperature to test a temperature-dependent
dark, a cheaper test. If the dark rises as the water gets colder (or with
pressure), the deep reading should increase from 300 m to 1000 m, where the
water keeps cooling. A flat reading over that range argues against it.

What a temperature dark would need (California Current, #27 comment 2): the
surface dark is ~0 while the reading below 300 m is ~0.15, so about 0.15 over
roughly 6 -> 16 degC, ~0.015 per degC. 300 -> 1000 m cools roughly 3-4 degC
there (climatology, not measured here), so roughly +0.05 from 300 to 1000 m.

Within-profile slopes are used, so drift over a deployment does not enter:
for each glider profile with deep samples spanning >= 300 m (between 300 and
1000 m), a least-squares slope of fluorescence on depth. Then the median per
deployment. Samples pass the DAC flag where there is one (1, 2, or 0), as in
the release.

Reads the raw deep pulls of fish-pace-datasets (read only):
  datasets/chla_z/notebooks/_temp_data/glider/raw_deep/<id>/<YYYY-MM>.csv.gz
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path.home() / "fish-pace-datasets/datasets/chla_z/notebooks/_temp_data/glider/raw_deep"
REL = Path.home() / "shared-public/chla-z/fish-pace-datasets/2026_11_26/CHLA_glider_profiles_plus_PACE.parquet"
OUT = Path.home() / "shared-public/chla-z/split-design/glider_dark_depth.csv"
MIN_SPAN = 300.0
EXPECTED_PER_100M = 0.05 / 7  # see docstring


def profile_slopes(dep: Path) -> pd.DataFrame:
    parts = [pd.read_csv(f) for f in sorted(dep.glob("*.csv.gz"))]
    if not parts:
        return pd.DataFrame()
    # The chlorophyll column is named per dataset (chlorophyll, chlorophyll_a, ...).
    parts = [x.rename(columns={c: "chlorophyll" for c in x.columns
                               if c.startswith("chl") and not c.endswith(("_qc", "_flag"))}) for x in parts]
    parts = [x for x in parts if "chlorophyll" in x]
    if not parts:
        return pd.DataFrame()
    d = pd.concat(parts, ignore_index=True)
    d = d[(d["depth"] >= 300) & (d["depth"] <= 1000) & d["chlorophyll"].notna()]
    qc = [c for c in d.columns if c.endswith(("_qc", "_flag"))]
    if qc:
        d = d[d[qc[0]].isin([0, 1, 2]) | d[qc[0]].isna()]
    rows = []
    for pid, g in d.groupby("profile_id"):
        if len(g) < 5 or g["depth"].max() - g["depth"].min() < MIN_SPAN:
            continue
        b = np.polyfit(g["depth"] / 100.0, g["chlorophyll"], 1)[0]
        shallow = g.loc[g["depth"] < 400, "chlorophyll"].median()
        deep = g.loc[g["depth"] > g["depth"].max() - 100, "chlorophyll"].median()
        rows.append((pid, b, g["chlorophyll"].median(), shallow, deep, g["depth"].max()))
    return pd.DataFrame(rows, columns=["profile_id", "slope_per_100m", "median", "at_300_400", "deepest_100m", "max_depth"])


def main():
    meta = pd.read_parquet(REL, columns=["dataset_id", "region", "platform_type", "dark_offset", "deep_offset_flag"])
    meta = meta.groupby("dataset_id").agg(region=("region", "first"), platform=("platform_type", "first"),
                                          dark=("dark_offset", "median"), flagged=("deep_offset_flag", "first"))
    out = []
    for dep in sorted(RAW.iterdir()):
        s = profile_slopes(dep)
        if len(s) < 5:
            continue
        out.append({"dataset_id": dep.name, "n_profiles": len(s),
                    "slope_per_100m": s["slope_per_100m"].median(),
                    "slope_iqr": s["slope_per_100m"].quantile(0.75) - s["slope_per_100m"].quantile(0.25),
                    "deep_median": s["median"].median(),
                    "at_300_400": s["at_300_400"].median(), "deepest_100m": s["deepest_100m"].median(),
                    "max_depth": s["max_depth"].median()})
    t = pd.DataFrame(out).set_index("dataset_id").join(meta, how="left")
    t["change_300_to_deepest"] = t["deepest_100m"] - t["at_300_400"]
    t.to_csv(OUT)
    pd.set_option("display.width", 200)
    print(f"{len(t)} deployments with >= 5 profiles spanning >= {MIN_SPAN:.0f} m below 300 m; wrote {OUT}")
    print(f"a temperature dark (California Current) would need about +{EXPECTED_PER_100M:.4f} per 100 m\n")
    cols = ["n_profiles", "deep_median", "slope_per_100m", "change_300_to_deepest", "max_depth"]
    g = t.groupby("region")
    s = g[cols].median().assign(deployments=g.size(), share_slope_pos=g["slope_per_100m"].apply(lambda x: (x > 0).mean()))
    print(s.round(4).sort_values("deployments", ascending=False).to_string())
    print("\nlarge darks (median deep reading > 0.1):")
    big = t[t["deep_median"] > 0.1]
    print(big[cols].describe().round(4).to_string())
    print("\nsmall darks (<= 0.1):")
    print(t[t["deep_median"] <= 0.1][cols].describe().round(4).to_string())


if __name__ == "__main__":
    main()
