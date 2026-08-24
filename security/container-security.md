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

The GitHub Actions job **PR Security Gate — Container Scan (Trivy)** builds the image and fails on **HIGH** or **CRITICAL** vulnerabilities reported by Trivy. Unfixed vulnerabilities are not silently ignored.

## Related documentation

- [README.md — Docker](../README.md#docker)
- [SECURITY.md](../SECURITY.md)
