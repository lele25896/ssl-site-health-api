"""SSRF guard + normalization are pure/offline-testable — covered thoroughly
since a mistake here lets our server be used to probe internal network
services. check_domain() itself needs live network (real TLS handshake to a
real domain); that's exercised once via the API in test_api.py.
"""
import pytest

from app.checks import DomainError, _is_public_ip, normalize_domain


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("example.com", "example.com"),
        ("https://example.com", "example.com"),
        ("http://example.com/path?q=1", "example.com"),
        ("example.com:8443", "example.com"),
        ("  example.com  ", "example.com"),
    ],
)
def test_normalize_domain(raw, expected):
    assert normalize_domain(raw) == expected


def test_normalize_domain_rejects_empty():
    with pytest.raises(DomainError):
        normalize_domain("")


@pytest.mark.parametrize(
    "ip",
    ["127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1", "169.254.1.1", "0.0.0.0", "::1"],
)
def test_guard_rejects_non_public_ip(ip):
    assert _is_public_ip(ip) is False


@pytest.mark.parametrize("ip", ["93.184.216.34", "8.8.8.8", "2606:4700:4700::1111"])
def test_guard_allows_public_ip(ip):
    assert _is_public_ip(ip) is True
