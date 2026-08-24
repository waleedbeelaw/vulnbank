# VulnBank

VulnBank is a deliberately vulnerable fintech REST API being developed as an educational Application Security / DevSecOps portfolio project. The goal is to demonstrate secure development practices, vulnerability assessment, and remediation in a realistic API context.

**Current status:** Step 5 — secure money transfers. Authenticated users can transfer funds between accounts with atomic balance updates, ownership checks, and currency validation. Intentional vulnerabilities have **not** been introduced yet.

## Setup (Windows)

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Environment variables

Copy the example environment file:

```powershell
copy .env.example .env
```

Edit `.env` and set:

```
DATABASE_URL=postgresql://username:password@localhost:5432/vulnbank
JWT_SECRET_KEY=replace-with-a-long-random-secret-key
```

| Variable         | Purpose                                      |
|------------------|----------------------------------------------|
| `DATABASE_URL`   | PostgreSQL connection string                 |
| `JWT_SECRET_KEY` | Secret used to sign and verify JWT tokens    |

A real `.env` file must **never** be committed to version control.

If either variable is missing, the application fails with a clear error message.

## Database

VulnBank uses **PostgreSQL** as its database. **SQLAlchemy** (via Flask-SQLAlchemy) is used as the ORM.

The database stores three core fintech models:

- **User** — account holders
- **Account** — bank accounts linked to a user
- **Transaction** — transfer records between two accounts

### Initialise database tables

After configuring `.env`, create the tables:

```powershell
python init_db.py
```

## Run the application

```powershell
python run.py
```

The API will be available at `http://127.0.0.1:5000`.

## Docker

Run VulnBank with Docker Compose (requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine + Compose).

### Prerequisites

- Docker with Compose v2
- Port `5000` available on localhost

### Quick start (one command)

```powershell
docker compose up --build
```

The entrypoint runs `init_db.py` automatically after PostgreSQL is healthy. Verify:

```powershell
curl http://localhost:5000/health
```

Expected: `{"status":"healthy"}`

### Step-by-step (explicit database init)

```powershell
docker compose up -d db
docker compose run --rm app python init_db.py
docker compose up app
```

### Stop containers

```powershell
docker compose down
```

### Reset development database

Removes the PostgreSQL volume and all container data:

```powershell
docker compose down -v
docker compose up --build
```

### Development-only credentials

`docker-compose.yml` uses fake credentials (`vulnbank-dev-password`, `docker-dev-jwt-secret-not-for-production-use`). **Do not use these in production.** PostgreSQL is not exposed to the host — only the app port `5000` is published.

See [security/container-security.md](security/container-security.md) for container security decisions.

## Run tests

```powershell
pytest
```

Tests use an isolated in-memory SQLite database and a test JWT secret, so they do not require PostgreSQL or real credentials.

## DevSecOps / CI Security

Every push to `vulnerable-lab` and every pull request targeting `vulnerable-lab` triggers the GitHub Actions workflow in `.github/workflows/security.yml`. The pipeline is designed to catch security regressions before merge:

| Job | Tool | Purpose |
|-----|------|---------|
| Python Test Suite | pytest | Run the full test suite, including vulnerability remediation regression tests |
| SAST (Bandit) | Bandit | Static analysis of `app/` for common Python security issues |
| Dependency Vulnerability Scan | pip-audit | Check declared dependencies in `requirements.txt` against known CVEs |
| Secret Scanning | Gitleaks | Detect accidentally committed credentials or secrets |
| DAST | OWASP ZAP | Dynamic scan of the running application on localhost plus authenticated regression checks |
| Container Scan | Trivy | Blocks **fixable** HIGH/CRITICAL vulnerabilities in the built Docker image |
| SBOM | Syft (Anchore SBOM Action) | Generates and validates a CycloneDX inventory from the built container image |

See [security/supply-chain-security.md](security/supply-chain-security.md) for SBOM purpose, CI flow, and limitations.

Run the same checks locally:

```powershell
pip install -r requirements-dev.txt
pytest -v
bandit -r app/ -ll
pip-audit -r requirements.txt
```

DAST requires Docker for the ZAP scan. See [security/dast/README.md](security/dast/README.md) for local instructions.

## Pull Request Security Gate

VulnBank uses a **security-gated pull request workflow** on the `vulnerable-lab` branch. The GitHub Actions workflow in `.github/workflows/security.yml` runs automatically on:

- **Pushes** to `vulnerable-lab`
- **Pull requests** targeting `vulnerable-lab`

Each pull request should pass all seven security checks before it is considered approved for merge:

| Check | Tool | What it verifies |
|-------|------|------------------|
| PR Security Gate — Test Suite (pytest) | pytest | Functional behaviour and security regression tests (107 tests) |
| PR Security Gate — SAST (Bandit) | Bandit | Python source in `app/` for common security anti-patterns |
| PR Security Gate — SCA (pip-audit) | pip-audit | Declared dependencies in `requirements.txt` against known CVEs |
| PR Security Gate — Secret Scan (Gitleaks) | Gitleaks | Repository history for accidentally committed credentials |
| PR Security Gate — DAST (OWASP ZAP) | OWASP ZAP | Dynamic scan of running localhost app and authenticated remediation checks |
| PR Security Gate — Container Scan (Trivy) | Trivy | Blocks fixable HIGH/CRITICAL container vulnerabilities |
| PR Security Gate — SBOM (Syft) | Syft | Builds the container image, generates a CycloneDX SBOM with Syft, validates the inventory, and retains it as a CI artifact |

If any check fails, the workflow fails and the pull request is **not** security-approved. Review the failing job in the GitHub Actions tab, fix the issue, and push again.

### Enforcing the gate with branch protection

The CI pipeline reports status on pull requests, but **merge blocking requires branch protection** configured by a repository administrator in GitHub (**Settings → Branches**). See [SECURITY.md — Branch Protection and Security Gates](SECURITY.md#branch-protection-and-security-gates) for the recommended rule: require a pull request, require all seven **PR Security Gate** status checks, keep branches up to date, and restrict direct pushes where appropriate.

Until branch protection is enabled, checks run and report results but GitHub may still allow a merge when checks fail.

## Security policy and documentation

VulnBank documents its security governance alongside technical controls:

| Document | Purpose |
|----------|---------|
| [SECURITY.md](SECURITY.md) | Vulnerability reporting, responsible disclosure, and project scope |
| [security/dependency-management.md](security/dependency-management.md) | Dependency scanning with pip-audit and upgrade workflow |
| [security/supply-chain-security.md](security/supply-chain-security.md) | SBOM generation (Syft/CycloneDX), supply-chain controls, and CI artifacts |
| [security/assessment.md](security/assessment.md) | Step 7 application security assessment |
| [security/remediation.md](security/remediation.md) | Step 8 vulnerability remediation summary |
| [security/README.md](security/README.md) | Security documentation index and lifecycle overview |

## Authentication

VulnBank uses **JWT (JSON Web Token)** authentication via the PyJWT library.

### Login

```http
POST /login
Content-Type: application/json

{
    "email": "alice@example.com",
    "password": "example-password"
}
```

Response (`200 OK`):

```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

Invalid credentials return `401` with a generic message that does not reveal whether the email exists:

```json
{
    "error": "Invalid credentials"
}
```

### Using a token

Send the token in the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

Tokens expire after 1 hour. Expired or invalid tokens return `401`.

## Authorisation

Authentication (who you are) and authorisation (what you can access) are handled separately.

### Protected endpoints

These endpoints require a valid JWT:

| Method | Path                    |
|--------|-------------------------|
| GET    | `/users/<id>`           |
| GET    | `/users/<id>/accounts`  |
| POST   | `/accounts`             |
| GET    | `/accounts/<id>`        |
| POST   | `/transactions`         |
| GET    | `/transactions/<id>`    |
| GET    | `/accounts/<id>/transactions` |

### Public endpoints

| Method | Path        | Notes                    |
|--------|-------------|--------------------------|
| GET    | `/`         | API status               |
| GET    | `/health`   | Health check             |
| POST   | `/users`    | User registration        |
| POST   | `/login`    | Obtain a JWT             |

### Ownership rules

- `GET /users/<id>` — users can only view their **own** profile (`403` for other users)
- `GET /users/<id>/accounts` — users can only list **their own** accounts (`403` for other users)
- `GET /accounts/<id>` — users can only view **their own** accounts (`403` for other users)
- `POST /accounts` — account is always created for the **authenticated user**; any `user_id` in the request body is ignored
- `POST /transactions` — authenticated user must **own the source account**; destination may belong to another user
- `GET /transactions/<id>` — only the sender or recipient can view a transaction
- `GET /accounts/<id>/transactions` — only the account owner can view transaction history

The current user is always determined from the JWT `sub` claim, never from request body parameters.

## Transactions

Authenticated users can transfer money between accounts.

### Create a transfer

```http
POST /transactions
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": "100.00",
    "currency": "GBP"
}
```

Response (`201 Created`):

```json
{
    "id": 1,
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": "100.00",
    "currency": "GBP",
    "created_at": "2026-08-24T12:00:00+00:00"
}
```

### Transfer rules

- JWT authentication is required
- The authenticated user must own the **source** account
- The destination account may belong to another user
- Source, destination, and request currency must all match (no conversion yet)
- Amount must be greater than zero
- Source account must have sufficient funds
- Source and destination must be different accounts
- Transfers are **atomic** — balance updates and the transaction record commit or roll back together
- Row locking on the source account prevents concurrent double-spending

### Get a transaction

```http
GET /transactions/1
Authorization: Bearer <access_token>
```

Only the sender or recipient can view the transaction. Unrelated users receive `403`. Nonexistent transactions return `404`.

### Account transaction history

```http
GET /accounts/1/transactions
Authorization: Bearer <access_token>
```

Returns all transactions where the account is either the source or destination. Only the account owner can access this endpoint.

## Security design (Steps 4–5)

- Passwords hashed with Werkzeug before storage
- JWT signed with `HS256` using `JWT_SECRET_KEY` from environment
- Explicit algorithm allow-list during verification (no algorithm confusion)
- Unsigned tokens are rejected
- Token expiration enforced
- No passwords, password hashes, or secrets in API responses
- Generic login failure messages (no account enumeration)
- Server-generated account numbers
- `Decimal` / `Numeric` for financial values (no Python float for money)
- SQLAlchemy ORM for parameterised queries
- Database transactions with row locking for transfer atomicity
- Generic error responses (no stack traces exposed to clients)

Intentional vulnerabilities (IDOR, broken auth, SQL injection, etc.) will be added in later steps for security testing demonstrations.

## Validation rules

### Users

| Field    | Rules                                      |
|----------|--------------------------------------------|
| username | Required, max 80 characters, unique        |
| email    | Required, max 120 characters, valid format, unique |
| password | Required, minimum 8 characters             |

### Accounts

| Field    | Rules                                      |
|----------|--------------------------------------------|
| currency | Required, must be `GBP`, `EUR`, or `USD`   |

Clients cannot set `user_id`, `account_number`, `balance`, or `created_at`.

### Transactions

| Field             | Rules                                              |
|-------------------|----------------------------------------------------|
| from_account_id   | Required, must exist, must be owned by JWT user    |
| to_account_id     | Required, must exist, must differ from source      |
| amount            | Required, must be > 0, parsed as Decimal           |
| currency          | Required, must match both account currencies       |

## Endpoints

| Method | Path                          | Auth     | Description                         |
|--------|-------------------------------|----------|-------------------------------------|
| GET    | `/`                           | No       | API name and online status          |
| GET    | `/health`                     | No       | Health check                        |
| POST   | `/users`                      | No       | Create a user                       |
| POST   | `/login`                      | No       | Obtain a JWT                        |
| GET    | `/users/<id>`                 | Required | Get your own user profile           |
| POST   | `/accounts`                   | Required | Create an account for yourself      |
| GET    | `/accounts/<id>`              | Required | Get your own account                |
| GET    | `/users/<id>/accounts`        | Required | List your own accounts              |
| POST   | `/transactions`               | Required | Transfer money from your account    |
| GET    | `/transactions/<id>`          | Required | View a transaction you sent/received |
| GET    | `/accounts/<id>/transactions` | Required | List transactions for your account  |

## Example workflow

### 1. Create a user

```http
POST /users
Content-Type: application/json

{
    "username": "alice",
    "email": "alice@example.com",
    "password": "example-password"
}
```

### 2. Log in

```http
POST /login
Content-Type: application/json

{
    "email": "alice@example.com",
    "password": "example-password"
}
```

### 3. Create an account (authenticated)

```http
POST /accounts
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "currency": "GBP"
}
```

Response (`201 Created`):

```json
{
    "id": 1,
    "user_id": 1,
    "account_number": "VB1234567890",
    "balance": "0.00",
    "currency": "GBP"
}
```

### 4. List your accounts

```http
GET /users/1/accounts
Authorization: Bearer <access_token>
```

### 5. Transfer money

```http
POST /transactions
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": "50.00",
    "currency": "GBP"
}
```

### 6. View transaction history

```http
GET /accounts/1/transactions
Authorization: Bearer <access_token>
```
