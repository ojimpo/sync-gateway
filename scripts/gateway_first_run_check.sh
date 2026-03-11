#!/usr/bin/env bash
set -euo pipefail

# First-run health/source/ingest/verify check for sync-gateway
# Usage:
#   ./scripts/gateway_first_run_check.sh [BASE_URL] [PAYLOAD_JSON]
# Examples:
#   ./scripts/gateway_first_run_check.sh
#   ./scripts/gateway_first_run_check.sh http://gateway.arigato-nas samples/bookmeter_first_run_payload.json

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BASE_URL="${1:-http://localhost:18000}"
PAYLOAD_PATH="${2:-$ROOT_DIR/samples/bookmeter_first_run_payload.json}"

if [[ -f "$ROOT_DIR/.env" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
fi

if [[ -z "${GATEWAY_API_KEY:-}" ]]; then
  echo "ERROR: GATEWAY_API_KEY is not set (.env)"
  exit 1
fi

if [[ ! -f "$PAYLOAD_PATH" ]]; then
  echo "ERROR: payload file not found: $PAYLOAD_PATH"
  exit 1
fi

auth_header=( -H "Authorization: Bearer ${GATEWAY_API_KEY}" )
json_header=( -H "Content-Type: application/json" )

echo "[1/5] Health check: ${BASE_URL}/healthz"
curl -fsS "${BASE_URL}/healthz" | jq .

echo "[2/5] Check source exists (bookmeter)"
source_count=$(curl -fsS "${BASE_URL}/api/v1/sources" | jq '[.[] | select(.slug=="bookmeter")] | length')

if [[ "$source_count" == "0" ]]; then
  echo "[3/5] Register source: bookmeter"
  register_code=$(curl -sS -o /tmp/gateway_register_source.json -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/sources/register" \
    "${json_header[@]}" "${auth_header[@]}" \
    -d '{"slug":"bookmeter","display_name":"読書メーター","description":"bookmeter.com collected records"}')
  if [[ "$register_code" != "201" && "$register_code" != "409" ]]; then
    echo "ERROR: source register failed (HTTP ${register_code})"
    cat /tmp/gateway_register_source.json
    exit 1
  fi
else
  echo "[3/5] Source already exists, skip register"
fi

echo "[4/5] Ingest payload: ${PAYLOAD_PATH}"
ingest_code=$(curl -sS -o /tmp/gateway_ingest.json -w "%{http_code}" \
  -X POST "${BASE_URL}/api/v1/ingest/events" \
  "${json_header[@]}" "${auth_header[@]}" \
  --data-binary "@${PAYLOAD_PATH}")

if [[ "$ingest_code" != "202" ]]; then
  echo "ERROR: ingest failed (HTTP ${ingest_code})"
  cat /tmp/gateway_ingest.json
  exit 1
fi
cat /tmp/gateway_ingest.json | jq .

echo "[5/5] Verify latest records (bookmeter, limit=20)"
curl -fsS "${BASE_URL}/api/v1/records?source=bookmeter&limit=20" | jq .

echo "DONE: first-run check completed"
