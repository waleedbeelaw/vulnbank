# Deployment and Configuration Security

## Purpose

Application code can be secure while **deployment configuration** still introduces risk. Misconfigured containers, exposed databases, privileged mode, or hardcoded secrets in Compose files can undermine otherwise sound controls.

VulnBank treats Dockerfile and Docker Compose as **Infrastructure-as-Code (IaC)** and scans them in CI with [Checkov](https://www.checkov.io/) alongside manual hardening decisions documented here.

## Controls implemented

| Control | Implementation |
|---------|----------------|
| Non-root container | Dockerfile `USER vulnbank` (UID/GID 1000) |
| Internal PostgreSQL | `db` service has **no** host port mapping — reachable only on the Compose network |
| Minimal exposed ports | Only app port `5000` published to the host |
| No privileged mode | `privileged: true` not used |
| No Docker socket | `/var/run/docker.sock` not mounted |
| No host bind mounts | Named volume `postgres_data` only |
| Compose hardening | `security_opt: no-new-privileges:true` on `db` and `app` |
| App capability reduction | `cap_drop: [ALL]` on `app` |
| Read-only app filesystem | `read_only: true` with `tmpfs: [/tmp]` for runtime temp files |
| Health checks | `pg_isready` for PostgreSQL; `GET /health` for Flask |
| OS package patching | Dockerfile `apt-get update && apt-get upgrade` before app install |
| Container vulnerability gate | Trivy scans built image in CI |
| IaC / config scanning | Checkov scans `Dockerfile` and `docker-compose.yml` in CI |

See also [container-security.md](container-security.md) and [supply-chain-security.md](supply-chain-security.md).

## Development credentials

`docker-compose.yml` uses **DEVELOPMENT-ONLY EXAMPLE CREDENTIALS**:

- `${POSTGRES_USER:-vulnbank}`
- `${POSTGRES_PASSWORD:-vulnbank-dev-password}`
- `${JWT_SECRET_KEY:-docker-dev-jwt-secret-not-for-production-use}`

These defaults exist for local lab convenience. They must **not** be reused in production. Override them via environment variables or a local `.env` file (see [`.env.example`](../.env.example)).

Gitleaks scans repository history for accidentally committed secrets. Checkov’s **secrets** framework is **not** enabled for Compose in CI because it would flag these intentional development placeholders; real secret leakage is still covered by Gitleaks and code review.

## Checkov

**Tool:** Checkov **3.3.13** (pinned in `requirements-dev.txt`, installed in CI via pip).

**CI job:** **PR Security Gate — IaC Scan (Checkov)**

| Target | Framework | Scope |
|--------|-----------|-------|
| `Dockerfile` | `dockerfile` | Image build instructions (USER, HEALTHCHECK, base tag, etc.) |
| `docker-compose.yml` | `yaml` | Compose service configuration |

Checkov runs with default fail behaviour (non-zero exit on failed checks). The job does **not** use `soft_fail`, `continue-on-error`, or broad `--skip-check` suppressions.

Findings are **reviewed** — not blindly ignored. If a check is skipped in future, it must be scoped, commented, and listed under [Accepted findings](#accepted-findings).

Run locally:

```powershell
pip install -r requirements-dev.txt
checkov -f Dockerfile --framework dockerfile --compact
checkov -f docker-compose.yml --framework yaml --compact
```

## Accepted findings

**None.** No Checkov checks are suppressed for VulnBank at this time.

## Production considerations

Be accurate about VulnBank’s scope:

- **Production secrets** belong in a secret manager (Vault, cloud KMS/Secrets Manager, etc.), not Compose literals or defaults
- **TLS / HTTPS** would normally terminate at a reverse proxy or ingress controller
- A production deployment would use a **WSGI server** (gunicorn, uwsgi) rather than Flask’s development server
- **Network policies, firewalls, and segmentation** are platform/deployment concerns
- VulnBank is an **educational lab**, not a production banking system

## Related documentation

- [container-security.md](container-security.md)
- [security-logging.md](security-logging.md)
- [README.md — Docker](../README.md#docker)
