# VulnBank

VulnBank is a deliberately vulnerable fintech REST API being developed as an educational Application Security / DevSecOps portfolio project. The goal is to demonstrate secure development practices, vulnerability assessment, and remediation in a realistic API context.

**Current status:** Step 2 — PostgreSQL database foundation with User, Account, and Transaction models. Root and health endpoints from Step 1 are unchanged. No authentication, payments, or intentional vulnerabilities have been added yet.

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

## Endpoints

| Method | Path      | Description                |
|--------|-----------|----------------------------|
| GET    | `/`       | API name and online status |
| GET    | `/health` | Health check               |
