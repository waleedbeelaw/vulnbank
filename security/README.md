# VulnBank Security Lab

This directory documents the **intentionally vulnerable** version of VulnBank running on the `vulnerable-lab` Git branch.

## Purpose

The vulnerable lab exists for **local educational AppSec testing only**. It supports:

- Manual vulnerability verification
- Code review practice
- Future SAST/DAST tool evaluation (Step 9)
- Remediation and regression testing

## SECURE BASELINE vs VULNERABLE LAB

| Branch           | Purpose                                      |
|------------------|----------------------------------------------|
| `main`           | Secure baseline — no intentional flaws       |
| `vulnerable-lab` | Intentional vulnerabilities for local testing |

**Never deploy `vulnerable-lab` to a public environment.**

## Current vulnerabilities

| ID | Name            | Endpoint(s)                          | File                                      |
|----|-----------------|--------------------------------------|-------------------------------------------|
| 1  | IDOR / BOLA     | `GET /accounts/<id>`                 | `app/routes/accounts.py`                  |
| 2  | SQL Injection   | `GET /search/users?q=`               | `app/routes/search.py`                    |
| 3  | Stored XSS      | `PUT /users/me/profile`, `GET /profile/<id>/view` | `app/routes/profile.py`      |
| 4  | Business Logic  | `POST /transactions`                 | `app/services/transactions.py`              |

See `security/vulnerabilities/` for detailed reports.

## Running locally

```powershell
cd C:\Users\main\Desktop\VulnBank
git checkout vulnerable-lab
.venv\Scripts\activate
pip install -r requirements.txt
python init_db.py
python run.py
```

The API runs at `http://127.0.0.1:5000`.

## Running tests

```powershell
pytest
```

- **Regression tests** (Steps 1–5) should continue to pass, except tests marked `xfail` where they conflict with intentional flaws.
- **Vulnerability tests** in `tests/test_vulnerabilities.py` demonstrate insecure behaviour and should **fail after remediation**.

## Resetting the local database

If you need a clean database:

1. Drop and recreate the PostgreSQL database `vulnbank`, or
2. Connect with psql and run `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`
3. Run `python init_db.py` again

For tests, pytest uses an in-memory SQLite database automatically — no reset needed.

## Safety rules

- Localhost only
- No real credentials in the repository
- No destructive SQL payloads in documentation or tests
- No malware, token theft, or external targeting
- Do not push this branch unless explicitly required for your lab setup

## Remediation workflow (future steps)

1. Read the vulnerability report in `security/vulnerabilities/`
2. Fix the root cause in code
3. Confirm the vulnerability test now fails (expects secure behaviour)
4. Remove the `xfail` marker from conflicting regression tests
5. Re-run the full test suite
