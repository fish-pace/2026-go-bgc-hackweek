#!/usr/bin/env bash
# Start the OOI window-weighting test (Eli, 2026-11-24) in the background on the big VM.
# A script instead of a pasted one-liner: terminals wrap long pasted lines.
# Rerunning skips finished units. Usage: ./vm_window_weights.sh [n_jobs]
cd "$(dirname "$0")"
OUT=~/shared-public/chla-z/split-design
nohup python run_window_weights.py \
  --out "$OUT/runs/window-weights" \
  --n-jobs "${1:-16}" \
  >> "$OUT/window-weights.log" 2>&1 &
echo "started pid $!; log: $OUT/window-weights.log"
