"""Water depth under every training profile, from ETOPO 2022 (15 arc-second).

Issue #9 (Data block); block 2 (coastal, #11) reuses the table. Rows are the
training rows of fish-pace-datasets release DATA_RELEASE after the Rrs and
biofouling filters, as loaded by ../split_design/run.py.

For each distinct profile position we ask the CoastWatch ERDDAP copy of ETOPO
2022 for a box the size of one PACE L3 4 km pixel centred on the position:

  water_depth_m               depth of the 15" cell nearest the profile
  water_depth_pixel_median_m  median depth over the box, i.e. roughly what
                              the satellite pixel spans; on the shelf break
                              the two can differ by hundreds of metres

depth_class uses water_depth_m: shelf < 200 m, slope 200-1000 m, open ocean
> 1000 m. Depths are positive down; a cell at or above sea level (possible
right at the coast) is kept with its negative depth and classed as shelf.

Positions are fetched in chunks; each chunk is written to its own file in
CACHE and skipped on a rerun, and each request is retried with backoff, so
the script can be stopped and restarted unattended.

    python poster/analysis/bathymetry/water_depth.py
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "split_design"))
import run  # noqa: E402

ERDDAP = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
DATASET = "ETOPO_2022_v1_15s"
SOURCE = {
    "bathymetry_source": "NOAA NCEI ETOPO 2022 v1, 15 arc-second (ice surface)",
    "bathymetry_doi": "10.25921/fd45-gt74",
    "bathymetry_access": f"{ERDDAP}/{DATASET} (NOAA CoastWatch West Coast ERDDAP)",
}
OUT_DIR = Path.home() / "shared-public" / "chla-z" / "bathymetry"
OUT = OUT_DIR / f"water_depth_{run.DATA_RELEASE}.parquet"
CACHE = OUT_DIR / "cache" / DATASET

# Half of a PACE L3 4 km pixel (1/24 degree).
HALF_PIXEL_DEG = 1 / 48
GRID_EDGE = 179.99791666666667  # first/last cell centre; ERDDAP refuses beyond it
CHUNK = 250
WORKERS = 4  # a few at a time is plenty and keeps the server load modest
RETRIES = 6


def fetch_box(lat: float, lon: float) -> tuple[float, float]:
    """(nearest-cell depth, box median depth) in metres, positive down."""
    la0, la1 = lat - HALF_PIXEL_DEG, lat + HALF_PIXEL_DEG
    lo0 = max(lon - HALF_PIXEL_DEG, -GRID_EDGE)
    lo1 = min(lon + HALF_PIXEL_DEG, GRID_EDGE)
    q = f"z[({la0:.5f}):1:({la1:.5f})][({lo0:.5f}):1:({lo1:.5f})]"
    url = f"{ERDDAP}/{DATASET}.csv?{urllib.parse.quote(q, safe='():')}"
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                txt = r.read().decode()
            break
        except Exception:
            if attempt == RETRIES - 1:
                raise
            time.sleep(2 ** attempt)
    box = pd.read_csv(StringIO(txt), skiprows=[1])
    i = ((box["latitude"] - lat) ** 2 + (box["longitude"] - lon) ** 2).idxmin()
    return -float(box.loc[i, "z"]), -float(box["z"].median())


def fetch_chunk(k: int, pos: pd.DataFrame) -> pd.DataFrame:
    path = CACHE / f"chunk_{k:04d}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    with ThreadPoolExecutor(WORKERS) as ex:
        res = list(ex.map(fetch_box, pos["lat"], pos["lon"]))
    out = pos.assign(
        water_depth_m=[r[0] for r in res],
        water_depth_pixel_median_m=[r[1] for r in res],
    )
    tmp = path.with_suffix(".part")
    out.to_parquet(tmp, index=False)
    tmp.rename(path)
    return out


def depth_class(z: pd.Series) -> pd.Series:
    return pd.Series(
        np.select([z < 200, z <= 1000], ["shelf", "slope"], "open ocean"), index=z.index
    )


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    d, _, _ = run.load(run.DEFAULT_CACHE)
    d["lon"] = d["lon180"]  # ETOPO is -180..180

    # Positions are sorted so chunk k always holds the same positions on a rerun.
    pos = (
        d[["lat", "lon"]].round(5).drop_duplicates().sort_values(["lat", "lon"]).reset_index(drop=True)
    )
    n_chunks = int(np.ceil(len(pos) / CHUNK))
    print(f"{len(d)} rows, {len(pos)} distinct positions, {n_chunks} chunks of {CHUNK}")
    parts = []
    for k in range(n_chunks):
        t0 = time.time()
        parts.append(fetch_chunk(k, pos.iloc[k * CHUNK : (k + 1) * CHUNK]))
        print(f"chunk {k + 1}/{n_chunks} {time.time() - t0:.1f}s", flush=True)
    depth = pd.concat(parts, ignore_index=True)

    key = d[["lat", "lon"]].round(5)
    t = (
        d[["profile_id", "platform", "instrument", "pixel"]]
        .assign(lat=key["lat"], lon=key["lon"])
        .merge(depth, on=["lat", "lon"], how="left", validate="many_to_one")
    )
    assert t["water_depth_m"].notna().all() and len(t) == len(d)
    t["lat"], t["lon"] = d["lat"].to_numpy(), d["lon"].to_numpy()
    t["depth_class"] = depth_class(t["water_depth_m"])

    meta = {
        **SOURCE,
        "data_release": f"fish-pace-datasets {run.DATA_RELEASE}",
        "water_depth_m": "depth (m, positive down) of the ETOPO 2022 15-arcsec cell nearest the profile",
        "water_depth_pixel_median_m": "median ETOPO 2022 depth over a 1/24 degree box centred on the profile",
        "depth_class": "shelf < 200 m, slope 200-1000 m, open ocean > 1000 m (from water_depth_m)",
        "script": "fish-pace/2026-go-bgc-hackweek poster/analysis/bathymetry/water_depth.py",
        "created": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
    }
    tbl = pa.Table.from_pandas(t, preserve_index=False)
    tbl = tbl.replace_schema_metadata({**tbl.schema.metadata, b"chla_z": json.dumps(meta).encode()})
    tmp = OUT.with_suffix(".part")
    pq.write_table(tbl, tmp)
    tmp.rename(OUT)
    (OUT_DIR / "README.md").write_text(
        f"# Water depth under the CHLA-Z training profiles\n\n"
        f"`{OUT.name}`: one row per training row of fish-pace-datasets release "
        f"`{run.DATA_RELEASE}` (after the Rrs and biofouling filters).\n\n"
        + "".join(f"- **{k}**: {v}\n" for k, v in meta.items())
        + "\nThe same metadata is in the parquet schema metadata under the key `chla_z`.\n"
    )
    print(f"wrote {OUT}")
    summary(t)


def summary(t: pd.DataFrame):
    """Rows and independent units per class (Argo: floats; OOI: PACE pixels = sites)."""
    cls = pd.Categorical(t["depth_class"], ["shelf", "slope", "open ocean"], ordered=True)
    g = t.assign(depth_class=cls).groupby(["depth_class", "platform"], observed=True)
    s = pd.DataFrame({"rows": g.size(), "instruments": g["instrument"].nunique(), "sites": g["pixel"].nunique()})
    print(s.to_string())


if __name__ == "__main__":
    main()
