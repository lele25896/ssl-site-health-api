"""SSL certificate + uptime/response-time check for a domain, in one TLS
connection.

ponytail: single request, no caching — every call re-checks live. Add an
in-memory TTL cache (e.g. cachetools) if request volume makes rechecking
the same domain on every call wasteful.
"""
import http.client
import ipaddress
import socket
import ssl
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

TIMEOUT_SECONDS = 5


class DomainError(Exception):
    """Domain failed validation, resolution, or the SSRF guard."""


def normalize_domain(raw: str) -> str:
    raw = raw.strip()
    if "//" not in raw:
        raw = "//" + raw
    host = urlparse(raw).hostname
    if not host:
        raise DomainError("invalid domain")
    return host


def _is_public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return not (
        addr.is_private or addr.is_loopback or addr.is_link_local
        or addr.is_reserved or addr.is_multicast or addr.is_unspecified
    )


def _resolve_and_guard(domain: str) -> str:
    """Resolve to an IP and reject private/loopback/link-local targets.

    Domain is untrusted user input driving an outbound connection from our
    server — without this an attacker can probe internal network services
    (SSRF) via our API as a proxy. Both checks below connect to this
    resolved IP directly (not the hostname again) so a second DNS lookup
    with a rebound answer can't slip a private address past the guard.
    """
    try:
        ip = socket.getaddrinfo(domain, 443)[0][4][0]
    except socket.gaierror as e:
        raise DomainError(f"could not resolve domain: {e}") from None

    if not _is_public_ip(ip):
        raise DomainError("domain resolves to a non-public address")
    return ip


def check_domain(raw_domain: str) -> dict:
    domain = normalize_domain(raw_domain)
    ip = _resolve_and_guard(domain)

    result = {"domain": domain, "ssl": None, "uptime": None}

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((ip, 443), timeout=TIMEOUT_SECONDS) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                expires_at = datetime.strptime(
                    cert["notAfter"], "%b %d %H:%M:%S %Y %Z"
                ).replace(tzinfo=timezone.utc)
                issuer = dict(x[0] for x in cert.get("issuer", []))
                result["ssl"] = {
                    "valid": True,
                    "issuer": issuer.get("organizationName", issuer.get("commonName", "unknown")),
                    "expires_at": expires_at.isoformat(),
                    "days_until_expiry": (expires_at - datetime.now(timezone.utc)).days,
                }

                request = (
                    f"HEAD / HTTP/1.1\r\nHost: {domain}\r\n"
                    "User-Agent: ssl-site-health-monitor/1.0\r\nConnection: close\r\n\r\n"
                )
                start = time.perf_counter()
                ssock.sendall(request.encode())
                resp = http.client.HTTPResponse(ssock)
                resp.begin()
                elapsed_ms = (time.perf_counter() - start) * 1000
                result["uptime"] = {
                    "reachable": True,
                    "status_code": resp.status,
                    "response_time_ms": round(elapsed_ms, 1),
                }
    except (socket.timeout, socket.error, ssl.SSLError, OSError) as e:
        if result["ssl"] is None:
            result["ssl"] = {"valid": False, "error": str(e)}
        else:
            result["uptime"] = {"reachable": False, "error": str(e)}

    return result
