# Security Engineering Journey

VulnBank is structured as an **end-to-end AppSec / DevSecOps portfolio**, not merely a banking API. Each stage adds a problem, security decision, implementation, and verification evidence.

| # | Stage | Problem | Security decision | Implementation | Verification |
|---|-------|---------|-------------------|----------------|--------------|
| 1 | Secure baseline application | Build realistic fintech API without known flaws | Secure defaults: JWT, ORM, hashed passwords, atomic transfers | Flask, SQLAlchemy, ownership checks on routes | pytest functional tests |
| 2 | Deliberately vulnerable AppSec lab | Need realistic flaws for assessment | Introduce controlled vulnerabilities on `vulnerable-lab` | IDOR, SQLi, XSS, business-logic bypass | `security/vulnerabilities/` |
| 3 | Vulnerability assessment | Prove flaws with evidence | Structured AppSec review + test matrix | `security/assessment.md`, VULN-001–004 | Manual + automated tests (historical) |
| 4 | Remediation | Fix root causes, not symptoms | Restore AuthZ, parameterised SQL, escaping, solvency checks | Code fixes in `app/` | `security/remediation.md`; all **Remediated** |
| 5 | Security regression testing | Prevent reintroduction | Expand pytest for every remediated flaw | `tests/test_vulnerabilities.py` + auth/transfer tests | **125 tests** — PR Security Gate — Test Suite (pytest) |
| 6 | SAST | Catch Python anti-patterns early | Bandit on `app/` only | `sast` job in workflow | **PR Security Gate — SAST (Bandit)** |
| 7 | SCA | Known CVEs in dependencies | pip-audit on `requirements.txt` | `dependency-scan` job | **PR Security Gate — SCA (pip-audit)** |
| 8 | Secret scanning | Committed credentials | Gitleaks full history; token via env | Gitleaks **v3** (Node 24) | **PR Security Gate — Secret Scan (Gitleaks)** |
| 9 | DAST | Runtime behaviour gaps | OWASP ZAP baseline (passive) + authenticated regression | `security/dast/` | **PR Security Gate — DAST (OWASP ZAP)** |
| 10 | Branch protection / PR gates | Merge without review | Document eight required status checks | `SECURITY.md`, PR workflow to `vulnerable-lab` | Eight named checks (admin enables branch protection) |
| 11 | Containerisation | Reproducible deployment | Dockerfile + Compose; non-root; internal DB | `Dockerfile`, `docker-compose.yml` | `docker compose config`; health checks |
| 12 | Container scanning | OS/lib CVEs in shipped image | Trivy; fixable HIGH/CRITICAL; `ignore-unfixed: true` | `container-scan` job | **PR Security Gate — Container Scan (Trivy)** |
| 13 | SBOM / supply-chain visibility | Inventory of what ships | Syft CycloneDX JSON from **built image** | `sbom` job + `validate_sbom.py` | **PR Security Gate — SBOM (Syft)** |
| 14 | Security audit logging | Investigate auth/financial events | Structured JSON audit log; no secrets; request IDs | `app/security_logging.py` | `tests/test_security_logging.py` (pytest) |
| 15 | Deployment / IaC hardening | Insecure Compose/Dockerfile | Checkov; Compose hardening; dev-only credentials | `deployment-security.md` | **PR Security Gate — IaC Scan (Checkov)** |
| 16 | CI/CD hardening | Pipeline supply-chain risk | SHA-pinned actions; least privilege; concurrency; timeouts | `cicd-security.md`, Dependabot | Documented pipeline controls |
| 17 | Final threat modelling | Communicate risks to reviewers | STRIDE table; lab vs remediated vs residual | `threat-model.md`, `control-matrix.md` | Portfolio documentation (Step 19) |

## Interview narrative (60 seconds)

1. Built a **secure fintech API**, then **deliberately broke it** for a realistic lab.
2. Ran a **structured assessment**, documented four findings, and **remediated root causes**.
3. Locked fixes in with **125 automated tests** including vulnerability regressions.
4. Added **defence in depth in CI**: SAST, SCA, secrets, DAST, container scan, SBOM, IaC scan — **eight gates** on pull requests.
5. Hardened **runtime and pipeline**: Docker non-root, audit logging, SHA-pinned Actions, threat model.

## Related documentation

- [README.md](../README.md)
- [architecture.md](architecture.md)
- [threat-model.md](threat-model.md)
- [README.md — security index](README.md)
