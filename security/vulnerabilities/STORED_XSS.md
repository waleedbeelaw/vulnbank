# Stored Cross-Site Scripting (XSS)

## Severity

**Medium**

User-supplied `display_name` content is stored in the database and later rendered as HTML without encoding. A script payload persists and executes when another user (or the same user) views the profile page.

## Description

The profile update endpoint accepts arbitrary `display_name` content. The profile view endpoint embeds that value directly into an HTML response. This creates a stored XSS vulnerability with a clear source → storage → sink path.

## Affected Endpoints

- `PUT /users/me/profile` — source (stores user input)
- `GET /profile/<id>/view` — sink (renders stored value as HTML)

## Root Cause

**Source:** `app/routes/profile.py` — `update_profile()` saves `display_name` without sanitisation.

**Storage:** `users.display_name` column in PostgreSQL/SQLite.

**Sink:** `view_profile()` builds HTML with an f-string:

```python
html = f"<html><body><h1>{name}</h1>...</body></html>"
return html, 200, {"Content-Type": "text/html; charset=utf-8"}
```

No HTML escaping is applied before rendering.

## Preconditions

- Attacker has a valid JWT to update their own profile
- Victim visits `GET /profile/<attacker_id>/view` in a browser

## Proof of Concept

```http
PUT /users/me/profile
Authorization: Bearer <token>
Content-Type: application/json

{"display_name": "<script>alert(\"VulnBank XSS\")</script>"}
```

```http
GET /profile/1/view
Host: 127.0.0.1:5000
```

The response body contains the unescaped `<script>` tag. In a browser, the script would execute.

This lab uses a harmless `alert()` proof of concept only.

## Impact

- Execute JavaScript in the victim's browser context
- Demonstrate how stored user content can become an execution sink
- In real applications, XSS can lead to session abuse — this lab does not implement cookie theft payloads

## OWASP Category

- [OWASP Top 10 — A03:2021 Injection (XSS)](https://owasp.org/Top10/A03_2021-Injection/)
- [OWASP API Security Top 10 — API8:2023 Security Misconfiguration](https://owasp.org/API-Security/editions/2023/en/0xa8-security-misconfiguration/)

## Remediation

1. **Encode output:** use `markupsafe.escape()` or Jinja2 auto-escaping when rendering HTML
2. **Content-Type:** prefer JSON APIs over raw HTML rendering where possible
3. **Input validation:** optionally restrict `display_name` length and character set
4. **CSP:** add Content-Security-Policy headers as defence in depth

Example fix:

```python
from markupsafe import escape
html = f"<html><body><h1>{escape(name)}</h1></body></html>"
```

## Regression Test

`tests/test_vulnerabilities.py::test_stored_xss_vulnerability_renders_unescaped_script` must show the payload is **escaped** after remediation (raw `<script>` must not appear in HTML output).
