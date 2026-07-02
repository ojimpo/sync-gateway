#!/usr/bin/env bash
set -euo pipefail
cd /home/kouki/dev/sync-gateway
TS="$(date +%F_%H-%M-%S)"
LOG_DIR="/home/kouki/dev/sync-gateway/scripts/logs"
mkdir -p "$LOG_DIR"
OUT_LOG="$LOG_DIR/bookmeter_states_${TS}.log"

python3 /home/kouki/dev/sync-gateway/scripts/bookmeter_sync_states_slow.py \
  --user-id "1006219" \
  --gateway "http://localhost:18000" \
  --states "read,reading,wish,stacked" \
  --max-pages 3 \
  >> "$OUT_LOG" 2>&1

echo "done: $OUT_LOG"
