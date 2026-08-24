# CI/CD Pipeline Security

## Purpose

VulnBank’s security gates run in **GitHub Actions**. A compromised workflow, mutable action reference, or over-privileged `GITHUB_TOKEN` can undermine application security controls. Step 18 hardens the existing **Security Pipeline** without adding a ninth scanner gate.

## Threat model

| Threat | Mitigation |
|--------|------------|
| Compromised third-party action (tag moved to malicious commit) | Pin actions to immutable **full commit SHAs** |
| Over-privileged workflow token | Workflow default `permissions: contents: read`; extra scopes only where required |
| Secret exfiltration via fork PR workflows | Standard `pull_request` trigger (not `pull_request_target`); least privilege; no secret echo |
| Shell injection from GitHub context | Avoid `${{ github.* }}` inside `run:` scripts; pass via `env` |
| Stale CI runs wasting runners / masking latest results | Concurrency group cancels superseded runs on the same ref |
| Hung scanners blocking runners indefinitely | Per-job `timeout-minutes` |
| Persisted Git credentials after checkout | `persist-credentials: false` on read-only checkouts |

## Least-privilege permissions

**Workflow default:**

```yaml
permissions:
  contents: read
```

**Job-level permission exceptions:** **None.** All jobs inherit the workflow default (`contents: read` only).

### Artifact upload permission review

Both **DAST** (failure-only ZAP reports) and **SBOM** (CycloneDX file) use the pinned `actions/upload-artifact@v4.6.2` step. The official [`actions/upload-artifact` README](https://github.com/actions/upload-artifact/tree/v4.6.2) and [`action.yml`](https://github.com/actions/upload-artifact/blob/v4.6.2/action.yml) **do not document** a required `GITHUB_TOKEN` scope for uploads.

VulnBank therefore does **not** grant job-level `actions: write`. Artifact steps inherit workflow-level `contents: read` only.

**SBOM-specific design:**

| Component | Setting | Purpose |
|-----------|---------|---------|
| `anchore/sbom-action` | `upload-artifact: false` | Disables Anchore’s built-in artifact upload path |
| `anchore/sbom-action` | `upload-release-assets: false` | No release asset writes |
| Follow-on step | `actions/upload-artifact@…` | Uploads `sbom.cdx.json` with explicit retention |

This keeps SBOM inventory generation (Syft) separate from artifact retention (official upload-artifact action) and avoids granting Anchore action broad upload permissions.

**Verification note:** Confirm in GitHub Actions that artifact upload succeeds under workflow-level `contents: read` only. If the runner rejects uploads, the least-privilege fix is a **narrow** job-level permission documented with upstream reference - not workflow-wide elevation.

No job grants `contents: write`, `pull-requests: write`, `packages: write`, or `id-token: write`.
## Immutable action SHA pinning

Third-party actions are pinned as:

```yaml
uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0
```

**Why not tags alone?** A mutable tag (e.g. `@v4`) can be retargeted to a different commit. Pinning the full SHA ensures the runner executes a known revision. Human-readable version comments are kept for maintainability.

**Dependabot** (`.github/dependabot.yml`) monitors `github-actions` weekly and opens PRs to bump SHA-pinned references when upstream releases change.

## Pinned action references

| Action | Version | Commit SHA | Used in |
|--------|---------|------------|---------|
| `actions/checkout` | v4.4.0 | `11d5960a326750d5838078e36cf38b85af677262` | All jobs except Secret Scan |
| `actions/checkout` | v6.0.1 | `8e8c483db84b4bee98b60c0593521ed34d9990e8` | Secret Scan (Gitleaks) - Node 24 runtime |
| `actions/setup-python` | v5.6.0 | `a26af69be951a213d495a4c3e4e4022e16d87065` | Python jobs |
| `actions/upload-artifact` | v4.6.2 | `ea165f8d65b6e75b540449e92b4886f43607fa02` | DAST, SBOM |
| `gitleaks/gitleaks-action` | v3.0.0 | `e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e` | Secret Scan |
| `aquasecurity/trivy-action` | v0.36.0 | `ed142fd0673e97e23eac54620cfb913e5ce36c25` | Container Scan |
| `anchore/sbom-action` | v0.24.0 | `e22c389904149dbc22b58101806040fa8d37a610` | SBOM |
Checkov and other scanners run via **pip** from `requirements-dev.txt` (not a GitHub Action).

Container images referenced in `run:` steps (e.g. `ghcr.io/zaproxy/zaproxy:stable`) are documented under [accepted risks](#accepted-risks).

## Checkout hardening

Read-only jobs use:

```yaml
- uses: actions/checkout@...
  with:
    persist-credentials: false
```

**Gitleaks** uses `fetch-depth: 0` (full history) because secret scanning requires complete Git history. It still sets `persist-credentials: false`.

The **Secret Scan** job uses `actions/checkout@v6.0.1` (Node 24) because the official [`gitleaks-action` v3 README](https://github.com/gitleaks/gitleaks-action/blob/v3.0.0/README.md) recommends checkout v6 alongside the Node 24 action runtime. Other jobs remain on checkout v4.4.0 to avoid unrelated mass upgrades.
## Shell and context injection

Review findings:

- **DAST ZAP step:** previously interpolated `${{ github.workspace }}` inside a `run:` block. Replaced with job-level `env: ZAP_WORKSPACE: ${{ github.workspace }}` and `"${ZAP_WORKSPACE}"` in the shell script.
- **Other `run:` steps:** use static commands or local files only; no PR titles, branch names, or commit messages are passed to the shell.
- **Scanner configs:** paths are repository-relative constants, not user-controlled workflow inputs.

## Secrets policy

- `GITHUB_TOKEN` is passed to Gitleaks via `env` (not CLI arguments).
- DAST uses a **CI-only** placeholder secret (`DAST_JWT_SECRET_KEY`) defined in workflow `env`, not a repository secret.
- No workflow step prints secrets.
- No `pull_request_target` workflow is used (avoids elevated fork PR access patterns).

## Concurrency

```yaml
concurrency:
  group: security-pipeline-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Supersedes in-progress runs for the **same workflow + ref** (branch or PR merge ref). Unrelated branches/PRs are unaffected.

## Job timeouts

| Job | `timeout-minutes` |
|-----|-------------------|
| Test Suite (pytest) | 15 |
| SAST (Bandit) | 15 |
| SCA (pip-audit) | 15 |
| Secret Scan (Gitleaks) | 20 |
| DAST (OWASP ZAP) | 45 |
| Container Scan (Trivy) | 30 |
| SBOM (Syft) | 30 |
| IaC Scan (Checkov) | 20 |

## pull_request vs pull_request_target

VulnBank uses **`pull_request`** and **`push`** on `vulnerable-lab` only. It does **not** use `pull_request_target`, which runs in the base repository context and can be dangerous with untrusted fork code combined with write permissions or secrets.

## Accepted risks

| Item | Rationale |
|------|-----------|
| Gitleaks `GITHUB_TOKEN` | Required by upstream action for GitHub API integration; scoped to workflow `contents: read`. |
| Artifact upload under `contents: read` only | Official `actions/upload-artifact` docs do not specify token scopes; GitHub Actions verification required. |
| `ghcr.io/zaproxy/zaproxy:stable` uses a moving tag | ZAP baseline image is invoked via `docker run` in a `run:` step, not a GitHub Action `uses:` reference. Pinning would require periodic manual digest updates; DAST behaviour is unchanged from Step 13. |
## Related documentation

- [deployment-security.md](deployment-security.md)
- [supply-chain-security.md](supply-chain-security.md)
- [README.md - Pull Request Security Gate](../README.md#pull-request-security-gate)
