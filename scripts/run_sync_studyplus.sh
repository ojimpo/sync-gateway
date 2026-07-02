#!/usr/bin/env bash
set -euo pipefail
cd /home/kouki/dev/sync-gateway
TS="$(date +%F_%H-%M-%S)"
LOG_DIR="/home/kouki/dev/sync-gateway/scripts/logs"
mkdir -p "$LOG_DIR"
OUT_LOG="$LOG_DIR/studyplus_${TS}.log"

python3 /home/kouki/dev/sync-gateway/scripts/studyplus_sync.py \
  --gateway "http://localhost:18000" \
  "$@" \
  >> "$OUT_LOG" 2>&1

echo "done: $OUT_LOG"
