# Finding VULN-002: SQL Injection in User Search

## Severity

**Medium** (CVSS 3.1 Base Score: **5.3 Medium**)

Unauthenticated attackers can manipulate SQL query logic to extract user records beyond the intended search scope. Impact is limited to the `users` table SELECT and the local lab scope; no write or destructive operations were identified.

## CWE

**CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')**

## OWASP Category

**OWASP Top 10 2021 — A03:2021 Injection**  
**OWASP API Security Top 10 — API8:2023 Security Misconfiguration** (unsafe implementation pattern)

## Affected Component

| | |
|---|---|
| **Endpoint** | `GET /search/users?q=<query>` |
| **File** | `app/routes/search.py` (lines 9–23) |
| **Function** | `search_users()` |

## Description

The user search endpoint constructs a SQL query by embedding the `q` query parameter directly into the SQL string using Python f-string interpolation. An attacker can inject SQL syntax to alter the `WHERE` clause logic, bypassing the intended filter and returning records that should not match.

The remainder of the application uses SQLAlchemy ORM with parameterised queries. This endpoint is an isolated exception.

## Root Cause

```python
query_term = request.args.get("q", "")
sql = (
    "SELECT id, username, email FROM users "
    f"WHERE username LIKE '%{query_term}%' OR email LIKE '%{query_term}%'"
)
results = db.session.execute(text(sql)).fetchall()
```

The `query_term` value is not sanitised, escaped, or bound as a parameter. User input becomes part of the executable SQL structure rather than a data value.

## Preconditions

- No authentication required
- Attacker can send HTTP requests to `http://127.0.0.1:5000`

## Proof of Concept

```powershell
$query = [uri]::EscapeDataString("' OR '1'='1")
Invoke-RestMethod -Uri "http://127.0.0.1:5000/search/users?q=$query"
```

Equivalent curl (Windows):

```powershell
curl.exe --globoff "http://127.0.0.1:5000/search/users?q=' OR '1'='1"
```

**Resulting SQL (simplified):**

```sql
SELECT id, username, email FROM users
WHERE username LIKE '%' OR '1'='1%' OR email LIKE '%' OR '1'='1%'
```

The boolean condition `'1'='1'` evaluates to true, causing all rows to be returned.

## Observed Result

HTTP `200 OK` with JSON array containing **all users** in the database, regardless of the intended search filter.

## Expected Secure Result

Only users whose username or email legitimately matches the search term should be returned. The injection payload should be treated as literal search text with no effect on query structure.

## Impact

| Dimension | Impact |
|-----------|--------|
| **Confidentiality** | Low — exposure of user IDs, usernames, and email addresses |
| **Integrity** | None in current implementation (SELECT only) |
| **Availability** | None |

In this lab, the query is SELECT-only. In a less restricted implementation, SQL injection could escalate to data modification. The root cause remains critical to fix regardless of current query type.

## Risk

SQL injection remains one of the most prevalent and well-understood web vulnerabilities. Even read-only injection in a fintech user directory exposes PII (email addresses) and aids account enumeration for follow-on attacks (credential stuffing, phishing).

## Recommended Remediation

Replace string concatenation with parameterised queries or ORM filters:

```python
# Option A: SQLAlchemy ORM
User.query.filter(
    or_(
        User.username.ilike(f"%{query_term}%"),
        User.email.ilike(f"%{query_term}%"),
    )
).all()

# Option B: Parameterised text()
sql = text(
    "SELECT id, username, email FROM users "
    "WHERE username LIKE :term OR email LIKE :term"
)
db.session.execute(sql, {"term": f"%{query_term}%"})
```

Additionally, require authentication for search if appropriate, and apply rate limiting.

## Verification

1. `GET /search/users?q=' OR '1'='1` must **not** return all users after fix
2. `GET /search/users?q=alice` must still return matching users
3. `tests/test_vulnerabilities.py::test_sql_injection_vulnerability_*` must fail (expect secure behaviour)

## CVSS v3.1

**Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N`  
**Base Score:** **5.3 (Medium)**

| Metric | Value | Rationale |
|--------|-------|-----------|
| AV:N | Network | Remote API endpoint |
| AC:L | Low | Simple boolean injection payload |
| PR:N | None | No authentication required |
| UI:N | None | No user interaction |
| S:U | Unchanged | Limited to application database |
| C:L | Low | Usernames and emails exposed |
| I:N | None | SELECT-only in current code |
| A:N | None | No availability impact |
