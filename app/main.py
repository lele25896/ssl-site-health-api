from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from app.checks import DomainError, check_domain

app = FastAPI(title="SSL & Site Health Monitor")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/check")
def check(domain: str):
    try:
        return check_domain(domain)
    except DomainError as e:
        raise HTTPException(400, str(e))
