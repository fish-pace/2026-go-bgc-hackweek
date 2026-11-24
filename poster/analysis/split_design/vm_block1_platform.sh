#!/usr/bin/env bash
# On the big VM, one session (Eli, 2026-11-24): rerun block 1 (hyperspectral) on
# the QC'd data, then the platform-input test (run_platform.py). About 45 min
# with 16 jobs; shut the VM down when the log says so.
# Usage: ./vm_block1_platform.sh [n_jobs]
cd "$(dirname "$0")"
OUT=~/shared-public/chla-z/split-design
nohup bash -c "
  python run_hyperspectral.py --out $OUT/runs/hyperspectral --n-jobs ${1:-16} --repeats 5
  echo \"\$(date -u +%FT%TZ) block 1 done; starting platform test\"
  python run_platform.py --out $OUT/runs/platform --n-jobs ${1:-16} --repeats 5
  echo \"\$(date -u +%FT%TZ) all done; VM can be shut down\"
" >> "$OUT/vm-block1-platform.log" 2>&1 &
echo "started (pid $!); log: $OUT/vm-block1-platform.log"
