# Threat Model

Practical STRIDE-oriented threat model for VulnBank on the **`vulnerable-lab`** branch after remediation and DevSecOps controls. This document describes the **current** codebase and CI pipeline - not aspirational controls.

## System assets

| Asset | Sensitivity | Location |
|-------|-------------|----------|
| User credentials (passwords) | High | PostgreSQL (`password_hash` only); never returned in API |
| JWT authentication tokens | High | Client-held; signed with `JWT_SECRET_KEY` |
| User identities | Medium | PostgreSQL; API JSON |
| Bank accounts & balances | High | PostgreSQL |
| Transaction records | High | PostgreSQL |
| Database contents | High | PostgreSQL volume (Compose) |
| Application configuration / secrets | Critical | Environment variables (`.env`, Compose); not in Git |
| Audit logs | Medium | stdout JSON (`vulnbank.security` logger) |

## Trust boundaries

```text
[Client] ----HTTP----> [Flask API] ----SQLAlchemy----> [PostgreSQL]
                           |
                    [Docker container]
                           |
              (PostgreSQL NOT exposed to host)

[Developer] ----Git----> [GitHub repository]
                              |
                    [GitHub Actions runners]
                              |
              [Build / test / scan artifacts]
```

| Boundary | Crosses | Controls |
|----------|---------|----------|
| Client → Flask API | HTTP, JWT, JSON bodies | AuthN/AuthZ, validation, generic errors |
| Flask API → PostgreSQL | SQL via ORM | Parameterised queries, transactions |
| Developer → GitHub | Source, PRs | Branch protection, 8 CI gates, Gitleaks |
| GitHub Actions → build env | Checkout, Docker, scanners | SHA-pinned actions, least privilege |
| Container → host | Published port 5000 only | Non-root user, Compose hardening |
| CI → artifacts | SBOM, ZAP reports | Upload steps; finite retention |

## Attack surfaces

- Authentication: `POST /login`, JWT middleware
- Authorisation: account, user, transaction endpoints
- Financial logic: `POST /transactions`, balance updates
- User input: registration, search, profile display name, transfer payloads
- JWT handling: `Authorization` header, HS256 verification
- Database: SQLAlchemy ORM (search route historically raw SQL - **remediated**)
- HTML output: profile view template - **remediated** (auto-escaping)
- Docker / Compose: image build, service configuration
- CI/CD: `.github/workflows/security.yml`, third-party actions
- Dependencies: `requirements.txt`, base OS packages in container image
- Audit logs: structured JSON to stdout

## STRIDE threat table

| Threat | Category | Affected component | Example attack | Existing mitigation | Residual risk |
|--------|----------|-------------------|----------------|---------------------|---------------|
| SQL injection in user search | **Tampering / Information disclosure** | `GET /search/users` | `' OR '1'='1` returns all users | **Remediated:** SQLAlchemy `ilike()` bound parameters; regression tests; ZAP/regression layer | Low - lab history preserved in Git; regression tests enforce fix |
| IDOR on account retrieval | **Information disclosure** | `GET /accounts/<id>` | Authenticated user reads another user's balance | **Remediated:** ownership check (`403`); auth regression tests | Low |
| Stored XSS in profile view | **Tampering** | `GET /profile/<id>/view` | `<script>` in `display_name` executes in browser | **Remediated:** Jinja2 auto-escaping; XSS regression tests; ZAP passive baseline | Low for API JSON clients; HTML profile still an output surface |
| Micro-transfer solvency bypass | **Tampering / Elevation** | `POST /transactions` | Transfer below threshold with insufficient funds | **Remediated:** balance check for all amounts; atomic DB transaction | Low |
| Authentication bypass | **Spoofing** | Protected routes | Call API without JWT | `jwt_required()` → `401`; audit `auth.unauthenticated` | Low for protected routes |
| JWT manipulation / algorithm confusion | **Spoofing / Elevation** | JWT middleware | Forge token or use `none` algorithm | HS256 only; secret from env; invalid/expired → `401`; audit events | Medium - symmetric HS256; secret strength depends on deployment |
| Brute-force / login abuse | **Denial of service** | `POST /login` | Password spraying | Generic error messages; audit `auth.login.failure` | **No rate limiting** - accepted lab limitation |
| Sensitive data in responses | **Information disclosure** | Login, user APIs | Extract password hashes via API | Hashes never serialised; generic login errors | Low |
| Secret leakage in Git | **Information disclosure** | Repository | Commit `.env` or API keys | `.gitignore`; Gitleaks full-history scan; CI Secret Scan gate | Low if hooks/CI enforced |
| Vulnerable Python dependencies | **Tampering** | Application runtime | Exploit known CVE in Flask/driver | pip-audit SCA gate; dependency docs | Medium - zero-day / transitive gaps remain |
| Vulnerable container OS/packages | **Tampering** | Docker image | Exploit base image CVE | Trivy gate (fixable HIGH/CRITICAL); `apt-get upgrade` in Dockerfile | Medium - vendor-unfixed OS CVEs tracked, not all blocked |
| Malicious dependency / supply-chain | **Tampering** | Build & runtime | Typosquat package | Pinned requirements; pip-audit; CycloneDX SBOM from **built image** | Medium - SBOM is inventory, not provenance signing |
| Container escape / compromise | **Elevation** | Docker host | Exploit privileged container | Non-root user; no privileged mode; cap drop on app; Checkov Dockerfile scan | Medium - lab stack not hardened to production K8s level |
| CI/CD pipeline compromise | **Tampering / Elevation** | GitHub Actions | Malicious action tag retargeted | SHA-pinned actions; Dependabot; concurrency/timeouts; `contents: read` default | Medium - artifact upload scope under verification |
| Log injection / log forging | **Repudiation / Tampering** | Audit logger | Newline in `X-Request-ID` creates fake log line | Sanitisation; length limits; pattern validation on request IDs | Low |
| CSRF on state-changing API | **Spoofing** | Browser clients | Cross-site form posts token | **Not applicable** to Bearer-token JSON API (no cookie session); browser CSRF differs from cookie-based apps | N/A for current API design - clients must protect tokens |
| Denial of service (application) | **Denial of service** | Flask API | Flood login/transfer endpoints | CI job timeouts only | **No WAF/rate limit** - accepted lab limitation |
| Audit log tampering | **Repudiation** | stdout logs | Attacker modifies local log files | Logs not integrity-signed; stdout collection only | Medium - production would use immutable log store |

## Lab history vs current state

| Phase | Description |
|-------|-------------|
| **Intentionally introduced (Step 6)** | VULN-001 IDOR, VULN-002 SQLi, VULN-003 stored XSS, VULN-004 business logic - preserved in Git history and `security/vulnerabilities/` |
| **Assessed (Step 7)** | Documented in `security/assessment.md` and `security/findings/` |
| **Remediated (Step 8)** | All four findings fixed; `tests/test_vulnerabilities.py` regression suite |
| **Residual / accepted** | No rate limiting, HS256 symmetric JWT, vendor-unfixed container CVEs, finite SBOM artifact retention, no SIEM, educational deployment only |

## Related documentation

- [architecture.md](architecture.md)
- [control-matrix.md](control-matrix.md)
- [remediation.md](remediation.md)
- [security-journey.md](security-journey.md)
