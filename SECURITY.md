# Security Policy

## About VulnBank

VulnBank is an **educational Application Security / DevSecOps portfolio project**. It implements a fintech-style REST API (Flask, PostgreSQL, JWT) used to demonstrate:

- Secure development practices
- Intentional vulnerability introduction (controlled lab)
- Structured security assessment
- Root-cause remediation
- Automated regression testing and CI security gates

**This repository is not production banking software.** It exists for learning, code review, and security workflow demonstration. Do not deploy it as a real financial service or expose it to untrusted networks without understanding its lab history.

## Supported branches and workflow

| Branch | Purpose |
|--------|---------|
| `main` | Secure baseline reference |
| `vulnerable-lab` | Full lab history: vulnerability introduction → assessment → remediation → CI security gates |

Changes to `vulnerable-lab` are expected to pass the GitHub Actions **Security Pipeline** (pytest, Bandit, pip-audit, Gitleaks) before merge. See [README.md](README.md#pull-request-security-gate) and [security/README.md](security/README.md).

## Reporting a security vulnerability

If you discover a **new, unintended security issue** in the current codebase (outside the documented lab history), please report it responsibly.

### Preferred reporting channels

1. **GitHub Security Advisories (recommended)**  
   Use **Security → Advisories → Report a vulnerability** on this repository (Private vulnerability reporting, if enabled by the repository owner).

2. **GitHub Issues (alternative)**  
   Open a issue with the title prefix `[Security]` and **do not** include exploit payloads, credentials, or sensitive data in the public description. The maintainer may request details through a private channel.

Do **not** report issues by committing exploit code, opening public pull requests with working exploits, or disclosing unfixed vulnerabilities in a way that puts users at risk.

## Responsible disclosure

Please allow reasonable time for triage and remediation before public disclosure. For this educational project:

- Report in good faith
- Provide enough detail to reproduce the issue locally
- Avoid testing against systems you do not own
- Do not access, modify, or exfiltrate data belonging to others
- Do not perform denial-of-service or destructive actions

## What to include in a report

A helpful report should contain:

| Item | Description |
|------|-------------|
| **Summary** | Short description of the issue and affected component |
| **Branch / commit** | Git branch and commit hash tested |
| **Steps to reproduce** | Minimal, local reproduction steps |
| **Expected vs actual behaviour** | What should happen vs what happens |
| **Impact** | Confidentiality, integrity, or availability effect |
| **Suggested fix** | Optional — root-cause fix if known |

Omit real credentials, production URLs, and personal data.

## How findings are tracked and remediated

This project follows a documented security lifecycle:

1. **Assessment** — findings recorded under `security/findings/` and summarised in `security/assessment.md`
2. **Remediation** — code fixes with root-cause changes, documented in `security/remediation.md` and per-finding reports
3. **Verification** — pytest regression tests in `tests/test_vulnerabilities.py` and the main test suite
4. **CI enforcement** — `.github/workflows/security.yml` blocks merge when checks fail

For dependency vulnerabilities, see [security/dependency-management.md](security/dependency-management.md).

## Intentional lab vulnerabilities

The `vulnerable-lab` branch **intentionally contained** documented flaws (IDOR, SQL injection, stored XSS, business-logic bypass) for educational purposes. These were assessed in Step 7 and remediated in Step 8. Historical reports remain under `security/findings/` and `security/vulnerabilities/` for learning purposes.

Do not assume every security weakness in Git history represents an unfixed issue in the current code — check `security/remediation.md` and the latest test results first.

## Scope limitations

Reports about the following are generally **out of scope**:

- Issues already documented and remediated in `security/remediation.md`
- Missing features not implemented by design (e.g. MFA, rate limiting)
- Risks inherent to running a local dev server on localhost
- Social engineering or physical attacks

Thank you for helping keep this project a useful and responsible AppSec learning resource.
