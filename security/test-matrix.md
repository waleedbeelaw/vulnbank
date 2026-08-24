# VulnBank Security Test Matrix

**Branch:** `vulnerable-lab`  
**Assessment date:** 24 August 2026  
**Legend:** PASS = secure behaviour observed | **FAIL** = vulnerability confirmed | XFAIL = known failure on lab branch

---

## Authentication

| Test ID | Test | Endpoint | Expected | Observed | Result |
|---------|------|----------|----------|----------|--------|
| AUTH-01 | No token on protected endpoint | `GET /accounts/1` | 401 | 401 Authentication required | PASS |
| AUTH-02 | Malformed Authorization header | `GET /accounts/1` | 401 | 401 | PASS |
| AUTH-03 | Invalid JWT | `GET /accounts/1` | 401 | 401 | PASS |
| AUTH-04 | Expired JWT | `GET /accounts/1` | 401 | 401 | PASS |
| AUTH-05 | Valid JWT on protected endpoint | `GET /accounts/1` (owner) | 200 | 200 | PASS |
| AUTH-06 | Login with wrong password | `POST /login` | 401 generic | 401 Invalid credentials | PASS |
| AUTH-07 | Login with unknown email | `POST /login` | 401 generic | 401 Invalid credentials | PASS |
| AUTH-08 | Password not in login response | `POST /login` | No password fields | No password fields | PASS |

---

## Authorization / Ownership

| Test ID | Test | Endpoint | Expected | Observed | Result |
|---------|------|----------|----------|----------|--------|
| AUTHZ-01 | User views own account | `GET /accounts/<own_id>` | 200 | 200 | PASS |
| AUTHZ-02 | User views another user's account | `GET /accounts/<other_id>` | 403 | **200 with other user's data** | **FAIL (VULN-001)** |
| AUTHZ-03 | User views own profile | `GET /users/<own_id>` | 200 | 200 | PASS |
| AUTHZ-04 | User views another user's profile | `GET /users/<other_id>` | 403 | 403 Forbidden | PASS |
| AUTHZ-05 | User lists own accounts | `GET /users/<own_id>/accounts` | 200 | 200 | PASS |
| AUTHZ-06 | User lists another user's accounts | `GET /users/<other_id>/accounts` | 403 | 403 Forbidden | PASS |
| AUTHZ-07 | User views own account transactions | `GET /accounts/<own_id>/transactions` | 200 | 200 | PASS |
| AUTHZ-08 | User views another user's transactions | `GET /accounts/<other_id>/transactions` | 403 | 403 Forbidden | PASS |
| AUTHZ-09 | Transfer from own account | `POST /transactions` | 201 | 201 | PASS |
| AUTHZ-10 | Transfer from another user's account | `POST /transactions` | 403 | 403 Forbidden | PASS |
| AUTHZ-11 | View transaction as sender | `GET /transactions/<id>` | 200 | 200 | PASS |
| AUTHZ-12 | View transaction as recipient | `GET /transactions/<id>` | 200 | 200 | PASS |
| AUTHZ-13 | View transaction as unrelated user | `GET /transactions/<id>` | 403 | 403 Forbidden | PASS |
| AUTHZ-14 | Create account for self (JWT owner) | `POST /accounts` | 201, user_id from JWT | 201, correct user_id | PASS |
| AUTHZ-15 | user_id in body ignored on account create | `POST /accounts` with foreign user_id | Own account created | Own account created | PASS |

---

## IDOR / BOLA

| Test ID | Test | Endpoint | Expected | Observed | Result |
|---------|------|----------|----------|----------|--------|
| IDOR-01 | Enumerate account by sequential ID | `GET /accounts/1`, `/2`, `/3` | 403 for non-owned | **200 for any authenticated user** | **FAIL (VULN-001)** |
| IDOR-02 | Account number exposed via IDOR | `GET /accounts/<id>` | Not accessible | **account_number in response** | **FAIL (VULN-001)** |
| IDOR-03 | Balance exposed via IDOR | `GET /accounts/<id>` | Not accessible | **balance in response** | **FAIL (VULN-001)** |

---

## SQL Injection

| Test ID | Test | Endpoint | Expected | Observed | Result |
|---------|------|----------|----------|----------|--------|
| SQLI-01 | Normal search | `GET /search/users?q=alice` | Matching users only | Matching users only | PASS |
| SQLI-02 | Boolean injection | `GET /search/users?q=' OR '1'='1` | Filtered results | **All users returned** | **FAIL (VULN-002)** |
| SQLI-03 | Empty search | `GET /search/users?q=` | All or none per design | All users (LIKE '%%') | INFO |
| SQLI-04 | ORM endpoints use parameterisation | `POST /users`, etc. | Parameterised | SQLAlchemy ORM used | PASS |

---

## Cross-Site Scripting (XSS)

| Test ID | Test | Endpoint | Expected | Observed | Result |
|---------|------|----------|----------|----------|--------|
| XSS-01 | Store display_name | `PUT /users/me/profile` | Stored | Stored in DB | PASS (storage works) |
| XSS-02 | Render profile HTML | `GET /profile/<id>/view` | Encoded output | **Raw script in HTML** | **FAIL (VULN-003)** |
| XSS-03 | JSON endpoints return JSON | `GET /users/<id>` | application/json | application/json | PASS |
| XSS-04 | PoC payload | `<script>alert("VulnBank XSS")</script>` | Harmless when encoded | **Executable in browser** | **FAIL (VULN-003)** |

---

## Transaction Validation

| Test ID | Test | Endpoint | Expected | Observed | Result |
|---------|------|----------|----------|----------|--------|
| TXN-01 | Missing from_account_id | `POST /transactions` | 400 | 400 | PASS |
| TXN-02 | Missing to_account_id | `POST /transactions` | 400 | 400 | PASS |
| TXN-03 | Missing amount | `POST /transactions` | 400 | 400 | PASS |
| TXN-04 | Missing currency | `POST /transactions` | 400 | 400 | PASS |
| TXN-05 | Negative amount | `POST /transactions` | 400 | 400 | PASS |
| TXN-06 | Zero amount | `POST /transactions` | 400 | 400 | PASS |
| TXN-07 | Invalid amount string | `POST /transactions` | 400 | 400 | PASS |
| TXN-08 | Same source and destination | `POST /transactions` | 400 | 400 | PASS |
| TXN-09 | Nonexistent source account | `POST /transactions` | 404 | 404 | PASS |
| TXN-10 | Nonexistent destination account | `POST /transactions` | 404 | 404 | PASS |
| TXN-11 | Unsupported currency | `POST /transactions` | 400 | 400 | PASS |

---

## Currency Validation

| Test ID | Test | Endpoint | Expected | Observed | Result |
|---------|------|----------|----------|----------|--------|
| CCY-01 | GBP → GBP transfer | `POST /transactions` | 201 | 201 | PASS |
| CCY-02 | GBP → EUR transfer | `POST /transactions` | 400 currency mismatch | 400 | PASS |
| CCY-03 | EUR → GBP transfer | `POST /transactions` | 400 currency mismatch | 400 | PASS |

---

## Insufficient Funds / Business Logic

| Test ID | Test | Endpoint | Expected | Observed | Result |
|---------|------|----------|----------|----------|--------|
| FUNDS-01 | Transfer exceeds balance (≥ £1000) | `POST /transactions` amount=1500, balance=100 | 400 insufficient funds | 400 insufficient funds | PASS |
| FUNDS-02 | Transfer exceeds balance (< £1000) | `POST /transactions` amount=500, balance=100 | 400 insufficient funds | **201 — balance goes negative** | **FAIL (VULN-004)** |
| FUNDS-03 | Valid transfer within balance | `POST /transactions` amount=50, balance=100 | 201 | 201 | PASS |
| FUNDS-04 | Failed large transfer leaves balances unchanged | `POST /transactions` | No change | No change | PASS |
| FUNDS-05 | Failed micro transfer leaves balances unchanged | `POST /transactions` | No change | **Balances changed (overdraft)** | **FAIL (VULN-004)** |
| FUNDS-06 | Atomicity on failure | DB rollback | Rollback | Rollback on commit failure | PASS |

---

## Input Validation (General)

| Test ID | Test | Endpoint | Expected | Observed | Result |
|---------|------|----------|----------|----------|--------|
| INPUT-01 | Malformed JSON body | Various POST endpoints | 400 | 400 | PASS |
| INPUT-02 | Missing username on register | `POST /users` | 400 | 400 | PASS |
| INPUT-03 | Duplicate username | `POST /users` | 409 | 409 | PASS |
| INPUT-04 | Password minimum length | `POST /users` | 400 if too short | 400 | PASS |
| INPUT-05 | Unsupported account currency | `POST /accounts` | 400 | 400 | PASS |

---

## Configuration / Secrets

| Test ID | Test | Component | Expected | Observed | Result |
|---------|------|-----------|----------|----------|--------|
| CFG-01 | DATABASE_URL from env | `app/config.py` | Not hardcoded | From environment | PASS |
| CFG-02 | JWT_SECRET_KEY from env | `app/config.py` | Not hardcoded | From environment | PASS |
| CFG-03 | Missing env vars fail clearly | App startup | RuntimeError | RuntimeError | PASS |
| CFG-04 | Password hash not in API | `POST /users`, `GET /users` | Absent | Absent | PASS |
| CFG-05 | .env not in repository | Git | Not committed | In .gitignore | PASS |

---

## Summary

| Category | Tests | Pass | Fail |
|----------|-------|------|------|
| Authentication | 8 | 8 | 0 |
| Authorization | 15 | 14 | 1 |
| IDOR/BOLA | 3 | 0 | 3 |
| SQL Injection | 4 | 2 | 1 |
| XSS | 4 | 2 | 2 |
| Transaction validation | 11 | 11 | 0 |
| Currency | 3 | 3 | 0 |
| Insufficient funds | 6 | 4 | 2 |
| Input validation | 5 | 5 | 0 |
| Configuration | 5 | 5 | 0 |
| **Total** | **64** | **54** | **10** |

Note: Multiple test rows map to the same underlying vulnerability (4 unique findings). Automated pytest: **88 passed, 6 xfailed**.
