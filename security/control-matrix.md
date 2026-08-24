# Security Control Matrix

Maps key risks to **preventative** and **detective** controls actually implemented in VulnBank. CI enforcement refers to named jobs in [`.github/workflows/security.yml`](../.github/workflows/security.yml).

| Risk | Preventative control | Detective control | CI enforcement | Evidence |
|------|---------------------|-------------------|----------------|----------|
| SQL injection | SQLAlchemy ORM parameterised queries (`ilike()` on search) | pytest SQLi regression tests; DAST regression script | pytest + DAST | `tests/test_vulnerabilities.py`; `security/findings/VULN-002-*` |
| IDOR / broken access control | Object-level ownership checks on accounts, users, transactions | pytest auth/IDOR tests | pytest + DAST regression | `app/routes/accounts.py`; `tests/test_auth.py` |
| Stored XSS | Jinja2 auto-escaping on profile HTML | pytest XSS tests; ZAP passive baseline | pytest + DAST | `tests/test_vulnerabilities.py`; `security/dast/` |
| Business-logic / solvency bypass | Balance check for all transfer amounts; atomic DB transaction | pytest transfer + vulnerability tests | pytest | `app/services/transactions.py` |
| Authentication bypass | `jwt_required()` on protected routes | pytest 401 tests; audit `auth.unauthenticated` | pytest | `app/auth.py`; `tests/test_security_logging.py` |
| JWT tampering | HS256 + secret from env; algorithm allow-list | pytest expired/invalid token tests; audit events | pytest | `app/auth.py` |
| Password exposure | Werkzeug hashing; never serialise hash | pytest response checks | pytest | `app/models.py`; `tests/test_auth.py` |
| Account enumeration on login | Generic `Invalid credentials` message | pytest | pytest | `app/routes/auth.py` |
| Secrets in Git | `.gitignore` for `.env`; env-based config | Gitleaks full-history scan | **PR Security Gate — Secret Scan (Gitleaks)** | `.gitignore`; Gitleaks v3 |
| Python dependency CVEs | Pinned `requirements.txt`; upgrade process documented | pip-audit | **PR Security Gate — SCA (pip-audit)** | `security/dependency-management.md` |
| Container / OS CVEs | `apt-get upgrade` in Dockerfile; minimal exposure | Trivy image scan | **PR Security Gate — Container Scan (Trivy)** | `security/container-security.md` |
| Supply-chain opacity | SBOM from built image; SHA-pinned Actions; Dependabot | Syft CycloneDX + validation script | **PR Security Gate — SBOM (Syft)** | `security/supply-chain-security.md` |
| IaC misconfiguration | Non-root user; internal DB; Compose hardening | Checkov Dockerfile + Compose scan | **PR Security Gate — IaC Scan (Checkov)** | `security/deployment-security.md` |
| SAST gaps in Python | Secure coding patterns in `app/` | Bandit `-ll` on `app/` | **PR Security Gate — SAST (Bandit)** | `.github/workflows/security.yml` |
| CI/CD pipeline tampering | SHA-pinned third-party actions; `contents: read` default | Dependabot github-actions updates | (process) | `security/cicd-security.md` |
| Sensitive data in audit logs | Policy: no passwords/JWTs/secrets in logs | pytest log capture tests | pytest | `security/security-logging.md` |
| Log injection | Sanitise user-influenced log fields; request ID pattern | pytest injection tests | pytest | `app/security_logging.py` |
| Undeclared merge of vulnerable code | PR workflow to `vulnerable-lab` | Eight required gates (when branch protection enabled) | All 8 gates | `SECURITY.md` |

## Controls not implemented (honest gaps)

| Gap | Notes |
|-----|-------|
| Rate limiting / brute-force lockout | Login abuse logged but not throttled |
| WAF / DDoS protection | Lab localhost scope |
| SIEM / centralised log storage | stdout only; 30-day SBOM artifact retention |
| CSRF tokens | Bearer JWT API — CSRF model differs from cookie sessions |
| Cryptographic SBOM signing / SLSA L3 | SBOM is inventory evidence only |

## Related documentation

- [threat-model.md](threat-model.md)
- [architecture.md](architecture.md)
- [security-journey.md](security-journey.md)
