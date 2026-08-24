# IDOR / Broken Object Level Authorization (BOLA)

## Severity

**High**

An authenticated user can read another user's bank account details. In a fintech API, unauthorised access to account balances and account numbers is a serious confidentiality breach even without the ability to transfer funds.

## Description

`GET /accounts/<id>` requires a valid JWT but does not verify that the authenticated user owns the requested account. Any logged-in user can retrieve any account by ID.

This demonstrates **Authentication ≠ Authorisation**: the API confirms who you are, but not what you are allowed to access.

## Affected Endpoint

`GET /accounts/<id>`

## Root Cause

In `app/routes/accounts.py`, the ownership check was intentionally removed:

```python
# Ownership check deliberately omitted on vulnerable-lab branch
return jsonify(account_to_dict(account)), 200
```

The secure baseline compared `account.user_id` to `get_current_user_id()` and returned `403` when they differed.

## Preconditions

- Attacker has a valid VulnBank account and JWT
- Attacker knows or can guess another account ID (often sequential integers)

## Proof of Concept

```http
POST /login
Content-Type: application/json

{"email": "alice@example.com", "password": "example-password"}
```

```http
GET /accounts/2
Authorization: Bearer <alice_token>
```

If account `2` belongs to Bob, Alice receives Bob's account JSON including balance and account number.

## Impact

- Read other users' account balances
- Read other users' account numbers
- Enumerate accounts by iterating IDs
- Support further attacks (social engineering, fraud planning)

## OWASP Category

- [OWASP API Security Top 10 - API1:2023 Broken Object Level Authorization](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)

## Remediation

Restore object-level ownership verification:

```python
if account.user_id != get_current_user_id():
    return jsonify({"error": "Forbidden"}), 403
```

Always derive the authorised object set from the JWT identity, never trust client-supplied ownership hints.

## Regression Test

`tests/test_vulnerabilities.py::test_idor_vulnerability_alice_can_view_bob_account` must expect **403** after remediation.

Secure regression: `tests/test_auth.py::test_alice_cannot_access_bob_account` must pass without `xfail`.
