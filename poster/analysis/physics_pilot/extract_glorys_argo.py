"""Daily GLORYS12 temperature profiles and mixed-layer depth at the BGC-Argo profiles.

Extends the OOI physics pilot (extract_glorys.py) to Argo (Eli, 2026-11-24):
the OOI-only, pre-QC pilot is not convincing on its own, and Argo has
independent instruments and calibration. Same product, variables and depth
range as extract_glorys.py; see its docstring for why GLORYS12. Physics
inputs must be global fields (reanalysis), never the float's own T/S, so a
model using them can still make maps.

One request per profile: the GLORYS daily mean on the profile's UTC date (like
the L3 daily Rrs match), at the nearest GLORYS cell with water at the surface
to the profile's PACE pixel. About 10 s per request (timed on 20 profiles,
2026-11-24), so requests run in parallel worker processes.

Recovers from failures: profiles are grouped into chunks of --chunk, one
parquet per chunk, written atomically (.part then rename); each request is
retried with backoff; rerunning the script skips finished chunks. A profile
that still fails after all retries is left out of its chunk and listed in
failed.csv, and a rerun with --retry-failed fetches just those.

Output: ~/shared-public/chla-z/glorys12/argo_profiles/chunk_NNNN.parquet with
profile_id, time (GLORYS day), T_<depth> columns, mlotst, glorys_lat,
glorys_lon, glorys_km (same columns as the OOI files, plus profile_id).
Needs a Copernicus Marine login (copernicusmarine login).
"""

import argparse
import multiprocessing
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "split_design"))
import run  # noqa: E402

DATASET = "cmems_mod_glo_phy_my_0.083deg_P1D-m"
OUT = run.DEFAULT_OUT.parent / "glorys12" / "argo_profiles"
MAX_DEPTH = 230.0
BOXES = (0.1, 0.3)  # degrees around the pixel; the wider box only if the first has no water


def fetch_one(lat, lon, day):
    import copernicusmarine as cm

    for box in BOXES:
        ds = cm.open_dataset(
            dataset_id=DATASET, variables=["thetao", "mlotst"],
            minimum_latitude=lat - box, maximum_latitude=lat + box,
            minimum_longitude=lon - box, maximum_longitude=lon + box,
            minimum_depth=0, maximum_depth=MAX_DEPTH,
            start_datetime=day, end_datetime=day, service="arco-time-series",
        ).load()
        surf = ds["thetao"].isel(depth=0, time=0).values
        if np.isfinite(surf).any():
            break
    else:
        raise ValueError("no GLORYS water cell near the pixel")
    la, lo = np.meshgrid(ds.latitude.values, ds.longitude.values, indexing="ij")
    dist = np.hypot(la - lat, (lo - lon) * np.cos(np.radians(lat)))
    dist[~np.isfinite(surf)] = np.inf
    i, j = np.unravel_index(np.argmin(dist), dist.shape)
    cell = ds.isel(latitude=i, longitude=j, time=0)
    row = {f"T_{z:.1f}": float(v) for z, v in zip(cell.depth.values, cell["thetao"].values)}
    row.update(time=pd.Timestamp(cell.time.values), mlotst=float(cell["mlotst"]),
               glorys_lat=float(cell.latitude), glorys_lon=float(cell.longitude),
               glorys_km=float(dist[i, j]) * 111.0)
    return row


def do_chunk(k, rows, out: Path):
    got, failed = [], []
    for pid, lat, lon, day in rows:
        for attempt in range(4):
            try:
                r = fetch_one(lat, lon, day)
                r["profile_id"] = pid
                got.append(r)
                break
            except Exception as e:  # network drops; retry with backoff
                if attempt == 3:
                    failed.append((pid, repr(e)[:200]))
                else:
                    time.sleep(15 * (attempt + 1))
    f = out / f"chunk_{k:04d}.parquet"
    pd.DataFrame(got).to_parquet(f.with_suffix(".part"))
    f.with_suffix(".part").rename(f)
    return k, len(got), failed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--chunk", type=int, default=50)
    ap.add_argument("--limit", type=int, default=None, help="first N profiles only (testing)")
    ap.add_argument("--retry-failed", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    d, _, _ = run.load(run.DEFAULT_CACHE)
    a = d[d.platform == "argo"].sort_values("profile_id").reset_index(drop=True)
    lat = a["pace_Rrs_lat"].fillna(a["lat"]).astype(float)
    lon = ((a["pace_Rrs_lon"].fillna(a["lon"]).astype(float) + 180) % 360) - 180
    day = pd.to_datetime(a["time"], utc=True).dt.strftime("%Y-%m-%d")
    rows = list(zip(a["profile_id"], lat, lon, day))
    if args.limit:
        rows = rows[: args.limit]
    failed_file = args.out / "failed.csv"

    if args.retry_failed:
        bad = set(pd.read_csv(failed_file)["profile_id"]) if failed_file.exists() else set()
        todo = [(9000 + i, [r for r in rows if r[0] in bad][i * args.chunk:(i + 1) * args.chunk])
                for i in range(int(np.ceil(len(bad) / args.chunk)))]
    else:
        chunks = [rows[i:i + args.chunk] for i in range(0, len(rows), args.chunk)]
        todo = [(k, c) for k, c in enumerate(chunks) if not (args.out / f"chunk_{k:04d}.parquet").exists()]
    print(f"{len(rows)} Argo profiles; {len(todo)} chunks to fetch with {args.workers} workers", flush=True)

    all_failed = []
    t0 = time.time()
    # Fresh "spawn" workers (not forked copies of this process, which holds the
    # release tables), each replaced after one chunk: the copernicusmarine
    # client's memory grew to ~1.4 GB per worker within one chunk (2026-11-24),
    # enough to threaten the hub's memory cap with 8 workers.
    del d, a
    ctx = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx, max_tasks_per_child=1) as ex:
        futs = [ex.submit(do_chunk, k, c, args.out) for k, c in todo]
        for n, fu in enumerate(as_completed(futs), 1):
            k, ok, failed = fu.result()
            all_failed += failed
            print(f"chunk {k:04d}: {ok} ok, {len(failed)} failed; {n}/{len(todo)} done, "
                  f"{(time.time() - t0) / 60:.0f} min", flush=True)
    if all_failed or args.retry_failed:
        pd.DataFrame(all_failed, columns=["profile_id", "error"]).to_csv(failed_file, index=False)
    print(f"finished; {len(all_failed)} profiles failed (see {failed_file.name})", flush=True)


if __name__ == "__main__":
    main()
