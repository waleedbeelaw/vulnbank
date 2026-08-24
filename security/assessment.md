# VulnBank Application Security Assessment

> **Historical document:** This assessment reflects the **`vulnerable-lab` branch at Step 7** (August 2026). Test counts and vulnerability status below are frozen at assessment time. Current state: all four findings remediated; **125 pytest tests** pass. See [remediation.md](remediation.md) and [threat-model.md](threat-model.md).

**Branch:** `vulnerable-lab`  
**Assessment date:** 24 August 2026  
**Assessor role:** Application Security Engineering review  
**Scope:** Local VulnBank REST API (Flask, PostgreSQL, JWT)  
**Out of scope:** Production deployment, external infrastructure, destructive exploitation

---

## Executive Summary

This assessment evaluates the intentionally vulnerable VulnBank fintech API running on the `vulnerable-lab` branch. The review combined **security code review**, **automated regression testing**, and **structured manual API test cases** against authentication, authorisation, input handling, database access, HTML rendering, and transaction business logic.

### Scope

- All REST endpoints exposed by the Flask application
- Authentication middleware (`app/auth.py`)
- Account, user, transaction, search, and profile routes
- Configuration and secrets handling (`app/config.py`, environment variables)
- Existing pytest suite (90 tests: 88 passed, 6 expected failures on this branch)

### Confirmed Findings

| ID | Title | Severity | CVSS 3.1 |
|----|-------|----------|----------|
| VULN-001 | Broken Object Level Authorization on account retrieval | High | 6.5 (Medium) |
| VULN-002 | SQL injection in user search | Medium | 5.3 (Medium) |
| VULN-003 | Stored cross-site scripting in profile view | Medium | 6.1 (Medium) |
| VULN-004 | Micro-transfer solvency bypass | High | 7.1 (High) |

**Total:** 4 confirmed vulnerabilities  
**Severity distribution:** 2 High-risk issues, 2 Medium-risk issues, 0 Critical, 0 Low

### Highest-Risk Issue

**VULN-004 (Business Logic — Micro-Transfer Solvency Bypass)** presents the greatest integrity risk. An authenticated user can initiate transfers below £1,000 without sufficient funds, causing negative source balances and unbacked credits to recipient accounts. In a fintech context, this directly violates the core invariant that `source balance >= transfer amount`.

### Major Security Themes

1. **Authentication without authorisation (VULN-001)** — JWT proves identity on `GET /accounts/<id>` but the endpoint does not verify object ownership, demonstrating that authentication and authorisation are separate controls.
2. **Unsafe SQL construction (VULN-002)** — A dedicated search endpoint bypasses the otherwise consistent SQLAlchemy ORM pattern by concatenating user input into SQL.
3. **Unencoded HTML output (VULN-003)** — User-controlled `display_name` flows from input → database → HTML response without encoding.
4. **Incomplete business rule enforcement (VULN-004)** — Transaction logic applies insufficient funds checks only above an arbitrary threshold.

### Positive Observations (Controls Working as Expected)

- JWT authentication enforced on protected endpoints; missing/invalid/expired tokens return `401`
- `GET /users/<id>`, `GET /users/<id>/accounts`, and `GET /accounts/<id>/transactions` enforce ownership checks
- `POST /transactions` verifies the authenticated user owns the source account
- `GET /transactions/<id>` restricts access to sender or recipient
- Passwords hashed with Werkzeug; not returned in API responses
- Secrets loaded from environment variables, not hardcoded
- Transaction input validation rejects negative, zero, and malformed amounts
- Currency mismatch between accounts is rejected
- Transfer operations use database transactions and row locking on source accounts

### Recommended Priorities

1. **Immediate:** Restore insufficient funds validation for all transfer amounts (VULN-004)
2. **High:** Add object-level ownership check to `GET /accounts/<id>` (VULN-001)
3. **High:** Parameterise the search query or migrate to ORM (VULN-002)
4. **Medium:** HTML-encode output in profile view; validate `display_name` input (VULN-003)

Remediation is planned for Step 8. No code changes were made during this assessment.

---

## Assessment Methodology

### 1. Security Code Review

Systematic review of:

| Area | Files reviewed | Result |
|------|----------------|--------|
| Authentication | `app/auth.py`, `app/routes/auth.py` | Secure baseline |
| Authorisation | `app/routes/accounts.py`, `users.py`, `services/transactions.py` | **VULN-001** on `GET /accounts/<id>` only |
| Transaction logic | `app/services/transactions.py`, `app/validators.py` | **VULN-004** |
| Database queries | `app/routes/search.py` vs ORM elsewhere | **VULN-002** |
| User input | `app/validators.py`, route handlers | Mostly validated; search/profile exceptions |
| HTML rendering | `app/routes/profile.py` | **VULN-003** |
| Configuration | `app/config.py`, `.env.example` | Secure baseline |
| Error handling | Route exception handlers | Generic errors; stack traces in debug mode only |

### 2. Automated Testing

```powershell
pytest
# Result: 88 passed, 6 xfailed in ~20s
```

- Regression suite (Steps 1–5) largely passes; 6 tests `xfail` due to known intentional flaws
- `tests/test_vulnerabilities.py` confirms all 4 vulnerabilities programmatically

### 3. Manual API Testing

Manual tests below use **localhost only** (`http://127.0.0.1:5000`). Prerequisites: application running, PostgreSQL migrated (`python migrate_db.py`), test users Alice and Bob with accounts.

---

## Manual Test Procedures

### Authentication Tests

#### AUTH-01: Protected endpoint without token

```http
GET /accounts/1
```

| | |
|---|---|
| **Expected (secure)** | `401 {"error": "Authentication required"}` |
| **Observed** | `401 {"error": "Authentication required"}` |
| **Result** | PASS |

#### AUTH-02: Invalid JWT

```http
GET /accounts/1
Authorization: Bearer invalid-token
```

| | |
|---|---|
| **Expected** | `401` |
| **Observed** | `401 {"error": "Authentication required"}` |
| **Result** | PASS |

#### AUTH-03: Expired JWT

Use a token with `exp` in the past.

| | |
|---|---|
| **Expected** | `401` |
| **Observed** | `401 {"error": "Authentication required"}` |
| **Result** | PASS (confirmed via pytest) |

---

### Authorisation Tests

#### AUTHZ-01: Access another user's account (IDOR)

1. Login as Alice → obtain token  
2. Identify Bob's account ID (e.g. `2`)  
3. Request:

```http
GET /accounts/2
Authorization: Bearer <alice_token>
```

| | |
|---|---|
| **Expected (secure)** | `403 {"error": "Forbidden"}` |
| **Observed** | `200` with Bob's account JSON including `balance`, `account_number`, `user_id` |
| **Result** | **FAIL — VULN-001 confirmed** |

**Analysis:** Authentication answers *"Who are you?"* (Alice is logged in). Authorisation answers *"Are you allowed to access account 2?"* (No — but the endpoint does not enforce this).

#### AUTHZ-02: Access another user's transaction history

```http
GET /accounts/2/transactions
Authorization: Bearer <alice_token>
```

| | |
|---|---|
| **Expected** | `403` |
| **Observed** | `403 {"error": "Forbidden"}` |
| **Result** | PASS — ownership check present on this endpoint |

#### AUTHZ-03: Transfer from another user's account

```http
POST /transactions
Authorization: Bearer <alice_token>

{"from_account_id": 2, "to_account_id": 1, "amount": "10.00", "currency": "GBP"}
```

(where account 2 belongs to Bob)

| | |
|---|---|
| **Expected** | `403` |
| **Observed** | `403 {"error": "Forbidden"}` |
| **Result** | PASS |

---

### Input Validation Tests

#### INPUT-01: Missing required fields on transfer

```http
POST /transactions
Authorization: Bearer <token>
{"from_account_id": 1, "currency": "GBP"}
```

| | |
|---|---|
| **Expected** | `400` with validation errors |
| **Observed** | `400 {"errors": ["amount is required", ...]}` |
| **Result** | PASS |

#### INPUT-02: Negative amount

```json
{"from_account_id": 1, "to_account_id": 2, "amount": "-10.00", "currency": "GBP"}
```

| | |
|---|---|
| **Expected** | `400` |
| **Observed** | `400` — "amount must be greater than zero" |
| **Result** | PASS |

#### INPUT-03: Zero amount

| | |
|---|---|
| **Expected** | `400` |
| **Observed** | `400` |
| **Result** | PASS |

#### INPUT-04: Invalid currency

```json
{"currency": "JPY"}
```

| | |
|---|---|
| **Expected** | `400` |
| **Observed** | `400` |
| **Result** | PASS |

---

### SQL Injection Tests

#### SQLI-01: Boolean-based injection on search

```http
GET /search/users?q=' OR '1'='1
```

| | |
|---|---|
| **Expected (secure)** | Only users matching literal search term; injection has no effect |
| **Observed** | All users returned (boolean condition makes WHERE clause always true) |
| **Result** | **FAIL — VULN-002 confirmed** |

**Root cause:** The `q` parameter is embedded via f-string into:

```python
f"WHERE username LIKE '%{query_term}%' OR email LIKE '%{query_term}%'"
```

The attacker-controlled `'` terminates the string literal and injects `OR '1'='1`, altering query logic.

**Impact:** Unauthenticated extraction of user records (id, username, email). No destructive SQL observed or tested.

#### SQLI-02: Normal search (baseline)

```http
GET /search/users?q=alice
```

| | |
|---|---|
| **Observed** | Returns matching users only |
| **Result** | Expected behaviour for benign input |

---

### XSS Tests

#### XSS-01: Stored XSS in profile

**Step 1 — Store payload (source):**

```http
PUT /users/me/profile
Authorization: Bearer <alice_token>
Content-Type: application/json

{"display_name": "<script>alert(\"VulnBank XSS\")</script>"}
```

| | |
|---|---|
| **Observed** | `200` — payload stored in `users.display_name` |

**Step 2 — Trigger rendering (sink):**

```http
GET /profile/1/view
```

| | |
|---|---|
| **Expected (secure)** | HTML-encoded output: `&lt;script&gt;...` |
| **Observed** | Raw `<script>alert("VulnBank XSS")</script>` in HTML body |
| **Result** | **FAIL — VULN-003 confirmed** |

**Data flow:** Input (`PUT /users/me/profile`) → Storage (`users.display_name`) → Sink (`GET /profile/<id>/view` renders via f-string into HTML).

**Impact:** JavaScript execution in victim's browser when viewing profile. Lab uses harmless `alert()` PoC only.

---

### Business Logic Tests

#### BL-01: Insufficient funds — large transfer (≥ £1000)

Alice balance: £100.00. Transfer: £1500.00.

| | |
|---|---|
| **Expected** | `400 {"error": "insufficient funds"}` |
| **Observed** | `400 insufficient funds` |
| **Result** | PASS — check applies at ≥ £1000 |

#### BL-02: Insufficient funds — micro transfer (< £1000)

Alice balance: £100.00. Transfer: £500.00.

| | |
|---|---|
| **Expected (secure)** | `400 {"error": "insufficient funds"}` |
| **Observed** | `201 Created` — Alice balance becomes `-400.00`, Bob receives £500 |
| **Result** | **FAIL — VULN-004 confirmed** |

**Violated invariant:** `source balance >= transaction amount`

The service only evaluates solvency when `amount >= Decimal("1000.00")`:

```python
if amount >= micro_transfer_limit and source.balance < amount:
    raise TransferError("insufficient funds", 400)
```

Transfers of £999.99 or below bypass this check entirely.

---

## Findings Summary

| ID | File | Endpoint | Class |
|----|------|----------|-------|
| VULN-001 | `app/routes/accounts.py` | `GET /accounts/<id>` | Broken Object Level Authorization |
| VULN-002 | `app/routes/search.py` | `GET /search/users` | SQL Injection |
| VULN-003 | `app/routes/profile.py` | `PUT /users/me/profile`, `GET /profile/<id>/view` | Stored XSS |
| VULN-004 | `app/services/transactions.py` | `POST /transactions` | Business Logic Flaw |

Detailed reports: `security/findings/VULN-00x-*.md`

Supporting artefacts:

- `security/test-matrix.md` — full test matrix
- `security/vulnerabilities/` — original lab introduction notes
- `tests/test_vulnerabilities.py` — automated PoC tests

---

## Conclusion

The VulnBank `vulnerable-lab` branch contains **four confirmed security vulnerabilities** spanning authorisation, injection, output encoding, and business logic. The application's secure baseline demonstrates good practices in JWT handling, password storage, ORM usage (except search), and most ownership checks — making the remaining gaps suitable for targeted remediation in Step 8.

No application code was modified during this assessment.
