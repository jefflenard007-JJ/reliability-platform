#!/usr/bin/env bash
# Chaos experiments against the local stack (docker compose) or a port-forwarded cluster.
# Usage: ./chaos/run_experiments.sh [latency|errors|kill|reset] [BASE_URL]
# Watch the effect live on the Grafana "shop-api — SLO & RED overview" dashboard.
set -euo pipefail

EXPERIMENT="${1:-}"
BASE_URL="${2:-http://localhost:8000}"

traffic() {
  # Background traffic so the SLIs have something to measure
  local seconds="$1"
  local end=$((SECONDS + seconds))
  while [ "$SECONDS" -lt "$end" ]; do
    curl -s -o /dev/null -X POST "$BASE_URL/orders" -H 'content-type: application/json' \
      -d '{"item":"widget","quantity":1}' || true
    curl -s -o /dev/null "$BASE_URL/orders" || true
    sleep 0.1
  done
}

set_chaos() {
  curl -fsS -X POST "$BASE_URL/chaos" -H 'content-type: application/json' -d "$1"
  echo
}

case "$EXPERIMENT" in
  latency)
    echo "Hypothesis: 400 ms of added latency triggers ShopApiLatencySLOBreach within ~5 minutes."
    set_chaos '{"latency_ms": 400, "error_rate": 0}'
    traffic 420
    ;;
  errors)
    echo "Hypothesis: a 20% error rate triggers ShopApiErrorBudgetFastBurn within ~3 minutes."
    set_chaos '{"latency_ms": 0, "error_rate": 0.2}'
    traffic 300
    ;;
  kill)
    echo "Hypothesis: killing the container fires ShopApiDown within ~1 minute; restart policy recovers it."
    docker kill reliability-platform-shop-api-1
    sleep 75
    docker start reliability-platform-shop-api-1
    ;;
  reset)
    set_chaos '{"latency_ms": 0, "error_rate": 0}'
    ;;
  *)
    echo "usage: $0 [latency|errors|kill|reset] [BASE_URL]"
    exit 1
    ;;
esac

echo "Done. Record what you observed in postmortems/ using the template."
