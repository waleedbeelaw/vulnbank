# VulnBank - Vulnerability Remediation Summary

Step 8 remediated all four intentional vulnerabilities identified in the Step 7 AppSec assessment. Each fix addresses the root cause rather than hiding symptoms in tests or UI.

## Remediation Table

| Finding | Root Cause | Remediation | Regression Test | Status |
|---------|------------|-------------|-----------------|--------|
| VULN-001 | Ownership check removed from `GET /accounts/<id>`; any authenticated user could read any account by ID | Restored object-level authorisation: compare `account.user_id` to JWT subject and return HTTP 403 when they differ | `tests/test_auth.py::test_alice_cannot_access_bob_account`, `tests/test_vulnerabilities.py::test_idor_remediation_*` | Remediated |
| VULN-002 | User input concatenated into raw SQL via f-string in `GET /search/users` | Replaced with SQLAlchemy ORM filters using `ilike()` and bound pattern values; empty queries return `[]` | `tests/test_vulnerabilities.py::test_sql_injection_remediation_*` | Remediated |
| VULN-003 | Stored `display_name` rendered into HTML via unescaped f-string in `GET /profile/<id>/view` | Switched to `render_template_string()` with Jinja2 auto-escaping so user data is HTML-encoded at output | `tests/test_vulnerabilities.py::test_xss_remediation_*` | Remediated |
| VULN-004 | Insufficient-funds check gated behind `amount >= £1000` micro-transfer threshold | Enforce `source.balance < amount` for every transfer amount before debiting accounts | `tests/test_transactions.py::test_insufficient_funds_rejected`, `tests/test_vulnerabilities.py::test_business_logic_remediation_*` | Remediated |

## Why Each Remediation Is Effective

### VULN-001 - IDOR / BOLA

Authentication alone cannot protect object-specific resources. Restoring the ownership check ensures the server validates that the requested account belongs to the authenticated user before serialising any account data. A 403 response prevents information leakage for accounts that exist but belong to another user; 404 is preserved for genuinely missing accounts.

### VULN-002 - SQL Injection

SQLAlchemy ORM filters treat user input as data values, not executable SQL structure. The `ilike()` pattern is passed as a bound parameter, so metacharacters such as `'`, `OR`, and `%` cannot alter query logic. The `' OR '1'='1` payload is searched literally and matches no usernames or emails.

### VULN-003 - Stored XSS

Jinja2 auto-escaping converts HTML metacharacters (`<`, `>`, `"`, `'`, `&`) to entity references at render time. Stored payloads remain in the database unchanged (preserving legitimate names with special characters) but are emitted as harmless text in the HTML response, preventing script execution in the browser.

### VULN-004 - Business Logic

Removing the micro-transfer threshold restores the financial invariant: source balance must always cover the transfer amount. The check runs inside the existing locked database transaction before any balance mutation or record creation, preserving atomicity and leaving balances unchanged when validation fails.

## Additional Changes

- Removed `VULNERABLE_LAB` xfail markers from `tests/conftest.py` - secure baseline tests now run normally.
- Updated `tests/test_vulnerabilities.py` from vulnerability demonstrations to remediation regression tests.
- Original finding reports under `security/findings/` retain their assessment content; each now includes **Remediation**, **Verification**, and **Status** sections documenting the fix.

## Verification Command

```powershell
.venv\Scripts\activate
pytest -v
```

Expected result after Step 8: all tests pass with no xfails related to the four intentional vulnerabilities.
