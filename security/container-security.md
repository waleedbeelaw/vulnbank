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
3. Fails on **HIGH** or **CRITICAL** vulnerabilities (`exit-code: 1`, `ignore-unfixed: false`)

Secret scanning is handled separately by the **PR Security Gate — Secret Scan (Gitleaks)** job. Trivy is configured with `scanners: vuln` only to avoid duplicate secret detection, not to weaken coverage.

### Trivy findings and remediation (Step 14)

Initial Trivy scans of the unpatched `python:3.12-slim` image reported **Debian 13** OS vulnerabilities (53 total in the first failing run). Python application packages (`requirements.txt`) showed **0** library vulnerabilities — the failures were **OS/base-image packages**, not VulnBank application code.

Representative findings included:

| Package | Severity | Status | Remediation |
|---------|----------|--------|-------------|
| `util-linux` | HIGH | Fixed version available (`2.41.5-0+deb13u1`) | `apt-get upgrade` during Docker build |
| `perl-base` | CRITICAL / HIGH | Some CVEs **affected** or **fix_deferred** with no Debian fix yet | Documented; not ignored in Trivy config |

**Dockerfile remediation:** an early build stage runs:

```dockerfile
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
```

This applies available Debian security updates (including fixable packages such as `util-linux`) on each image build without adding unnecessary packages.

**Base image:** remains the official `python:3.12-slim` image (Debian-based, actively maintained). No switch to unofficial images. Python 3.12, Flask, and `psycopg2-binary` compatibility are unchanged.

### Fixable vs unfixed vulnerabilities

| Category | Policy |
|----------|--------|
| **Fixable** (Debian publishes a patched package) | Must be remediated in the Dockerfile via `apt-get upgrade` so Trivy passes |
| **Unfixed / fix_deferred** (no patched package from Debian yet) | **Not** added to Trivy ignore lists. Documented here. Re-evaluate when Debian publishes fixes |
| **Reachability** | `perl-base` is a base OS dependency of the slim image; VulnBank does not invoke Perl at runtime. Residual OS CVEs may still fail the gate until upstream patches exist |

**Current gate policy:** `severity: HIGH,CRITICAL`, `ignore-unfixed: false`. The pipeline fails when Trivy reports unfixed HIGH/CRITICAL OS CVEs even if no vendor patch exists yet. This is intentional — it surfaces base-image debt and triggers rebuilds when Debian publishes fixes, rather than hiding findings.

Do **not** set `ignore-unfixed: true` or blanket CVE ignores merely to green the pipeline while CRITICAL `perl-base` issues remain without vendor fixes.

## Related documentation

- [README.md — Docker](../README.md#docker)
- [SECURITY.md](../SECURITY.md)
