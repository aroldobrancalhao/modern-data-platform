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
# wasted -- see docs/architecture/roadmap-next-steps.md). This script
# runs the exact same query the watcher would, against the same
# Prometheus instance, so you find out *before* triggering instead of
# after a real pipeline is already running.
#
# Mirrors the DAG's own query construction (mdp_bronze_
# records_written_total{entity="order_status_history"}, window = 2x
# the current poke_interval Variable) -- if that DAG's query logic
# ever changes, update this script to match, or it'll give a false
# reading.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

POKE_INTERVAL_SECONDS=$(docker exec mdp-airflow-scheduler \
  airflow variables get order_status_history_lag_watcher_poke_interval_seconds \
  2>/dev/null | tail -1)

if ! [[ "$POKE_INTERVAL_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "Could not read the poke_interval Variable (got: '$POKE_INTERVAL_SECONDS')." >&2
  echo "Defaulting to the DAG's own fallback, 3600s -- check manually if unsure." >&2
  POKE_INTERVAL_SECONDS=3600
fi

WINDOW_SECONDS=$((POKE_INTERVAL_SECONDS * 2))

QUERY="increase(mdp_bronze_records_written_total{entity=\"order_status_history\"}[${WINDOW_SECONDS}s]) > 0"

RESULT=$(docker exec mdp-airflow-scheduler curl -s \
  --data-urlencode "query=${QUERY}" \
  "http://prometheus:9090/api/v1/query")

MATCH_COUNT=$(echo "$RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(len(data.get('data', {}).get('result', [])))
")

echo "Poke interval:  ${POKE_INTERVAL_SECONDS}s"
echo "Window checked: ${WINDOW_SECONDS}s (2x poke interval, same as the DAG)"
echo "Query:          ${QUERY}"
echo ""

if [ "$MATCH_COUNT" -gt 0 ]; then
  echo "!! WOULD FIRE IMMEDIATELY if triggered/unpaused now."
  echo "!! Recent order_status_history writes are still inside the detection"
  echo "!! window -- triggering now will run a REAL marketplace_batch_pipeline,"
  echo "!! including real Databricks compute. Wait for the window to age past"
  echo "!! the recent activity, or confirm that's actually what you want."
  exit 1
else
  echo "OK: no recent order_status_history writes in the window."
  echo "Safe to trigger/unpause -- it will only fire on genuinely new activity."
  exit 0
fi
