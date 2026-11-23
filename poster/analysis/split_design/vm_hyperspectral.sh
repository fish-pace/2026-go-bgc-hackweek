#!/usr/bin/env bash
# Start the block 1 (#10) hyperspectral run in the background on the big VM.
# A script instead of a pasted one-liner: terminals wrap long pasted lines.
# Rerunning skips finished units.
cd "$(dirname "$0")"
OUT=~/shared-public/chla-z/split-design
nohup python run_hyperspectral.py \
  --out "$OUT/runs/hyperspectral" \
  --n-jobs "${1:-16}" \
  > "$OUT/hyperspectral.log" 2>&1 &
echo "started pid $!; log: $OUT/hyperspectral.log"
