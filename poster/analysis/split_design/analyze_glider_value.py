"""Read runs/glider-value-<release> (run_glider_value.py) and answer #27's questions.

Eli, 2026-11-26:
  1. With glider bins below 100 m removed, what are block 2's numbers?
  2. Does glider data help predict Chl a on the slope and shelf? Same
     held-out rows, model trained with vs without gliders.
  3. Can we predict on the shelf when the water is clear (low surface Chl a),
     or is the shelf hard at every Chl a level?

For 3, skill is compared at equal surface Chl a across water-depth classes,
because r^2 inside a narrow stratum is small by construction. Measures, per
profile over its observed bins above 100 m, in log10:
  rmse        prediction error
  rmse_flat   error of a "flat" profile: every bin set to the profile's own
              observed 0-10 m value (as if the surface value were known
              perfectly and the column were mixed)
  skill_flat  1 - rmse^2 / rmse_flat^2 over the stratum: > 0 means the model
              gets the vertical shape better than a mixed column would,
              even though the flat profile is given the true surface
Surface Chl a stratum: PACE chlor_a at the profile (what a product knows).
"""

from pathlib import Path

import numpy as np
import pandas as pd

import run

SHARED = Path.home() / "shared-public" / "chla-z"
RUN = SHARED / "split-design" / "runs" / "glider-value-2026_11_26" / "preds"
OLD = SHARED / "split-design" / "runs" / "platform-glider-2026_11_26" / "preds"
DEPTH = SHARED / "bathymetry" / "water_depth_2026_11_26.parquet"
CACHE = SHARED / "fish-pace-datasets" / "2026_11_26"
ORDER = ["open ocean", "slope", "shelf"]
CHL_BINS = [0, 0.1, 0.2, 0.5, 1, 2, 100]


def r2(q):
    return np.corrcoef(q["y"], q["yhat"])[0, 1] ** 2 if len(q) > 2 else np.nan


def load(path, design, repeats=(0, 1, 2)):
    wd = pd.read_parquet(DEPTH, columns=["profile_id", "depth_class"])
    p = pd.concat(pd.read_parquet(path / f"both__{design}__1deg_30d__r{r}.parquet",
                                  columns=["profile_id", "platform", "instrument", "bin", "y", "yhat", "repeat"])
                  for r in repeats)
    p = p.merge(wd, on="profile_id")
    p["top"] = p["bin"].str.split("_").str[1].astype(int)
    return p


def pace_surface():
    cols = ["profile_id", "pace_chlor_a", "pace_Kd_490"]
    parts = [pd.read_parquet(CACHE / run.TABLES[k], columns=cols) for k in ("argo", "ooi", "glider")]
    return pd.concat(parts).drop_duplicates("profile_id").set_index("profile_id")


def table(p, label):
    rows = {}
    for dc in ORDER:
        q = p[p["depth_class"] == dc]
        rows[dc] = {"r2 pooled": r2(q), "r2 Argo+OOI": r2(q[q.platform != "glider"]),
                    "r2 glider": r2(q[q.platform == "glider"]),
                    "rmse glider": np.sqrt(((q.yhat - q.y)[q.platform == "glider"] ** 2).mean()),
                    "bias glider": (q.yhat - q.y)[q.platform == "glider"].mean()}
    t = pd.DataFrame(rows).T
    print(f"\n--- {label}")
    print(t.round(3).to_string())
    return t


def shape_skill(p, surf):
    """Per profile, bins above 100 m: model error vs a flat profile at the true surface value."""
    q = p[p["top"] < 100]
    s0 = q[q["top"] == 0].set_index(["repeat", "profile_id"])["y"].rename("y0")
    q = q.join(s0, on=["repeat", "profile_id"], how="inner")
    q = q.join(surf, on="profile_id")
    q = q.assign(se=(q.yhat - q.y) ** 2, se_flat=(q.y0 - q.y) ** 2)
    g = q.groupby(["repeat", "profile_id"])
    prof = g.agg(platform=("platform", "first"), depth_class=("depth_class", "first"),
                 chl=("pace_chlor_a", "first"), n=("y", "size"), se=("se", "sum"),
                 se_flat=("se_flat", "sum"), ymax=("y", "max"), ymin=("y", "min"))
    prof["range_obs"] = prof["ymax"] - prof["ymin"]
    prof = prof[(prof["n"] >= 4) & prof["chl"].notna()]
    prof["chl_bin"] = pd.cut(prof["chl"], CHL_BINS)
    out = prof.groupby(["depth_class", "chl_bin"], observed=True).apply(lambda x: pd.Series({
        "profiles": len(x) / x.index.get_level_values("repeat").nunique(),
        "rmse": np.sqrt(x.se.sum() / x.n.sum()),
        "rmse_flat": np.sqrt(x.se_flat.sum() / x.n.sum()),
        "skill_flat": 1 - x.se.sum() / x.se_flat.sum(),
        "obs_range_log10": x.range_obs.median()}), include_groups=False)
    return prof, out


def main():
    pd.set_option("display.width", 200)
    cut = load(RUN, "argo_bias_cut100")
    ng = load(RUN, "no_glider_train")
    old = load(OLD, "argo_bias")
    old_cut = old[~((old.platform == "glider") & (old.top >= 100))]

    print("=== 1. Block 2 numbers (pointwise, all depths pooled; mean of repeats pooled)")
    table(old, "all gliders, all depths (as #27 first comment, r0-2)")
    table(old_cut, "same run, glider bins >= 100 m only dropped from scoring")
    table(cut, "refit: glider bins >= 100 m dropped from training and scoring")

    print("\n=== 2. Does glider training data help? Same held-out rows, bins above 100 m")
    for label, p in [("with gliders", cut), ("without gliders", ng)]:
        table(p[p["top"] < 100], label + " (bins < 100 m)")
    m = cut.merge(ng[["profile_id", "bin", "repeat", "yhat"]], on=["profile_id", "bin", "repeat"],
                  suffixes=("", "_ng"))
    m = m[m["top"] < 100]
    rows = {}
    for (pl, dc), q in m.groupby(["platform", "depth_class"]):
        e1, e0 = q.yhat - q.y, q.yhat_ng - q.y
        rows[(pl, dc)] = {"rows": len(q) // 3, "rmse with": np.sqrt((e1 ** 2).mean()),
                          "rmse without": np.sqrt((e0 ** 2).mean()),
                          "r2 with": r2(q), "r2 without": r2(q.assign(yhat=q.yhat_ng)),
                          "bias without": e0.mean()}
    print("\nby platform and class (bins < 100 m):")
    print(pd.DataFrame(rows).T.round(3).to_string())

    print("\n=== 3. Skill vs surface Chl a (PACE chlor_a), model with gliders, bins < 100 m")
    surf = pace_surface()
    prof, out = shape_skill(cut, surf)
    print(out.round(3).to_string())
    print("\nshelf by platform:")
    sh = prof[prof["depth_class"] == "shelf"]
    print(sh.groupby(["platform", "chl_bin"], observed=True).apply(lambda x: pd.Series({
        "profiles": len(x) / 3, "rmse": np.sqrt(x.se.sum() / x.n.sum()),
        "skill_flat": 1 - x.se.sum() / x.se_flat.sum()}), include_groups=False).round(3).to_string())
    prof.assign(chl_bin=prof["chl_bin"].astype(str)).reset_index().to_parquet(RUN.parent / "profile_skill.parquet")


if __name__ == "__main__":
    main()
