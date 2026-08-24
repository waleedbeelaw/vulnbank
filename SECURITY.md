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
| `main` | Secure baseline reference; protected by the Security Pipeline |
| `vulnerable-lab` | Full lab history: vulnerability introduction → assessment → remediation → CI security gates |

Changes to `main` or `vulnerable-lab` should pass the GitHub Actions **Security Pipeline** (pytest, Bandit, pip-audit, Gitleaks, OWASP ZAP, Trivy, Syft SBOM, Checkov) before merge. See [README.md](README.md#pull-request-security-gate) and [security/README.md](security/README.md). CI/CD hardening details: [security/cicd-security.md](security/cicd-security.md).

## Branch Protection and Security Gates

VulnBank is designed to demonstrate a **security-gated pull request workflow** on the `main` and `vulnerable-lab` branches. The CI pipeline in `.github/workflows/security.yml` runs eight jobs on every push and pull request targeting `main` or `vulnerable-lab`. When branch protection is configured, these jobs become **required status checks** that must pass before GitHub allows a merge.

### Required status checks (job names)

Repository administrators should require these exact GitHub Actions check names:

| Status check name |
|-------------------|
| PR Security Gate — Test Suite (pytest) |
| PR Security Gate — SAST (Bandit) |
| PR Security Gate — SCA (pip-audit) |
| PR Security Gate — Secret Scan (Gitleaks) |
| PR Security Gate — DAST (OWASP ZAP) |
| PR Security Gate — Container Scan (Trivy) |
| PR Security Gate — SBOM (Syft) |
| PR Security Gate — IaC Scan (Checkov) |

These names match the `name:` fields defined in `.github/workflows/security.yml`. After the workflow has run at least once on the branch, they appear under **Settings → Branches → Branch protection rules → Require status checks to pass**.

### Recommended configuration

The following settings are **recommended** for `main` and `vulnerable-lab` in **Settings → Branches → Add branch protection rule** (or edit an existing rule):

| Setting | Recommendation |
|---------|----------------|
| **Require a pull request before merging** | Enabled — all changes enter through reviewable PRs |
| **Require status checks to pass before merging** | Enabled — select all eight **PR Security Gate** checks listed above |
| **Require branches to be up to date before merging** | Enabled (recommended) — ensures checks ran against the latest base branch |
| **Do not merge when checks fail** | Implicit when required checks are configured; a failing Security Pipeline must block merge |
| **Restrict who can push to matching branches** | Enabled where appropriate — limits direct pushes that bypass PR workflow |
| **Allow force pushes** | Disabled — prevents rewriting history to skip failed checks |
| **Allow deletions** | Disabled — prevents accidental branch removal |

### Currently configured

Branch protection is a **GitHub repository setting** configured by administrators in the GitHub web UI. It is **not** defined in this repository's source code.

**This documentation does not assert that branch protection is currently enabled.** To verify the live configuration, a repository administrator should review **Settings → Branches** on GitHub.

Until branch protection is enabled:

- The Security Pipeline still runs and reports pass/fail on pull requests
- A merge may remain technically possible even when checks fail
- Enabling the recommended settings above closes that gap and enforces the security gate at the platform level

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
4. **CI enforcement** — `.github/workflows/security.yml` runs security checks on every PR; with branch protection enabled, failing checks block merge (see [Branch Protection and Security Gates](SECURITY.md#branch-protection-and-security-gates))

For dependency vulnerabilities, see [security/dependency-management.md](security/dependency-management.md).

Portfolio documentation: [security/README.md](security/README.md) · [security/threat-model.md](security/threat-model.md) · [security/architecture.md](security/architecture.md) · [security/security-journey.md](security/security-journey.md) · [security/control-matrix.md](security/control-matrix.md).

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
