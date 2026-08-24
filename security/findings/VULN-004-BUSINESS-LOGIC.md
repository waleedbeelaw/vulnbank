# Finding VULN-004: Micro-Transfer Solvency Bypass

## Severity

**High** (CVSS 3.1 Base Score: **7.1 High**)

An authenticated user can transfer funds they do not possess for any amount below £1,000, violating the core financial invariant that source balance must cover the transfer amount. This enables unbacked payments to other users.

## CWE

**CWE-840: Business Logic Errors**

Related: CWE-691 (Insufficient Control Flow Management), CWE-20 (Improper Input Validation - incomplete business rule)

## OWASP Category

**OWASP API Security Top 10 - API6:2023 Unrestricted Access to Sensitive Business Flows**  
**OWASP Top 10 2021 - A04:2021 Insecure Design**

## Affected Component

| | |
|---|---|
| **Endpoint** | `POST /transactions` |
| **File** | `app/services/transactions.py` (lines 47–53) |
| **Function** | `create_transfer()` |

## Description

The transaction service implements a flawed "micro-transfer fast path" that only validates sufficient funds when the transfer amount is **greater than or equal to £1,000**. Transfers below this threshold skip the solvency check entirely, allowing accounts to be debited beyond zero and recipient accounts to be credited with unbacked funds.

### Violated Business Rule

```
source balance >= transaction amount   (must ALWAYS hold)
```

Currently enforced only when:

```
transaction amount >= £1000.00
```

## Root Cause

```python
micro_transfer_limit = Decimal("1000.00")
if amount >= micro_transfer_limit and source.balance < amount:
    raise TransferError("insufficient funds", 400)
```

The conditional `amount >= micro_transfer_limit` means transfers of £0.01 through £999.99 never evaluate the balance check. The code then proceeds to:

```python
source.balance -= amount
destination.balance += amount
```

If `source.balance` is £100 and `amount` is £500, the source becomes `-£400` while the destination receives a legitimate-looking £500 credit.

## Preconditions

- Attacker has valid JWT
- Attacker owns the source account (`from_account_id`)
- Transfer amount is **less than** £1,000
- Source and destination currencies match (GBP/GBP, etc.)

## Proof of Concept

**Setup:** Alice has £100.00 in account 1. Bob owns account 2.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/transactions" -Method POST `
  -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer <alice_token>" } `
  -Body '{"from_account_id":1,"to_account_id":2,"amount":"500.00","currency":"GBP"}'
```

## Observed Result

HTTP `201 Created`:

```json
{
    "id": 1,
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": "500.00",
    "currency": "GBP"
}
```

Account balances after transfer:

| Account | Before | After |
|---------|--------|-------|
| Alice (source) | £100.00 | **-£400.00** |
| Bob (destination) | £0.00 | **£500.00** |

## Expected Secure Result

HTTP `400 Bad Request`:

```json
{"error": "insufficient funds"}
```

No balance changes. No transaction record created.

## Impact

| Dimension | Impact |
|-----------|--------|
| **Confidentiality** | None |
| **Integrity** | **High** - financial records corrupted; unbacked credits issued |
| **Availability** | None |

An attacker can send up to £999.99 per transaction without possessing funds, repeatedly paying other users with money that does not exist in the source account.

## Risk

Financial integrity is the foundational property of a banking API. Solvency validation must apply uniformly to every transfer regardless of amount. A partial or threshold-based bypass creates a realistic fraud vector that would cause direct monetary loss in production.

This finding demonstrates why business logic testing complements traditional security testing - input validation passes, authentication passes, authorisation passes, yet the transaction should still be rejected.

## Recommended Remediation

Enforce insufficient funds check for **every** transfer:

```python
if source.balance < amount:
    raise TransferError("insufficient funds", 400)
```

Remove the micro-transfer threshold entirely. If performance optimisations are needed, they must not skip solvency validation.

Consider adding a database constraint preventing negative balances as defence in depth.

## Verification

1. Alice with £100 transfers £500 → must receive `400 insufficient funds`
2. Alice with £100 transfers £1500 → must receive `400 insufficient funds`
3. Alice with £100 transfers £50 → must succeed (legitimate transfer)
4. `tests/test_transactions.py::test_insufficient_funds_rejected` must pass without `xfail`
5. `tests/test_vulnerabilities.py::test_business_logic_vulnerability_*` must fail (expect secure behaviour)

## CVSS v3.1

**Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N`  
**Base Score:** **7.1 (High)**

| Metric | Value | Rationale |
|--------|-------|-----------|
| AV:N | Network | Transaction API over HTTP |
| AC:L | Low | Simple POST with known account IDs |
| PR:L | Low | Requires authenticated user with own source account |
| UI:N | None | No victim interaction required |
| S:U | Unchanged | Impact within application financial data |
| C:N | None | No confidentiality impact |
| I:H | High | Unbacked fund transfers; negative balances |
| A:N | None | Service remains available |

## Remediation

Removed the micro-transfer threshold in `app/services/transactions.py` and enforced insufficient funds for every transfer:

```python
if source.balance < amount:
    raise TransferError("insufficient funds", 400)
```

The check executes after source-account authorisation and currency validation, and before any balance mutation or transaction record creation. Existing row locking (`with_for_update()`) and atomic commit/rollback behaviour are unchanged.

## Verification

The following regression tests confirm the fix:

- `tests/test_transactions.py::test_insufficient_funds_rejected` - overdraft attempt returns 400
- `tests/test_transactions.py::test_failed_transfer_does_not_modify_source_balance` - source balance unchanged on failure
- `tests/test_transactions.py::test_failed_transfer_does_not_modify_destination_balance` - destination balance unchanged on failure
- `tests/test_transactions.py::test_failed_transfer_does_not_create_record` - no transaction record on failure
- `tests/test_vulnerabilities.py::test_business_logic_remediation_micro_transfer_overdraft_rejected` - £100 → £500 fails
- `tests/test_vulnerabilities.py::test_business_logic_remediation_exact_balance_transfer_succeeds` - £100 → £100 succeeds
- `tests/test_vulnerabilities.py::test_business_logic_remediation_sub_limit_transfer_succeeds` - £100 → £99.99 succeeds
- `tests/test_vulnerabilities.py::test_business_logic_remediation_failed_transfer_creates_no_record` - no record after failed £500 transfer

Manual retest: Alice with £100 transfers £500 → HTTP 400 `{"error": "insufficient funds"}`; balances unchanged.

## Status

**REMEDIATED**
