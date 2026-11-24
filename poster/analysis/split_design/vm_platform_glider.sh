#!/usr/bin/env bash
# Poster v2 (#22), on the big VM: the platform run (run_platform.py) on Argo +
# OOI + glider, into runs/platform-glider (v1's runs/platform is left alone).
# Block 1 (hyperspectral) is BGC-Argo only and is not rerun. Needs the glider
# table in run.GLIDER_PRERELEASE (python glider_prerelease.py, on the hub)
# until fish-pace-datasets#14 is released. v1's platform run took ~12 min with
# 16 jobs; gliders add ~7% rows. Shut the VM down when the log says so.
# Usage: ./vm_platform_glider.sh [n_jobs]
cd "$(dirname "$0")"
OUT=~/shared-public/chla-z/split-design
nohup bash -c "
  python run_platform.py --platforms argo ooi glider --out $OUT/runs/platform-glider --n-jobs ${1:-16} --repeats 5
  echo \"\$(date -u +%FT%TZ) all done; VM can be shut down\"
" >> "$OUT/vm-platform-glider.log" 2>&1 &
echo "started (pid $!); log: $OUT/vm-platform-glider.log"
