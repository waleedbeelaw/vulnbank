# VulnBank Security Documentation

Central index for the Application Security / DevSecOps lifecycle demonstrated by VulnBank on the **`vulnerable-lab`** branch.

## Portfolio overview

| Document | Description |
|----------|-------------|
| [security-journey.md](security-journey.md) | End-to-end lifecycle narrative (baseline → lab → remediation → CI gates) |
| [architecture.md](architecture.md) | Runtime stack and DevSecOps pipeline (Mermaid diagrams) |
| [threat-model.md](threat-model.md) | STRIDE-style threat model - assets, boundaries, lab vs remediated vs residual |
| [control-matrix.md](control-matrix.md) | Risk → preventative/detective controls → CI enforcement |

## Security lifecycle

```
Secure baseline (Steps 1–5)
         ↓
Vulnerability introduction (Step 6)
         ↓
Security assessment (Step 7)
         ↓
Remediation (Step 8)
         ↓
Automated regression testing (125 pytest tests)
         ↓
CI security gates (8 required PR checks)
         ↓
Threat modelling & portfolio documentation (Step 19)
```

Each phase is preserved in Git history so reviewers can follow the full AppSec story.

## Policy and governance

| Document | Description |
|----------|-------------|
| [../SECURITY.md](../SECURITY.md) | Security policy - reporting, disclosure, scope, branch protection |
| [../README.md](../README.md) | Project overview and Security Engineering Highlights |

## Assessment and remediation (historical)

| Document | Description |
|----------|-------------|
| [assessment.md](assessment.md) | Step 7 AppSec assessment summary (historical snapshot at assessment time) |
| [remediation.md](remediation.md) | Step 8 remediation summary - all findings **Remediated** |
| [test-matrix.md](test-matrix.md) | Structured manual test cases |
| [findings/](findings/) | Per-finding reports (VULN-001 … VULN-004) with remediation status |
| [vulnerabilities/](vulnerabilities/) | Original lab vulnerability descriptions (historical) |

## Technical controls

| Document | Description |
|----------|-------------|
| [dependency-management.md](dependency-management.md) | pip-audit SCA and dependency upgrade workflow |
| [container-security.md](container-security.md) | Docker image decisions and Trivy policy |
| [supply-chain-security.md](supply-chain-security.md) | Syft CycloneDX SBOM from built image; CI artifact retention |
| [security-logging.md](security-logging.md) | Structured JSON audit logging and request correlation |
| [deployment-security.md](deployment-security.md) | Docker/Compose hardening and Checkov IaC scanning |
| [cicd-security.md](cicd-security.md) | SHA-pinned Actions, permissions, concurrency, Gitleaks v3 |
| [dast/README.md](dast/README.md) | OWASP ZAP baseline and authenticated regression checks |

## CI security gates

Pull requests targeting `vulnerable-lab` must pass eight checks defined in [`.github/workflows/security.yml`](../.github/workflows/security.yml):

| # | Status check name | Tool |
|---|-------------------|------|
| 1 | PR Security Gate - Test Suite (pytest) | pytest (125 tests) |
| 2 | PR Security Gate - SAST (Bandit) | Bandit |
| 3 | PR Security Gate - SCA (pip-audit) | pip-audit |
| 4 | PR Security Gate - Secret Scan (Gitleaks) | Gitleaks v3 |
| 5 | PR Security Gate - DAST (OWASP ZAP) | OWASP ZAP + `security/dast/regression_checks.py` |
| 6 | PR Security Gate - Container Scan (Trivy) | Trivy |
| 7 | PR Security Gate - SBOM (Syft) | Syft (CycloneDX JSON from container image) |
| 8 | PR Security Gate - IaC Scan (Checkov) | Checkov (Dockerfile / Compose) |

See [README.md - Pull Request Security Gate](../README.md#pull-request-security-gate). CI/CD pipeline hardening is documented in [cicd-security.md](cicd-security.md).

## Quick local verification

```powershell
pip install -r requirements-dev.txt
pytest -v
bandit -r app/ -ll
pip-audit -r requirements.txt
checkov -f Dockerfile --framework dockerfile --compact
checkov -f docker-compose.yml --framework yaml --compact
```

DAST requires Docker. See [dast/README.md](dast/README.md).

## Lab safety

- Localhost development only
- No real credentials in the repository
- Not intended for production deployment

See [../SECURITY.md](../SECURITY.md) for full reporting and disclosure guidance.
