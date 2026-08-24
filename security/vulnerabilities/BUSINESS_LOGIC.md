# Business Logic — Micro-Transfer Solvency Bypass

## Severity

**High**

The transaction service skips the insufficient funds check for transfers below £1000. An account holder can send money they do not have, driving the source account into a negative balance.

## Description

Financial systems must enforce the invariant: **a user cannot transfer more money than their account holds**. A flawed "micro-transfer fast path" was added that only validates solvency when `amount >= 1000.00`.

This violates a core business rule and allows overdraft transfers to other users.

## Affected Endpoint

`POST /transactions`

## Root Cause

In `app/services/transactions.py`:

```python
micro_transfer_limit = Decimal("1000.00")
if amount >= micro_transfer_limit and source.balance < amount:
    raise TransferError("insufficient funds", 400)
```

Transfers under £1000 never check whether the source account has enough funds. The balance can go negative.

**Business rule violated:** accounts must not send funds exceeding their available balance, regardless of transfer size.

## Preconditions

- Attacker has a valid JWT
- Attacker owns the source account
- Attacker knows a destination account ID
- Transfer amount is **less than** £1000

## Proof of Concept

Alice has £100.00 in account 1. Bob owns account 2.

```http
POST /transactions
Authorization: Bearer <alice_token>
Content-Type: application/json

{
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": "500.00",
    "currency": "GBP"
}
```

**Expected (secure):** `400 insufficient funds`

**Actual (vulnerable):** `201 Created` — Alice's balance becomes `-400.00`, Bob receives £500.00.

## Impact

- Send money without sufficient funds
- Create negative balances
- Defraud other users by crediting their accounts with unbacked transfers
- Undermine financial integrity of the application

## OWASP Category

- [OWASP API Security Top 10 — API6:2023 Unrestricted Access to Sensitive Business Flows](https://owasp.org/API-Security/editions/2023/en/0xa6-unrestricted-access-to-sensitive-business-flows/)
- [OWASP Top 10 — A04:2021 Insecure Design](https://owasp.org/Top10/A04_2021-Insecure_Design/)

## Remediation

Always enforce solvency for every transfer:

```python
if source.balance < amount:
    raise TransferError("insufficient funds", 400)
```

Remove special-case shortcuts unless they are backed by equivalent financial controls (e.g. authorised overdraft limits with explicit business approval).

## Regression Test

`tests/test_vulnerabilities.py::test_business_logic_vulnerability_micro_transfer_overdraft` must receive **400** after remediation.

Secure regression: `tests/test_transactions.py::test_insufficient_funds_rejected` must pass without `xfail`.
