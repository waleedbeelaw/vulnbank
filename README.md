# VulnBank

VulnBank is a deliberately vulnerable fintech REST API being developed as an educational Application Security / DevSecOps portfolio project. The goal is to demonstrate secure development practices, vulnerability assessment, and remediation in a realistic API context.

**Current status:** Step 3 — Users and Accounts API. Passwords are hashed before storage. Account numbers are generated server-side. Authentication has not been implemented yet, and intentional vulnerabilities have not been introduced yet.

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

## Database

VulnBank uses **PostgreSQL** as its database. **SQLAlchemy** (via Flask-SQLAlchemy) is used as the ORM.

The database stores three core fintech models:

- **User** — account holders
- **Account** — bank accounts linked to a user
- **Transaction** — records between two accounts (transfers are not implemented yet)

Database credentials are provided through environment variables. A real `.env` file must **never** be committed to version control.

### Configure the database

1. Install and start PostgreSQL locally.
2. Create a database named `vulnbank` (or your preferred name).
3. Copy the example environment file:

```powershell
copy .env.example .env
```

4. Edit `.env` and set `DATABASE_URL` to your local PostgreSQL connection string:

```
DATABASE_URL=postgresql://username:password@localhost:5432/vulnbank
```

Replace `username`, `password`, and the database name with your local values.

### Initialise database tables

After configuring `.env`, create the tables:

```powershell
python init_db.py
```

This runs `db.create_all()` to create the `users`, `accounts`, and `transactions` tables.

## Run the application

```powershell
python run.py
```

The API will be available at `http://127.0.0.1:5000`.

If `DATABASE_URL` is missing, the application will fail with a clear error message.

## Run tests

```powershell
pytest
```

Tests use an isolated in-memory SQLite database, so they do not require PostgreSQL or real credentials.

## Security baseline (Step 3)

The current API follows secure baseline practices:

- Passwords are hashed with Werkzeug before storage
- Plaintext passwords and password hashes are never returned in API responses
- Account numbers are generated server-side
- Balances use `Decimal` / `Numeric` rather than floating point
- Input is validated before database operations
- SQLAlchemy ORM is used for parameterised queries

Authentication (JWT or session-based) is **not** implemented yet. Any user can call any endpoint. Intentional vulnerabilities will be added in later steps.

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
| user_id  | Required, must reference an existing user  |
| currency | Required, must be `GBP`, `EUR`, or `USD`     |

Clients cannot set `account_number`, `balance`, or `created_at`.

## Endpoints

| Method | Path                    | Description                          |
|--------|-------------------------|--------------------------------------|
| GET    | `/`                     | API name and online status           |
| GET    | `/health`               | Health check                         |
| POST   | `/users`                | Create a user                        |
| GET    | `/users/<id>`           | Get a user by ID                     |
| POST   | `/accounts`             | Create an account for a user         |
| GET    | `/accounts/<id>`        | Get an account by ID                 |
| GET    | `/users/<id>/accounts`  | List all accounts for a user         |

## Example requests

### Create a user

```http
POST /users
Content-Type: application/json

{
    "username": "alice",
    "email": "alice@example.com",
    "password": "example-password"
}
```

Response (`201 Created`):

```json
{
    "id": 1,
    "username": "alice",
    "email": "alice@example.com"
}
```

### Get a user

```http
GET /users/1
```

Response (`200 OK`):

```json
{
    "id": 1,
    "username": "alice",
    "email": "alice@example.com"
}
```

### Create an account

```http
POST /accounts
Content-Type: application/json

{
    "user_id": 1,
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

### List a user's accounts

```http
GET /users/1/accounts
```

Response (`200 OK`):

```json
[
    {
        "id": 1,
        "user_id": 1,
        "account_number": "VB1234567890",
        "balance": "0.00",
        "currency": "GBP"
    }
]
```

Returns an empty list (`[]`) if the user exists but has no accounts.
