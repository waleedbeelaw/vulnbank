# SQL Injection

## Severity

**High**

User input from the search query parameter is concatenated directly into a SQL statement. An attacker can alter the query logic and extract data beyond the intended search scope.

## Description

`GET /search/users?q=<query>` builds SQL using Python f-string interpolation instead of parameterised queries. This is a classic SQL injection sink.

## Affected Endpoint

`GET /search/users?q=<query>`

## Root Cause

In `app/routes/search.py`:

```python
sql = (
    "SELECT id, username, email FROM users "
    f"WHERE username LIKE '%{query_term}%' OR email LIKE '%{query_term}%'"
)
results = db.session.execute(text(sql)).fetchall()
```

The `query_term` value is inserted directly into the SQL string without escaping or parameter binding.

## Preconditions

- No authentication required for this endpoint
- Attacker can send HTTP requests to the local VulnBank instance

## Proof of Concept

```http
GET /search/users?q=' OR '1'='1
Host: 127.0.0.1:5000
```

This payload modifies the `WHERE` clause so that all users are returned instead of a filtered subset.

Other benign local-only payloads for lab testing:

```http
GET /search/users?q=alice' UNION SELECT id, username, email FROM users WHERE '1'='1
```

## Impact

- Bypass search filters
- Extract additional user records (usernames, emails, IDs)
- Potential foundation for further injection techniques in a less restricted lab

This lab implementation is limited to `SELECT` on the local `users` table. No destructive operations are implemented.

## OWASP Category

- [OWASP API Security Top 10 — API8:2023 Security Misconfiguration](https://owasp.org/API-Security/editions/2023/en/0xa8-security-misconfiguration/) (unsafe defaults)
- [OWASP Top 10 — A03:2021 Injection](https://owasp.org/Top10/A03_2021-Injection/)

## Remediation

Use SQLAlchemy ORM or parameterised queries:

```python
User.query.filter(
    or_(
        User.username.ilike(f"%{query_term}%"),
        User.email.ilike(f"%{query_term}%"),
    )
).all()
```

Or with `text()` and bound parameters:

```python
sql = text(
    "SELECT id, username, email FROM users "
    "WHERE username LIKE :term OR email LIKE :term"
)
db.session.execute(sql, {"term": f"%{query_term}%"})
```

Never concatenate untrusted input into SQL strings.

## Regression Test

`tests/test_vulnerabilities.py::test_sql_injection_vulnerability_returns_extra_users` must **not** return all users when given an injection payload after remediation.
