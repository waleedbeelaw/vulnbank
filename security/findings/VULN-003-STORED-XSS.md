# Finding VULN-003: Stored Cross-Site Scripting in Profile View

## Severity

**Medium** (CVSS 3.1 Base Score: **6.1 Medium**)

Stored XSS allows JavaScript execution in a victim's browser when they view a crafted profile. The lab uses a harmless `alert()` proof of concept; in production this class of flaw commonly leads to session abuse.

## CWE

**CWE-79: Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')**

Specifically: **CWE-80** (Improper Neutralization of Script-Related HTML Tags in a Web Page)

## OWASP Category

**OWASP Top 10 2021 - A03:2021 Injection (XSS)**  
**OWASP API Security Top 10 - API8:2023 Security Misconfiguration**

## Affected Component

| | |
|---|---|
| **Source endpoint** | `PUT /users/me/profile` |
| **Sink endpoint** | `GET /profile/<id>/view` |
| **File** | `app/routes/profile.py` |
| **Storage** | `users.display_name` column (`app/models.py`) |

## Description

Authenticated users can set an arbitrary `display_name` value that is persisted without sanitisation. When any client requests the HTML profile view, the stored value is embedded directly into the response body without HTML encoding, creating a stored XSS vulnerability.

### Data Flow

```
[Source]  PUT /users/me/profile  →  {"display_name": "<script>..."}
                ↓
[Storage] users.display_name column (PostgreSQL)
                ↓
[Sink]    GET /profile/<id>/view  →  f"<h1>{name}</h1>"  (unescaped HTML)
```

## Root Cause

**Source** - no input sanitisation:

```python
user.display_name = data.get("display_name", "")
```

**Sink** - f-string HTML construction without escaping:

```python
html = f"<html><body><h1>{name}</h1><p>Profile for user {user.username}</p></body></html>"
return html, 200, {"Content-Type": "text/html; charset=utf-8"}
```

The application treats attacker-controlled data as HTML markup rather than text content.

## Preconditions

- Attacker has a valid JWT (to set their own `display_name`)
- Victim visits `GET /profile/<attacker_user_id>/view` in a web browser

## Proof of Concept

**Step 1 - Store payload:**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/users/me/profile" -Method PUT `
  -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer <token>" } `
  -Body '{"display_name":"<script>alert(\"VulnBank XSS\")</script>"}'
```

**Step 2 - View profile (in browser or via request):**

```
http://127.0.0.1:5000/profile/1/view
```

## Observed Result

HTTP `200` with `Content-Type: text/html`. Response body contains the literal string:

```html
<h1><script>alert("VulnBank XSS")</script></h1>
```

In a browser, the JavaScript executes and displays an alert dialog.

## Expected Secure Result

The script tags should be HTML-encoded in the output:

```html
<h1>&lt;script&gt;alert("VulnBank XSS")&lt;/script&gt;</h1>
```

No JavaScript execution should occur.

## Impact

| Dimension | Impact |
|-----------|--------|
| **Confidentiality** | Low - potential access to page content/cookies depending on browser context |
| **Integrity** | Low - ability to modify page DOM, perform actions as victim |
| **Availability** | None |

This lab PoC uses `alert()` only. Stored XSS in fintech applications could enable session token theft, fraudulent actions, or phishing content injection.

## Risk

XSS in any customer-facing rendering path undermines trust in the platform. Even if the primary API is JSON-based, a single HTML endpoint without output encoding creates an exploitable browser-side attack surface.

## Recommended Remediation

1. **Encode all dynamic output** using `markupsafe.escape()` or Jinja2 auto-escaping templates
2. **Prefer JSON APIs** over raw HTML rendering where possible
3. **Content-Security-Policy** header as defence in depth: `Content-Security-Policy: default-src 'self'`
4. Optionally validate/sanitize `display_name` length and character set on input

```python
from markupsafe import escape
html = f"<html><body><h1>{escape(name)}</h1></body></html>"
```

## Verification

1. Store XSS payload via `PUT /users/me/profile`
2. Request `GET /profile/<id>/view`
3. Confirm `<script>` appears encoded, not executable
4. `tests/test_vulnerabilities.py::test_stored_xss_vulnerability_*` must fail (expect secure behaviour)

## CVSS v3.1

**Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N`  
**Base Score:** **6.1 (Medium)**

| Metric | Value | Rationale |
|--------|-------|-----------|
| AV:N | Network | Profile view accessible over HTTP |
| AC:L | Low | Straightforward stored XSS |
| PR:L | Low | Attacker needs account to store payload |
| UI:R | Required | Victim must visit profile page |
| S:C | Changed | XSS executes in victim browser context |
| C:L | Low | Limited data accessible to script |
| I:L | Low | DOM manipulation possible |
| A:N | None | No direct availability impact |

## Remediation

Replaced f-string HTML construction in `app/routes/profile.py` with Jinja2 templating via `render_template_string()`. Flask/Jinja2 auto-escaping HTML-encodes `display_name` and `username` at render time:

```python
html = render_template_string(
    PROFILE_TEMPLATE,
    name=name,
    username=user.username,
)
```

Input storage is unchanged - legitimate display names including `<`, `>`, quotes, and ampersands are stored as provided. Output encoding at the sink prevents script execution.

## Verification

The following regression tests confirm the fix:

- `tests/test_vulnerabilities.py::test_xss_remediation_payload_is_html_escaped` - `<script>alert(...)</script>` rendered as encoded text, not executable markup
- `tests/test_vulnerabilities.py::test_xss_remediation_normal_display_name_renders` - normal names display correctly (with encoding where needed)
- `tests/test_vulnerabilities.py::test_xss_remediation_quotes_and_special_characters_safe` - quotes and special characters handled safely

Manual retest: store XSS payload via `PUT /users/me/profile`, view via `GET /profile/<id>/view` - response contains `&lt;script&gt;...` not raw `<script>`.

## Status

**REMEDIATED**
