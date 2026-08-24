# VulnBank Security Documentation

This directory contains the Application Security lifecycle demonstrated by the VulnBank portfolio project.

## Security lifecycle

```
Vulnerability introduction (Step 6)
         ↓
Security assessment (Step 7)
         ↓
Remediation (Step 8)
         ↓
Automated regression testing (pytest)
         ↓
CI security gates (GitHub Actions)
```

Each phase is preserved in Git history on the `vulnerable-lab` branch so reviewers can follow the full AppSec story.

## Documentation index

| Document | Description |
|----------|-------------|
| [../SECURITY.md](../SECURITY.md) | Security policy — reporting, disclosure, scope |
| [dependency-management.md](dependency-management.md) | Dependency scanning with pip-audit |
| [container-security.md](container-security.md) | Docker container security decisions |
| [supply-chain-security.md](supply-chain-security.md) | SBOM generation, supply-chain inventory, and CI artifact retention |
| [security-logging.md](security-logging.md) | Structured security audit logging and request correlation |
| [deployment-security.md](deployment-security.md) | Docker/Compose hardening and Checkov IaC scanning |
| [cicd-security.md](cicd-security.md) | GitHub Actions hardening — permissions, SHA pinning, concurrency |
| [dast/README.md](dast/README.md) | Dynamic application security testing with OWASP ZAP |
| [assessment.md](assessment.md) | Step 7 AppSec assessment summary |
| [remediation.md](remediation.md) | Step 8 remediation summary (all findings **Remediated**) |
| [test-matrix.md](test-matrix.md) | Structured manual test cases |
| [findings/](findings/) | Per-finding reports (VULN-001 … VULN-004) with remediation status |
| [vulnerabilities/](vulnerabilities/) | Original lab vulnerability descriptions (historical) |

## CI security gates

Pull requests targeting `vulnerable-lab` must pass eight checks defined in [`.github/workflows/security.yml`](../.github/workflows/security.yml):

| Gate | Tool |
|------|------|
| Test Suite | pytest |
| SAST | Bandit |
| SCA | pip-audit |
| Secret Scan | Gitleaks |
| DAST | OWASP ZAP + `security/dast/regression_checks.py` |
| Container Scan | Trivy |
| SBOM | Syft (CycloneDX container inventory) |
| IaC Scan | Checkov (Dockerfile / Compose) |

See [README.md — Pull Request Security Gate](../README.md#pull-request-security-gate). CI/CD pipeline hardening (least privilege, SHA-pinned actions, concurrency, timeouts) is documented in [cicd-security.md](cicd-security.md).

## Quick local verification

```powershell
pip install -r requirements-dev.txt
pytest -v
bandit -r app/ -ll
pip-audit -r requirements.txt
```

## Lab safety

- Localhost development only
- No real credentials in the repository
- Not intended for production deployment

See [../SECURITY.md](../SECURITY.md) for full reporting and disclosure guidance.
