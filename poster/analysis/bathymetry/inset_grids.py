"""Small ETOPO 2022 grids around the OOI coastal arrays, for the map insets.

The Data map (poster/scripts/fig_data_map.py) draws the 200 m and 1000 m
contours, the water-depth class boundaries, in its insets. It must run in
seconds, so the grids are fetched once here and saved next to the water-depth
table. Stride 4 on the 15" grid (1 arc-minute) is plenty for two contours.

    python poster/analysis/bathymetry/inset_grids.py
"""

import time
import urllib.request
from io import StringIO

import pandas as pd

from water_depth import DATASET, ERDDAP, OUT_DIR, RETRIES

# Boxes as (lat0, lat1, lon0, lon1); keep in sync with INSETS in fig_data_map.py.
BOXES = {
    "endurance": (43.6, 47.8, -131.0, -123.4),
    "pioneer": (35.3, 36.6, -75.8, -74.3),
}
STRIDE = 4


def fetch(name, box):
    path = OUT_DIR / f"etopo2022_{name}.parquet"
    if path.exists():
        return
    la0, la1, lo0, lo1 = box
    url = f"{ERDDAP}/{DATASET}.csv?z[({la0}):{STRIDE}:({la1})][({lo0}):{STRIDE}:({lo1})]"
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                txt = r.read().decode()
            break
        except Exception:
            if attempt == RETRIES - 1:
                raise
            time.sleep(2 ** attempt)
    g = pd.read_csv(StringIO(txt), skiprows=[1])
    tmp = path.with_suffix(".part")
    g.to_parquet(tmp, index=False)
    tmp.rename(path)
    print(f"wrote {path} ({len(g)} cells)")


if __name__ == "__main__":
    for name, box in BOXES.items():
        fetch(name, box)
