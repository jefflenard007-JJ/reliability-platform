# Runbook: shop-api high error rate

**Alerts:** `ShopApiErrorBudgetFastBurn` (page), `ShopApiErrorBudgetSlowBurn` (ticket)
**SLO:** 99.5% of requests succeed over 30 days (error budget 0.5%)

## 1. Confirm impact (2 minutes)
- Grafana → *shop-api — SLO & RED overview* → "Error ratio vs SLO burn thresholds".
- Which routes? `sum by (route, status) (rate(http_requests_total{job="shop-api",status=~"5.."}[5m]))`
- Is it all pods or one? `kubectl -n shop get pods -o wide` and compare restarts.

## 2. Check recent changes (most incidents follow a change)
- Argo CD: was there a sync in the last hour? `kubectl -n argocd get application shop-api`
- Git: `git log --oneline -5 -- helm/ app/`
- Is chaos active? `curl $BASE_URL/chaos` / panel "Active chaos faults".

## 3. Read the logs
- Grafana → Explore → Loki: `{service="shop-api", level="ERROR"} | json`
- Follow one failing `request_id` end to end.

## 4. Mitigate first, diagnose second
| Cause | Mitigation |
|---|---|
| Bad deploy | Roll back: revert the commit in Git, Argo CD syncs the previous version |
| One unhealthy pod | `kubectl -n shop delete pod <pod>` (the ReplicaSet replaces it) |
| Load spike | Check HPA: `kubectl -n shop get hpa`; raise `maxReplicas` if pinned |
| Chaos left on | `./chaos/run_experiments.sh reset` |

## 5. After recovery
- Confirm the 5m error ratio is back under the threshold.
- Open a postmortem from `postmortems/TEMPLATE.md` if the page fired.
