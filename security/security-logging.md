# Security Logging and Audit Trail

## Purpose

Structured security logging helps VulnBank answer audit and investigation questions such as:

- **Who** performed an action?
- **What** action occurred?
- **Which resource** was affected?
- **Was it allowed or denied?**
- **When** did it happen?
- **Which request** ties related events together?

Security logging supports:

- incident investigation after suspicious activity
- abuse detection (failed logins, repeated authorization denials)
- authentication and authorization review
- financial transaction auditability

VulnBank emits JSON audit events to **stdout** so container platforms can collect them. This is suitable for local development and Docker deployments; a production deployment would normally forward logs to a centralized logging or SIEM platform.

## Logged events

| Event | When |
|-------|------|
| `auth.login.success` | Valid credentials authenticate a user |
| `auth.login.failure` | Invalid credentials on login |
| `auth.unauthenticated` | Protected endpoint accessed without an `Authorization` header |
| `auth.token.invalid` | Missing, malformed, expired, or invalid JWT |
| `authorization.denied` | Authenticated user denied access to another user's account, transaction, or transaction history |
| `account.created` | Authenticated user creates a new account |
| `transaction.created` | Transfer completes successfully |
| `transaction.rejected` | Transfer rejected (insufficient funds, source-account ownership, currency mismatch) |

Routine successful GET requests (for example `/health`) are **not** logged as security events.

## Sensitive data policy

VulnBank **does not log**:

- plaintext passwords
- password hashes
- JWTs or access tokens
- `Authorization` headers
- application secrets (`JWT_SECRET_KEY`, session secrets)
- database credentials (`DATABASE_URL`, database passwords)
- complete request bodies that may contain sensitive fields

Audit records prefer stable identifiers such as `user_id`, `account_id`, and `transaction_id` rather than full object serialization.

## Request IDs

Each HTTP request receives a **correlation ID**:

- Clients may send `X-Request-ID` with a bounded value (1–64 characters; letters, digits, `.`, `_`, `-` only).
- If the header is missing or invalid, the server generates a UUID.
- The resolved ID is stored for the request lifetime, included in security audit events, and returned in the response header `X-Request-ID`.

Request correlation helps tie login, authorization, and transaction events to a single API call during investigation.

## Structured logging

Security events are emitted as single-line JSON records on the `vulnbank.security` logger.

Common fields:

| Field | Description |
|-------|-------------|
| `timestamp` | UTC ISO-8601 timestamp |
| `level` | Log level (audit events use `INFO`) |
| `event` | Dot-separated event name |
| `outcome` | `success`, `failure`, or `denied` where applicable |
| `request_id` | Correlation ID for the HTTP request |
| `user_id` | Authenticated user when known |
| `resource_type` | Affected resource type (`account`, `transaction`) |
| `resource_id` | Affected resource identifier |
| `reason` | Machine-readable reason code |
| `remote_addr` | Client address from the WSGI request |

Not every event includes every field.

Example:

```json
{
  "timestamp": "2026-08-24T21:00:00+00:00",
  "level": "INFO",
  "event": "auth.login.success",
  "outcome": "success",
  "request_id": "client-req-123",
  "user_id": 1,
  "remote_addr": "127.0.0.1"
}
```

Implementation: [`app/security_logging.py`](../app/security_logging.py).

## Log injection protections

User-influenced values written to logs are sanitized:

- carriage return (`\r`) and newline (`\n`) characters are removed
- values are truncated to a maximum length (128 characters)
- client `X-Request-ID` values must match a strict allow-list pattern or are replaced with a server UUID

This reduces log forging / log injection where attacker-controlled input could otherwise create fake log lines.

## Production considerations

Be accurate about VulnBank's scope:

- **stdout logging** is suitable for container log collection (Docker, Kubernetes, etc.)
- A real production deployment would normally **forward** logs to centralized storage with retention and access controls
- **Retention and access control** for financial audit logs are deployment and governance concerns
- VulnBank **does not implement a SIEM** or log aggregation platform
- The optional `LOG_LEVEL` environment variable adjusts logger verbosity but security audit events are emitted at `INFO`; lowering log level below `INFO` would suppress audit output - document and avoid in production

## Related documentation

- [README.md - Security](../README.md#security-policy-and-documentation)
- [security/README.md](README.md)
