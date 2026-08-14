#!/usr/bin/env bash
set -e

# Pre-flight check for order_status_history_lag_watcher
# (airflow/dags/order_status_history_lag_watcher.py) -- run this
# before manually triggering/unpausing that DAG, not after. Exists
# because of a real incident (2026-08-13): manually re-triggering the
# watcher right after a live test still had that test's own
# order_status_history writes inside the detection window, so the
# watcher fired immediately and ran a real, unwanted
# marketplace_batch_pipeline (~10min of real Databricks compute,
# wasted -- see docs/architecture/roadmap-next-steps.md).
#
# Mirrors the DAG's own query construction: raw instant value of
# mdp_bronze_records_written_total{entity="order_status_history"}
# compared against the order_status_history_lag_watcher_last_consumed_count
# Variable (watermark, added 2026-08-14 after a second, worse incident --
# the pre-watermark window-based version fired the batch pipeline 188
# times in 30 minutes, 2 of which reached real Databricks compute; see
# docs/architecture/roadmap-next-steps.md). If that DAG's query logic
# ever changes, update this script to match, or it'll give a false
# reading.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

LAST_CONSUMED=$(docker exec mdp-airflow-scheduler \
  airflow variables get order_status_history_lag_watcher_last_consumed_count \
  2>/dev/null | tail -1)

if ! [[ "$LAST_CONSUMED" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
  LAST_CONSUMED=0
fi

QUERY='mdp_bronze_records_written_total{entity="order_status_history"}'

RESULT=$(docker exec mdp-airflow-scheduler curl -s \
  --data-urlencode "query=${QUERY}" \
  "http://prometheus:9090/api/v1/query")

CURRENT_VALUE=$(echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('data', {}).get('result', [])
print(results[0]['value'][1] if results else '')
")

echo "Last consumed (watermark): ${LAST_CONSUMED}"
echo "Current raw value:         ${CURRENT_VALUE:-<no data>}"
echo "Query:          ${QUERY}"
echo ""

DIFFERS=$(python3 -c "
current = '${CURRENT_VALUE}'
last = '${LAST_CONSUMED}'
print('1' if current and float(current) != float(last) else '0')
")

if [ "$DIFFERS" = "1" ]; then
  echo "!! WOULD FIRE IMMEDIATELY if triggered/unpaused now."
  echo "!! Current value differs from the last-consumed watermark --"
  echo "!! triggering now will run a REAL marketplace_batch_pipeline,"
  echo "!! including real Databricks compute."
  exit 1
else
  echo "OK: current value matches the last-consumed watermark -- nothing new."
  echo "Safe to trigger/unpause -- it will only fire on genuinely new activity."
  exit 0
fi
