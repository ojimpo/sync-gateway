#!/usr/bin/env bash
set -euo pipefail
cd /home/kouki/dev/sync-gateway
TS="$(date +%F_%H-%M-%S)"
LOG_DIR="/home/kouki/dev/sync-gateway/scripts/logs"
mkdir -p "$LOG_DIR"
OUT_LOG="$LOG_DIR/filmarks_delta_${TS}.log"

python3 /home/kouki/dev/sync-gateway/scripts/filmarks_sync_delta.py \
  --user-slug "ojimpo" \
  --gateway "http://localhost:18000" \
  --max-pages 3 \
  >> "$OUT_LOG" 2>&1

echo "done: $OUT_LOG"
