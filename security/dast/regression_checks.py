"""Authenticated dynamic security regression checks against a running VulnBank instance.

OWASP ZAP handles general unauthenticated crawling and passive scanning.
This script verifies remediated security properties that require JWT-authenticated
API flows and are awkward to express purely in ZAP automation.

Run only against localhost in CI or local DAST environments.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import quote

import jwt

BASE_URL = os.environ.get("DAST_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
CI_JWT_SECRET = os.environ.get(
    "DAST_JWT_SECRET_KEY",
    "ci-dast-only-secret-not-for-production-use!",
)

ALICE = {
    "email": "dast-alice@example.com",
    "password": "dast-example-password",
}
BOB = {
    "email": "dast-bob@example.com",
    "password": "dast-example-password",
}
XSS_USER = {
    "username": "dast_xss_user",
    "email": "dast-xss@example.com",
    "password": "dast-example-password",
}
XSS_PAYLOAD = '<script>alert("VulnBank XSS")</script>'


class DastCheckError(Exception):
    """Raised when a dynamic security check fails."""


def _request(method: str, path: str, *, headers=None, body=None):
    url = f"{BASE_URL}{path}"
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _json(method: str, path: str, *, headers=None, body=None):
    status, content = _request(method, path, headers=headers, body=body)
    if not content:
        return status, None
    return status, json.loads(content.decode("utf-8"))


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(email: str, password: str) -> str:
    status, payload = _json("POST", "/login", body={"email": email, "password": password})
    if status != 200 or not payload or "access_token" not in payload:
        raise DastCheckError("Failed to obtain JWT via /login")
    return payload["access_token"]


def _user_id_from_token(token: str) -> int:
    payload = jwt.decode(token, CI_JWT_SECRET, algorithms=["HS256"])
    return int(payload["sub"])


def _first_account_id(token: str, user_id: int) -> int:
    status, payload = _json(
        "GET",
        f"/users/{user_id}/accounts",
        headers=_auth_header(token),
    )
    if status != 200 or not payload:
        raise DastCheckError("Failed to list user accounts")
    return payload[0]["id"]


def check_health() -> None:
    status, payload = _json("GET", "/health")
    if status != 200 or payload.get("status") != "healthy":
        raise DastCheckError("GET /health did not return healthy status")


def check_unauthenticated_account_access_rejected() -> None:
    status, payload = _json("GET", "/accounts/1")
    if status != 401 or payload.get("error") != "Authentication required":
        raise DastCheckError("Unauthenticated GET /accounts/<id> was not rejected with 401")


def check_invalid_jwt_rejected() -> None:
    status, payload = _json(
        "GET",
        "/accounts/1",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )
    if status != 401 or payload.get("error") != "Authentication required":
        raise DastCheckError("Invalid JWT was not rejected with 401")


def check_idor_remediation() -> None:
    alice_token = _login(ALICE["email"], ALICE["password"])
    bob_token = _login(BOB["email"], BOB["password"])

    bob_user_id = _user_id_from_token(bob_token)
    bob_account_id = _first_account_id(bob_token, bob_user_id)

    status, payload = _json(
        "GET",
        f"/accounts/{bob_account_id}",
        headers=_auth_header(alice_token),
    )
    if status != 403 or payload.get("error") != "Forbidden":
        raise DastCheckError("IDOR remediation failed: cross-user account access not blocked")


def check_sql_injection_remediation() -> None:
    query = quote("' OR '1'='1")
    status, payload = _json("GET", f"/search/users?q={query}")
    if status != 200 or not isinstance(payload, list):
        raise DastCheckError("SQL injection check could not query /search/users")
    if len(payload) >= 2:
        raise DastCheckError("SQL injection PoC returned multiple users")


def check_xss_remediation() -> None:
    status, user = _json("POST", "/users", body=XSS_USER)
    if status != 201:
        raise DastCheckError("Failed to create user for XSS check")

    token = _login(XSS_USER["email"], XSS_USER["password"])
    status, _ = _json(
        "PUT",
        "/users/me/profile",
        headers=_auth_header(token),
        body={"display_name": XSS_PAYLOAD},
    )
    if status != 200:
        raise DastCheckError("Failed to store display_name for XSS check")

    status, body = _request("GET", f"/profile/{user['id']}/view")
    html = body.decode("utf-8")
    if status != 200:
        raise DastCheckError("Profile view did not return 200")
    if XSS_PAYLOAD in html or "<script>" in html:
        raise DastCheckError("Stored XSS payload was not HTML-encoded in profile view")
    if "&lt;script&gt;" not in html:
        raise DastCheckError("Expected encoded script tags in profile view")


def check_insufficient_funds_remediation() -> None:
    alice_token = _login(ALICE["email"], ALICE["password"])
    bob_token = _login(BOB["email"], BOB["password"])

    alice_account_id = _first_account_id(alice_token, _user_id_from_token(alice_token))
    bob_account_id = _first_account_id(bob_token, _user_id_from_token(bob_token))

    status, payload = _json(
        "POST",
        "/transactions",
        headers=_auth_header(alice_token),
        body={
            "from_account_id": alice_account_id,
            "to_account_id": bob_account_id,
            "amount": "500.00",
            "currency": "GBP",
        },
    )
    if status != 400 or payload.get("error") != "insufficient funds":
        raise DastCheckError("Insufficient-funds bypass still succeeds or wrong error returned")


def check_unsupported_method() -> None:
    status, _ = _request("DELETE", "/health")
    if status != 405:
        raise DastCheckError("Unsupported DELETE /health did not return 405")


def main() -> int:
    checks = [
        ("health", check_health),
        ("unauthenticated account access", check_unauthenticated_account_access_rejected),
        ("invalid JWT", check_invalid_jwt_rejected),
        ("IDOR remediation", check_idor_remediation),
        ("SQL injection remediation", check_sql_injection_remediation),
        ("stored XSS remediation", check_xss_remediation),
        ("insufficient funds remediation", check_insufficient_funds_remediation),
        ("unsupported HTTP method", check_unsupported_method),
    ]

    failures: list[str] = []
    for name, check in checks:
        try:
            check()
            print(f"PASS: {name}")
        except DastCheckError as exc:
            failures.append(f"{name}: {exc}")
            print(f"FAIL: {name}: {exc}", file=sys.stderr)
        except Exception as exc:  # pragma: no cover
            failures.append(f"{name}: unexpected error: {exc}")
            print(f"FAIL: {name}: unexpected error: {exc}", file=sys.stderr)

    if failures:
        print(f"\nDAST regression checks failed ({len(failures)}):", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(f"\nAll {len(checks)} DAST regression checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
