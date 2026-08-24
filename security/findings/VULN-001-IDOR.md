# Finding VULN-001: Broken Object Level Authorization on Account Retrieval

## Severity

**High** (CVSS 3.1 Base Score: **6.5 Medium**)

Although CVSS rates this 6.5 (Medium band), it is classified **High** in this fintech context because unauthorised access to account balances and account numbers represents a significant confidentiality breach for a banking API. The score reflects that exploitation requires a valid authenticated session (PR:L) and does not directly modify data (I:N).

## CWE

**CWE-639: Authorization Bypass Through User-Controlled Key**

Related: CWE-284 (Improper Access Control), CWE-862 (Missing Authorization)

## OWASP Category

**OWASP API Security Top 10 — API1:2023 Broken Object Level Authorization (BOLA/IDOR)**

## Affected Component

| | |
|---|---|
| **Endpoint** | `GET /accounts/<id>` |
| **File** | `app/routes/accounts.py` (lines 35–47) |
| **Function** | `get_account()` |

## Description

The account retrieval endpoint requires a valid JWT but does not verify that the authenticated user owns the requested account. Any authenticated user who knows or can enumerate an account ID can retrieve another user's account details, including balance, account number, currency, and internal user ID.

Authentication confirms *who* the caller is. Authorisation confirms *whether* that caller may access the specific object. This endpoint implements authentication only.

## Root Cause

The ownership check present in the secure baseline was intentionally removed:

```python
@accounts_bp.route("/accounts/<id>")
@jwt_required()
def get_account(account_id):
    account = db.session.get(Account, account_id)
    if account is None:
        return jsonify({"error": "account not found"}), 404
    # Ownership check omitted — returns any account to any authenticated user
    return jsonify(account_to_dict(account)), 200
```

Other account-related endpoints (`GET /accounts/<id>/transactions`) correctly compare `account.user_id` to the JWT subject.

## Preconditions

- Attacker holds a valid VulnBank JWT (any registered user)
- Attacker knows or can guess target account IDs (sequential integers: 1, 2, 3…)

## Proof of Concept

```powershell
# 1. Login as Alice
$alice = Invoke-RestMethod -Uri "http://127.0.0.1:5000/login" -Method POST `
  -ContentType "application/json" `
  -Body '{"email":"alice@example.com","password":"example-password"}'

# 2. Request Bob's account (ID 2) while authenticated as Alice
Invoke-RestMethod -Uri "http://127.0.0.1:5000/accounts/2" `
  -Headers @{ Authorization = "Bearer $($alice.access_token)" }
```

## Observed Result

HTTP `200 OK` with Bob's account JSON:

```json
{
    "id": 2,
    "user_id": 2,
    "account_number": "VB1234567890",
    "balance": "50.00",
    "currency": "GBP"
}
```

## Expected Secure Result

HTTP `403 Forbidden`:

```json
{"error": "Forbidden"}
```

## Impact

| Dimension | Impact |
|-----------|--------|
| **Confidentiality** | High — exposure of financial balances and account numbers |
| **Integrity** | None — read-only access |
| **Availability** | None |

An attacker can enumerate accounts and harvest financial metadata for all users, supporting fraud planning, targeted social engineering, or further attacks.

## Risk

In a fintech application, account balance and account number are sensitive customer data protected by access control regulations and customer trust. BOLA on financial objects is one of the most common and impactful API vulnerabilities (OWASP API1).

## Recommended Remediation

Restore object-level ownership verification before returning account data:

```python
if account.user_id != get_current_user_id():
    return jsonify({"error": "Forbidden"}), 403
```

Ensure every endpoint returning user-specific objects validates ownership against the JWT `sub` claim, not client-supplied identifiers.

## Verification

1. `tests/test_auth.py::test_alice_cannot_access_bob_account` must pass (expect `403`)
2. `tests/test_vulnerabilities.py::test_idor_vulnerability_*` must fail or be updated to expect `403`
3. Manual retest: Alice requests Bob's account → `403`

## CVSS v3.1

**Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N`  
**Base Score:** **6.5 (Medium)**

| Metric | Value | Rationale |
|--------|-------|-----------|
| AV:N | Network | API accessible over HTTP |
| AC:L | Low | Sequential account IDs; no special conditions |
| PR:L | Low | Requires registered user account and JWT |
| UI:N | None | No victim interaction required |
| S:U | Unchanged | Impact limited to VulnBank data |
| C:H | High | Full account object including balance exposed |
| I:N | None | Read-only |
| A:N | None | No availability impact |
