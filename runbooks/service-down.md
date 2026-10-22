# Runbook: shop-api down

**Alert:** `ShopApiDown` (page) — Prometheus cannot scrape the service for 1 minute

1. Pods: `kubectl -n shop get pods` — look for `CrashLoopBackOff`, `ImagePullBackOff`, `Pending`.
2. Crash loop: `kubectl -n shop logs <pod> --previous` and `kubectl -n shop describe pod <pod>` (check `OOMKilled`).
3. Image pull: confirm the tag in `helm/shop-api/values.yaml` exists in the GitLab container registry.
4. Pending: `kubectl describe pod` → insufficient CPU/memory → check node group size in Terraform.
5. Service and endpoints: `kubectl -n shop get endpoints shop-api` — empty means readiness probes are failing.
6. Mitigate: roll back the last commit; Argo CD restores the previous working version.
