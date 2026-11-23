#!/usr/bin/env bash
# Start the block 1 (#10) hyperspectral run in the background on the big VM.
# A script instead of a pasted one-liner: terminals wrap long pasted lines.
# Rerunning skips finished units, so going from 3 to 5 repeats runs only r3 and r4.
# 5 repeats to match the leakage block and the Methods text (Eli, 2026-11-23).
# Usage: ./vm_hyperspectral.sh [n_jobs] [repeats]
cd "$(dirname "$0")"
OUT=~/shared-public/chla-z/split-design
nohup python run_hyperspectral.py \
  --out "$OUT/runs/hyperspectral" \
  --n-jobs "${1:-16}" \
  --repeats "${2:-5}" \
  >> "$OUT/hyperspectral.log" 2>&1 &
echo "started pid $!; log: $OUT/hyperspectral.log"
