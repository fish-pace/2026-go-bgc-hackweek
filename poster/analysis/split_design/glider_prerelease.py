"""Stand-in glider training table until fish-pace-datasets#14 is released (#22).

Poster v2 adds the IOOS Glider DAC profiles as a third platform. The glider
tables are built in the local fish-pace-datasets checkout (branch
glider-pilot) but not yet in a release, so run.py reads the glider table from
GLIDER_PRERELEASE (below) instead of the release cache. This script fills that
folder:

1. If the checkout has the released-style table
   datasets/chla_z/data/CHLA_glider_profiles_plus_PACE.parquet, copy it.
2. Otherwise (as on 2026-11-24, when the glider-pilot session had rebuilt the
   profile table but not yet rerun the PACE merge), join the PACE columns of
   the earlier window24 matchup table onto the current profile table. Why this
   is the same thing: the window24 table uses the release's PACE rule (24 h
   after time_coverage_start) and has the same profile_id, time and position
   for every row; only the CHLA columns differ (that run subtracted the dark
   offset, which Eli then dropped: Sauzède only). So CHLA comes from the
   current table and PACE from window24. Rows without a PACE granule are kept,
   as in the release tables (run.load drops rows without Rrs).

Once the glider tables are released: set run.DATA_RELEASE to the new tag and
run.GLIDER_PRERELEASE to None, and this script is no longer needed.

    python glider_prerelease.py
"""

import json
import shutil
from pathlib import Path

import pandas as pd

import run

SRC = Path.home() / "fish-pace-datasets" / "datasets" / "chla_z"
RELEASED_STYLE = SRC / "data" / "CHLA_glider_profiles_plus_PACE.parquet"
PROFILES = SRC / "data" / "CHLA_glider_profiles.parquet"
WINDOW24 = SRC / "notebooks" / "_temp_data" / "glider" / "CHLA_glider_profiles_plus_PACE_window24.parquet"


def main():
    out_dir = run.GLIDER_PRERELEASE
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / run.TABLES["glider"]
    if RELEASED_STYLE.exists():
        shutil.copy2(RELEASED_STYLE, out)
        how = f"copied {RELEASED_STYLE}"
    else:
        g = pd.read_parquet(PROFILES)
        w = pd.read_parquet(WINDOW24)
        pace = [c for c in w.columns if c.startswith("pace_")]
        chk = g[["profile_id", "time", "lat", "lon"]].merge(
            w[["profile_id", "time", "lat", "lon"]], on="profile_id", suffixes=("", "_w"))
        assert (chk["time"] == chk["time_w"]).all() and (chk["lat"] == chk["lat_w"]).all() \
            and (chk["lon"] == chk["lon_w"]).all(), "window24 rows no longer match the profile table"
        t = g.merge(w[["profile_id"] + pace], on="profile_id", how="left", validate="one_to_one")
        t.to_parquet(out.with_suffix(".part"))
        out.with_suffix(".part").rename(out)
        how = f"joined PACE columns of {WINDOW24.name} onto {PROFILES}"
    t = pd.read_parquet(out)
    rrs = [c for c in t.columns if c.startswith("pace_Rrs_") and c[-1].isdigit()]
    n_rrs = int(t[rrs].notna().any(axis=1).sum())
    info = {"how": how, "rows": len(t), "rows_with_rrs": n_rrs,
            "deployments": int(t["dataset_id"].nunique()) if "dataset_id" in t else None,
            "created": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    (out_dir / "PRERELEASE.json").write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
