# Container Security

VulnBank's Docker setup follows basic container hardening for a **local development/demo** stack.

## Non-root execution

The application image creates a dedicated `vulnbank` user (UID/GID 1000) and runs `ENTRYPOINT` / `CMD` as that user. The container does not run Flask as root.

## Secret handling

- `.env` and real credentials are excluded via [`.dockerignore`](../.dockerignore).
- No secrets are baked into the [Dockerfile](../Dockerfile).
- [`docker-compose.yml`](../docker-compose.yml) uses clearly fake development-only values for `POSTGRES_PASSWORD` and `JWT_SECRET_KEY`.
- Production deployments must inject secrets via a secure secret manager, not Compose literals.

## Minimal exposure

| Surface | Decision |
|---------|----------|
| App port | `5000` published to localhost for API access |
| PostgreSQL | **Not** published to the host — reachable only on the Compose network as `db` |
| Privileged mode | Not used |
| Docker socket | Not mounted |
| Host bind mounts | Not used (named volume for PostgreSQL data only) |

## PostgreSQL isolation

The database runs in a separate Compose service on an internal network. The application connects with `DATABASE_URL` pointing at hostname `db`, not `localhost`.

## Health checks

- **db:** `pg_isready` ensures PostgreSQL accepts connections before the app starts.
- **app:** `GET /health` confirms the Flask process is responding.

## Image scanning (CI)

The GitHub Actions job **PR Security Gate — Container Scan (Trivy)**:

1. Builds `vulnbank:ci` from the [Dockerfile](../Dockerfile)
2. Scans the **built image** with Trivy (`scan-type: image`, `scanners: vuln`, `vuln-type: os,library`)
3. Fails on **fixable** **HIGH** or **CRITICAL** vulnerabilities (`exit-code: 1`, `ignore-unfixed: true`)

Secret scanning is handled separately by the **PR Security Gate — Secret Scan (Gitleaks)** job. Trivy is configured with `scanners: vuln` only to avoid duplicate secret detection, not to weaken coverage.

### Trivy assessment summary (Step 14)

| Scan stage | OS (Debian) findings | Python library findings |
|------------|----------------------|-------------------------|
| Initial image (before `apt-get upgrade`) | **53** vulnerabilities | **0** |
| After `apt-get update && apt-get upgrade` | **17** (14 HIGH, 3 CRITICAL) | **0** |

The OS upgrade removed all findings that had an available vendor fixed version. The remaining **17** HIGH/CRITICAL findings had **no vendor Fixed Version** in Trivy at assessment time and were marked **affected** or **fix_deferred**.

Examples of tracked, vendor-unfixed findings:

| Package | Example CVEs | Trivy status |
|---------|--------------|--------------|
| `gzip` | CVE-2026-41992 | affected, no fixed version |
| `ncurses` | CVE-2025-69720 | affected, no fixed version |
| OpenSSL | CVE-2026-14456 | fix_deferred, no fixed version |
| `perl-base` | CVE-2026-13221, CVE-2026-42496, CVE-2026-8376, CVE-2026-42497, and others | affected / fix_deferred, no fixed version |

These are **not** claimed to be harmless. They remain **security debt** in the base OS layer. VulnBank does not invoke Perl, gzip, or ncurses at application runtime, but the vulnerabilities still exist in the container filesystem until Debian publishes patches.

**Dockerfile remediation:** an early build stage runs:

```dockerfile
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
```

This applies available Debian security updates on each image build. **Base image:** official `python:3.12-slim` (Debian-based, actively maintained).

### Container vulnerability gate policy

VulnBank gates on **fixable** HIGH/CRITICAL container vulnerabilities:

| Finding type | CI behaviour |
|--------------|--------------|
| **Fixable** HIGH/CRITICAL (vendor Fixed Version available) | **FAIL** — PR blocked until remediated (typically via `apt-get upgrade` and image rebuild) |
| **Unfixed / vendor-deferred** HIGH/CRITICAL (no Fixed Version yet) | **Reported** in Trivy output; does **not** permanently block the PR |

**Trivy settings:**

```yaml
severity: HIGH,CRITICAL
exit-code: "1"
scanners: vuln
ignore-unfixed: true
```

`ignore-unfixed: true` does **not** mean “ignore vulnerabilities.” It means CI does **not** fail on findings that currently have **no available vendor remediation**. When Debian publishes a fix and Trivy’s vulnerability database records a Fixed Version, the finding becomes fixable and the gate **will fail** until the image is rebuilt with patched packages.

Fresh image builds and Trivy DB updates automatically reassess vendor-unfixed findings when fixes become available. No CVE-specific blanket ignore lists are used.

Vendor-unfixed vulnerabilities should be re-evaluated when:

- The base image tag is updated
- Debian security advisories publish fixes
- Trivy vulnerability data is refreshed in CI

The container does **not** have zero vulnerabilities while vendor-unfixed HIGH/CRITICAL OS CVEs remain in Trivy reports.

## Related documentation

- [README.md — Docker](../README.md#docker)
- [SECURITY.md](../SECURITY.md)
