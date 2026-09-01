"""API contract test. test_check_known_domain hits a real domain over the
network (this API's whole job is live network checks — there's nothing to
mock) — CI runners have outbound internet, same assumption the deployed
service depends on.
"""
from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_check_known_domain():
    r = client.get("/check", params={"domain": "example.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["domain"] == "example.com"
    assert body["ssl"]["valid"] is True
    assert body["ssl"]["days_until_expiry"] > 0
    assert body["uptime"]["reachable"] is True
    assert body["uptime"]["status_code"] == 200


def test_check_rejects_private_target():
    r = client.get("/check", params={"domain": "localhost"})
    assert r.status_code == 400


def test_check_unresolvable_domain():
    r = client.get("/check", params={"domain": "this-domain-does-not-exist-abc123xyz.invalid"})
    assert r.status_code == 400


def test_check_requires_proxy_secret_when_configured(monkeypatch):
    monkeypatch.setattr(main, "RAPIDAPI_PROXY_SECRET", "s3cret")

    r = client.get("/check", params={"domain": "example.com"})
    assert r.status_code == 403

    r = client.get(
        "/check",
        params={"domain": "example.com"},
        headers={"X-RapidAPI-Proxy-Secret": "wrong"},
    )
    assert r.status_code == 403

    r = client.get(
        "/check",
        params={"domain": "example.com"},
        headers={"X-RapidAPI-Proxy-Secret": "s3cret"},
    )
    assert r.status_code == 200
