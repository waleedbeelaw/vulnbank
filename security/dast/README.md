# Dynamic Application Security Testing (DAST)

## What is DAST?

**Dynamic Application Security Testing** exercises a **running** application from the outside, sending real HTTP requests and observing responses. It complements:

| Technique | When it runs | What it inspects |
|-----------|--------------|------------------|
| **SAST** (Bandit) | Build time | Source code |
| **SCA** (pip-audit) | Build time | Dependencies |
| **DAST** (OWASP ZAP + regression script) | Run time | Live HTTP behaviour on localhost |

DAST can reveal issues visible only when components interact - routing, authentication enforcement, response encoding, and server configuration - that static analysis may miss.

## Why OWASP ZAP?

[OWASP ZAP](https://www.zaproxy.org/) is an open-source DAST tool widely used in DevSecOps pipelines. VulnBank runs ZAP from the official container image (`ghcr.io/zaproxy/zaproxy:stable`) in GitHub Actions so developers do not need a local ZAP installation.

The scan target is **always** `http://127.0.0.1:5000` - the VulnBank instance started inside the CI job. No external or production systems are scanned.

## What is tested?

VulnBank DAST uses **two complementary layers**:

1. **OWASP ZAP baseline** - unauthenticated spidering and **passive** scanning
2. **`regression_checks.py`** - targeted authenticated HTTP checks for previously remediated flaws

### OWASP ZAP baseline scan (spider + passive only)

`zap-baseline.py` is **not** a full active vulnerability scan. It:

1. Spiders the target URL to discover linked resources (including `/profile/<id>/view` HTML)
2. Runs **passive** scan rules against observed traffic
3. Reports findings according to [`zap-baseline.conf`](zap-baseline.conf)

It does **not** actively inject SQL injection, path traversal, or XSS attack payloads. Rules in the config file marked **FAIL** for active-scan rule IDs (e.g. SQL injection) do **not** mean ZAP baseline performs those attacks - they would only fail CI if passive analysis somehow raised that alert. In practice, baseline blocking relies on passive findings such as **stored XSS** in HTML responses and **application error disclosure**.

Browser security header gaps (X-Frame-Options, X-Content-Type-Options, Content-Security-Policy, Cache-Control, server version disclosure) are **not** globally suppressed. With `-I`, they appear as **WARN** in ZAP reports for visibility - relevant because VulnBank serves an HTML profile view - but they do not block the PR gate.

#### Rule actions and CI failure (`-I`)

| Action | CI effect (with `-I`) |
|--------|------------------------|
| **FAIL** | Finding fails the job (exit code 1) - blocks the PR security gate |
| **WARN** | Reported in output/reports but does **not** fail CI |
| **IGNORE** | Suppressed - only for findings genuinely inapplicable to localhost CI |

The workflow runs `zap-baseline.py` with **`-I`** (*do not return failure on warning*). Unlisted rules default to **WARN** and remain visible without blocking merge.

**Note:** `-l` sets the minimum *rule action level to display* (`PASS`, `IGNORE`, `INFO`, `WARN`, `FAIL`) - it is **not** a CVSS/severity threshold. Do not pass values such as `MEDIUM`; they cause exit code 3.

#### IGNORE rules (narrow)

| Rule | Why IGNORE is justified |
|------|-------------------------|
| 10035 HSTS | CI scans `http://127.0.0.1` only - no TLS |
| 10096 Timestamp disclosure | Intentional `created_at` fields in JSON API responses |
| 10202 Anti-CSRF | Stateless JWT Bearer API - not cookie-form CSRF |

#### FAIL rules (passive gate)

| Rule | Why it blocks CI |
|------|------------------|
| 40014 Stored XSS | Passive detection of unencoded HTML in spidered pages (e.g. profile view) |
| 90022 Application error disclosure | Passive detection of stack traces or debug errors in responses |

### Python DAST regression script (authenticated, targeted)

Full authenticated ZAP automation would require custom OpenAPI scripts and token handling in ZAP. That adds significant complexity for a portfolio API.

**Design decision:** ZAP baseline handles unauthenticated spidering and passive analysis; [`regression_checks.py`](regression_checks.py) performs **targeted dynamic HTTP checks** for the four remediated vulnerability classes:

| Check | Remediated flaw |
|-------|-----------------|
| `GET /health` | Application reachable |
| `GET /accounts/<id>` without token | Authentication enforced (401) |
| Invalid JWT | Token validation (401) |
| Alice → Bob's account | **IDOR / BOLA** (403) |
| `' OR '1'='1` search | **SQL injection** (no broad result leak) |
| Stored XSS payload in profile view | **Stored XSS** (HTML-encoded output) |
| £100 → £500 transfer | **Business logic / insufficient funds** (400) |
| `DELETE /health` | Unsupported method handling (405) |

These checks **actively send crafted requests** (including the SQLi PoC and XSS payload) via normal HTTP APIs. ZAP baseline alone does **not** perform these authenticated or payload-driven tests.

JWTs are obtained via `POST /login` at runtime. Tokens are **not** committed and are **not** printed to logs.

## CI job architecture

The workflow job **PR Security Gate - DAST (OWASP ZAP)** in [`.github/workflows/security.yml`](../../.github/workflows/security.yml):

1. Checks out the repository
2. Sets up Python 3.12 and installs dependencies
3. Starts VulnBank with [`start_ci_server.py`](start_ci_server.py) (SQLite, CI-only secret)
4. Waits for [`wait_for_health.py`](wait_for_health.py) to confirm `GET /health`
5. Runs OWASP ZAP baseline scan via Docker (`--network host`) - spider + passive only
6. Runs [`regression_checks.py`](regression_checks.py) - targeted authenticated checks
7. Stops the application (even if a step fails)
8. Uploads ZAP reports as workflow artifacts on failure

### CI configuration

| Variable | Purpose |
|----------|---------|
| `DAST_JWT_SECRET_KEY` | Fake CI-only JWT signing secret (not a production credential) |
| `DAST_DATABASE_URL` | Isolated SQLite file under `$RUNNER_TEMP` |
| `DAST_BASE_URL` | `http://127.0.0.1:5000` |

Seeded CI users (`dast_alice`, `dast_bob`) exist only in the ephemeral SQLite database created for the job.

## Run locally (optional)

Docker is required for the ZAP scan. On Windows/Linux/macOS:

```powershell
# Terminal 1 - start CI-style server
$env:DAST_JWT_SECRET_KEY = "ci-dast-only-secret-not-for-production-use!"
python security/dast/start_ci_server.py

# Terminal 2 - wait, scan, regression checks
python security/dast/wait_for_health.py
docker run --rm --network host -v ${PWD}:/zap/wrk:rw ghcr.io/zaproxy/zaproxy:stable `
  zap-baseline.py -t http://127.0.0.1:5000 `
  -J /zap/wrk/zap-report.json -r /zap/wrk/zap-report.html `
  -w /zap/wrk/zap-report.md `
  -c /zap/wrk/security/dast/zap-baseline.conf -I

$env:DAST_JWT_SECRET_KEY = "ci-dast-only-secret-not-for-production-use!"
python security/dast/regression_checks.py
```

If Docker is unavailable, run the server and `regression_checks.py` only; ZAP must be verified in GitHub Actions after push.

## Branch protection

After merge, administrators may add **PR Security Gate - DAST (OWASP ZAP)** as a fifth required status check alongside the existing four security gates.
