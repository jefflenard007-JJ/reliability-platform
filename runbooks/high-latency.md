# Runbook: shop-api high latency

**Alert:** `ShopApiLatencySLOBreach` (page) — more than 1% of requests slower than 300 ms for 5 minutes

## 1. Where is the time going?
- Grafana "Latency percentiles": is p50 also up (everything is slow) or only p99 (some requests)?
- By route: `topk(5, route:http_request_duration_seconds:p95_5m)`

## 2. Saturation checks
- CPU throttling: `rate(container_cpu_cfs_throttled_seconds_total{namespace="shop"}[5m])`
- In-flight requests: `sum(http_requests_in_flight{job="shop-api"})` — rising means requests are queueing.
- HPA at max replicas? `kubectl -n shop get hpa`

## 3. Dependencies and chaos
- Injected latency active? Panel "Active chaos faults" / `curl $BASE_URL/chaos`.
- Node pressure: `kubectl top nodes`, `kubectl describe node <node>` (look for MemoryPressure).

## 4. Mitigate
- Scale out: `kubectl -n shop scale deploy shop-api --replicas=4` (temporary; fix HPA settings in Git).
- Raise CPU limits in `values.yaml` if pods are throttled; commit so Argo CD applies it.
- Roll back a recent change if latency started with a deploy.
