import os
import secrets

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse

from app.checks import DomainError, check_domain

app = FastAPI(title="SSL & Site Health Monitor")

# Set on the Cloud Run service once wired into RapidAPI (Studio > Security
# tab). Unset = check disabled, so local dev/tests hit /check unauthenticated.
RAPIDAPI_PROXY_SECRET = os.environ.get("RAPIDAPI_PROXY_SECRET")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/check")
def check(domain: str, x_rapidapi_proxy_secret: str | None = Header(default=None)):
    if RAPIDAPI_PROXY_SECRET and not (
        x_rapidapi_proxy_secret
        and secrets.compare_digest(x_rapidapi_proxy_secret, RAPIDAPI_PROXY_SECRET)
    ):
        raise HTTPException(403, "missing or invalid proxy secret")
    try:
        return check_domain(domain)
    except DomainError as e:
        raise HTTPException(400, str(e))
