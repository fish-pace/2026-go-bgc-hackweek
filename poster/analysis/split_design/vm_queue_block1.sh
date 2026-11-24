#!/usr/bin/env bash
# On the big VM: wait for the window-weights test to finish, then rerun block 1
# (hyperspectral, 5 repeats) on the QC'd data, so the VM can be shut down as soon
# as both are done (Eli, 2026-11-24). The pre-QC block 1 run was moved to
# runs/hyperspectral-preqc. Usage: ./vm_queue_block1.sh [n_jobs]
cd "$(dirname "$0")"
OUT=~/shared-public/chla-z/split-design
nohup bash -c "
  while pgrep -f run_window_weights.py > /dev/null; do sleep 60; done
  echo \"\$(date -u +%FT%TZ) window test done; starting block 1\"
  python run_hyperspectral.py --out $OUT/runs/hyperspectral --n-jobs ${1:-16} --repeats 5
  echo \"\$(date -u +%FT%TZ) block 1 done; VM can be shut down\"
" >> "$OUT/hyperspectral.log" 2>&1 &
echo "queued (pid $!); log: $OUT/hyperspectral.log"
