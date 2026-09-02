# Pre-deploy status — 2026-09-02

Service: `ssl-site-health-api` · GCP project `site-health-api-178823` · region `europe-west1`

## Verdict

**Deployed 2026-09-02.** Service URL: `https://ssl-site-health-api-74615653496.europe-west1.run.app`, revision `ssl-site-health-api-00001-p8s`. Smoke-tested `/check?domain=example.com` — 200 OK.

## Checks run

| Check | Result |
|---|---|
| `pytest` | 22 passed |
| `pip-audit` (runtime + dev) | 0 known vulnerabilities |
| `terraform fmt -check` / `validate` | clean |
| Cloud Run service | none yet (expected) |
| Artifact Registry image | `.../ssl-site-health-api:latest` pushed 2026-09-01 |
| GitHub Actions secrets | none — CI terraform/deploy jobs will fail until WIF secrets set |

## Findings and fixes applied (uncommitted)

| # | Finding | Fix |
|---|---|---|
| 1 | SSRF guard used `is_private`, which lets 100.64.0.0/10 (CGNAT, GCP internal) through | `_is_public_ip` now returns `ip.is_global`; test adds `100.64.1.1`, `::ffff:10.0.0.1` |
| 2 | `getaddrinfo` could return AAAA first; Cloud Run egress is IPv4-only | resolve with `socket.AF_INET` |
| 3 | fastapi 0.115.5 → starlette 0.41.3 with 8 CVEs (Host/path spoofing, multipart + Range DoS) | `fastapi==0.141.1` (starlette 1.6.0) |
| 4 | pytest 8.3.3 PYSEC-2026-1845 (dev only) | `pytest==9.0.3` |
| 5 | No instance cap on public endpoint, small budget | `--max-instances 2` in README deploy cmd; `scaling { max_instance_count = 2 }` in Terraform |
| 6 | `terraform.tfvars` project_id was placeholder | set to `site-health-api-178823` (from previous session) |

## RapidAPI wiring (done 2026-09-02)

- `app/main.py`: `/check` now requires `X-RapidAPI-Proxy-Secret` to match `RAPIDAPI_PROXY_SECRET` env var (constant-time compare); unset env var = check disabled (local/CI unaffected). `/health` stays open. Test added in `tests/test_api.py`.
- Cloud Run env var `RAPIDAPI_PROXY_SECRET` set to RapidAPI's actual proxy secret (Studio → Hub Listing → Gateway → Firewall Settings), not a self-generated one — revision `ssl-site-health-api-00003-m4z`.
- Rapid Studio (`api_22018346-fc29-432a-9cd7-fdd39fe6473c`): Base URL set to the Cloud Run URL (General tab), Health Check URL set to `/health`, one REST endpoint defined (`GET /check`, required query param `domain`).
- Verified end-to-end via the live gateway host `ssl-site-health-monitor.p.rapidapi.com` with a real `X-RapidAPI-Key` — 200 OK with correct payload. Direct Cloud Run calls without the proxy-secret header now get 403.

## Known, deliberately deferred

- DNS resolution has no timeout (socket timeout applies after connect). MVP-acceptable.
- GitHub Actions pinned by major tag, not SHA.
- No response cache (`ponytail:` note in `app/checks.py`).

## Next steps

1. ~~Commit these changes and push~~ — done (commit `0a767b5`, pushed to `origin/master`).
2. ~~Rebuild + push image with fixes 1–3~~ — done, digest `sha256:a7468cc5d6...`.
3. ~~Deploy~~ — done, `ssl-site-health-api-00001-p8s` serving 100% traffic.
4. ~~Wire into RapidAPI Studio + add proxy-secret check~~ — done, see above.
5. `terraform import` bucket, artifact repo, Cloud Run service; set repo secrets `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT`, `GCP_PROJECT_ID`.
6. Finish Hub Listing (logo, long description) and Monetize tab (free 15/day → Pro $4.99 → Ultra $9.99), then submit for review/publish to Hub.
