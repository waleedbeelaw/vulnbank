# VulnBank

VulnBank is a deliberately vulnerable fintech REST API being developed as an educational Application Security / DevSecOps portfolio project. The goal is to demonstrate secure development practices, vulnerability assessment, and remediation in a realistic API context.

**Current status:** Step 4 — JWT authentication and authorisation. Protected endpoints require a valid Bearer token. Users can only access their own accounts and profile. Intentional vulnerabilities have **not** been introduced yet.

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
- **Transaction** — records between two accounts (transfers are not implemented yet)

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

## Run tests

```powershell
pytest
```

Tests use an isolated in-memory SQLite database and a test JWT secret, so they do not require PostgreSQL or real credentials.

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

The current user is always determined from the JWT `sub` claim, never from request body parameters.

## Security design (Step 4)

- Passwords hashed with Werkzeug before storage
- JWT signed with `HS256` using `JWT_SECRET_KEY` from environment
- Explicit algorithm allow-list during verification (no algorithm confusion)
- Unsigned tokens are rejected
- Token expiration enforced
- No passwords, password hashes, or secrets in API responses
- Generic login failure messages (no account enumeration)
- Server-generated account numbers
- `Decimal` / `Numeric` for financial values
- SQLAlchemy ORM for parameterised queries

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

## Endpoints

| Method | Path                    | Auth     | Description                    |
|--------|-------------------------|----------|--------------------------------|
| GET    | `/`                     | No       | API name and online status     |
| GET    | `/health`               | No       | Health check                   |
| POST   | `/users`                | No       | Create a user                  |
| POST   | `/login`                | No       | Obtain a JWT                   |
| GET    | `/users/<id>`           | Required | Get your own user profile      |
| POST   | `/accounts`             | Required | Create an account for yourself |
| GET    | `/accounts/<id>`        | Required | Get your own account           |
| GET    | `/users/<id>/accounts`  | Required | List your own accounts         |

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
