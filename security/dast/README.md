# Dynamic Application Security Testing (DAST)

## What is DAST?

**Dynamic Application Security Testing** exercises a **running** application from the outside, sending real HTTP requests and observing responses. It complements:

| Technique | When it runs | What it inspects |
|-----------|--------------|------------------|
| **SAST** (Bandit) | Build time | Source code |
| **SCA** (pip-audit) | Build time | Dependencies |
| **DAST** (OWASP ZAP) | Run time | Live HTTP behaviour on localhost |

DAST can reveal issues visible only when components interact — routing, authentication enforcement, response encoding, and server configuration — that static analysis may miss.

## Why OWASP ZAP?

[OWASP ZAP](https://www.zaproxy.org/) is an open-source DAST tool widely used in DevSecOps pipelines. VulnBank runs ZAP from the official container image (`ghcr.io/zaproxy/zaproxy:stable`) in GitHub Actions so developers do not need a local ZAP installation.

The scan target is **always** `http://127.0.0.1:5000` — the VulnBank instance started inside the CI job. No external or production systems are scanned.

## What is tested?

### OWASP ZAP baseline scan (unauthenticated)

Passive/active baseline scan against the running app, including public endpoints such as `/`, `/health`, `/search/users`, and `/profile/<id>/view`.

ZAP is configured with `-l MEDIUM` so **Medium** and **High** findings fail the job. Narrow **Low**-severity header heuristics are documented in [`zap-baseline.conf`](zap-baseline.conf).

### Python DAST regression script (authenticated)

Full authenticated ZAP automation would require custom OpenAPI scripts and token handling in ZAP. That adds significant complexity for a portfolio API.

**Design decision:** use ZAP for general unauthenticated dynamic scanning, and [`regression_checks.py`](regression_checks.py) for authenticated, remediation-focused API checks against localhost.

| Check | Property verified |
|-------|-------------------|
| `GET /health` | Application reachable |
| `GET /accounts/<id>` without token | Returns 401 |
| Invalid JWT | Returns 401 |
| Alice → Bob's account | IDOR remediated (403) |
| `' OR '1'='1` search | SQL injection remediated |
| Stored XSS payload in profile view | HTML-encoded output |
| £100 → £500 transfer | Insufficient funds enforced (400) |
| `DELETE /health` | Unsupported method returns 405 |

JWTs are obtained via `POST /login` at runtime. Tokens are **not** committed and are **not** printed to logs.

## CI job architecture

The workflow job **PR Security Gate — DAST (OWASP ZAP)** in [`.github/workflows/security.yml`](../../.github/workflows/security.yml):

1. Checks out the repository
2. Sets up Python 3.12 and installs dependencies
3. Starts VulnBank with [`start_ci_server.py`](start_ci_server.py) (SQLite, CI-only secret)
4. Waits for [`wait_for_health.py`](wait_for_health.py) to confirm `GET /health`
5. Runs OWASP ZAP baseline scan via Docker (`--network host`)
6. Runs [`regression_checks.py`](regression_checks.py)
7. Stops the application (even if a step fails)
8. Uploads ZAP reports as workflow artifacts on failure

### CI configuration

| Variable | Purpose |
|----------|---------|
| `DAST_JWT_SECRET_KEY` | Fake CI-only JWT signing secret (not a production credential) |
| `DAST_DATABASE_URL` | Isolated SQLite file under `$RUNNER_TEMP` |
| `DAST_BASE_URL` | `http://127.0.0.1:5000` |

Seeded CI users (`dast_alice`, `dast_bob`) exist only in the ephemeral SQLite database created for the job.

## Accepted / suppressed ZAP findings

See [`zap-baseline.conf`](zap-baseline.conf). Each `IGNORE` rule is:

- **Narrow** — single rule ID, not a whole category
- **Documented** — rationale in the config file
- **CI-scoped** — reflects HTTP localhost lab scanning, not production deployment

Real Medium+ findings in application logic are **not** suppressed and will fail the pipeline.

## Run locally (optional)

Docker is required for the ZAP scan. On Windows/Linux/macOS:

```powershell
# Terminal 1 — start CI-style server
$env:DAST_JWT_SECRET_KEY = "ci-dast-only-secret-not-for-production-use!"
python security/dast/start_ci_server.py

# Terminal 2 — wait, scan, regression checks
python security/dast/wait_for_health.py
docker run --rm --network host -v ${PWD}:/zap/wrk:rw ghcr.io/zaproxy/zaproxy:stable `
  zap-baseline.py -t http://127.0.0.1:5000 `
  -J /zap/wrk/zap-report.json -r /zap/wrk/zap-report.html `
  -c /zap/wrk/security/dast/zap-baseline.conf -l MEDIUM

$env:DAST_JWT_SECRET_KEY = "ci-dast-only-secret-not-for-production-use!"
python security/dast/regression_checks.py
```

If Docker is unavailable, run the server and `regression_checks.py` only; ZAP must be verified in GitHub Actions after push.

## Branch protection

After merge, administrators may add **PR Security Gate — DAST (OWASP ZAP)** as a fifth required status check alongside the existing four security gates.
