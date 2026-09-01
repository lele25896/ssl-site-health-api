# SSL & Site Health Monitor

Single-call API: SSL certificate expiry, uptime, and response time for a
domain, in one TLS connection. Same deploy pattern as the
[Defect Classifier API](https://github.com/lele25896/defect-classifier-api)
(FastAPI + Docker + Terraform + GitHub Actions CI/CD with Workload Identity
Federation) — stdlib-only checker instead of an ML model, so no torch, no
GPU, no model files.

## Setup

```
pip install -r requirements-dev.txt
```

## Run

```
uvicorn app.main:app --reload
```

- `GET /health` — liveness
- `GET /check?domain=example.com` —
  ```json
  {
    "domain": "example.com",
    "ssl": {"valid": true, "issuer": "...", "expires_at": "...", "days_until_expiry": 123},
    "uptime": {"reachable": true, "status_code": 200, "response_time_ms": 87.3}
  }
  ```

Domain is resolved once, guarded against private/loopback/link-local
targets (SSRF — this API makes outbound connections to whatever the caller
supplies), then both the cert and the HEAD-request timing come off the same
pinned-IP TLS connection.

## Test

```
pytest tests/
```

`tests/test_checks.py` covers the SSRF guard and domain normalization
offline. `tests/test_api.py` hits a real domain (`example.com`) — this API's
job is live checks, there's nothing meaningful to mock.

## Deploy (manual, once)

```
gcloud projects create PROJECT_ID
gcloud config set project PROJECT_ID
# link billing in the console, then:
gcloud services enable run.googleapis.com artifactregistry.googleapis.com monitoring.googleapis.com
gsutil mb -l europe-west1 gs://ssl-site-health-tfstate
gcloud artifacts repositories create ssl-site-health-api --repository-format=docker --location=europe-west1
docker build -t europe-west1-docker.pkg.dev/PROJECT_ID/ssl-site-health-api/ssl-site-health-api:latest .
docker push europe-west1-docker.pkg.dev/PROJECT_ID/ssl-site-health-api/ssl-site-health-api:latest
gcloud run deploy ssl-site-health-api --image europe-west1-docker.pkg.dev/PROJECT_ID/ssl-site-health-api/ssl-site-health-api:latest --region europe-west1 --allow-unauthenticated --memory 256Mi --max-instances 2
```

Then set `terraform/terraform.tfvars` `project_id`, `terraform import` the
manually-created resources, and wire repo secrets `WIF_PROVIDER`,
`WIF_SERVICE_ACCOUNT`, `GCP_PROJECT_ID` for CI.

## CV line

> Deployed a stdlib-only (ssl/socket) domain health checker as a
> containerized FastAPI REST service on **GCP Cloud Run**, with
> **GitHub Actions CI/CD** and **Terraform** IaC. Free-tier cost (~€0).
