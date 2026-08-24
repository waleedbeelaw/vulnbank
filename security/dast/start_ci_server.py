"""Start VulnBank for CI/DAST with an isolated SQLite database.

Uses fake CI-only credentials from environment variables. Never use this
configuration outside isolated test/CI environments.
"""

import os
import sys
from decimal import Decimal
from pathlib import Path

from werkzeug.security import generate_password_hash

# Ensure repository root is on sys.path when run as a script.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app import create_app
from app.extensions import db
from app.models import Account, User

CI_JWT_SECRET = os.environ.get(
    "DAST_JWT_SECRET_KEY",
    "ci-dast-only-secret-not-for-production-use!",
)
_DEFAULT_DB_DIR = os.environ.get("RUNNER_TEMP") or os.environ.get("TEMP") or "/tmp"
CI_DATABASE_URL = os.environ.get(
    "DAST_DATABASE_URL",
    f"sqlite:///{Path(_DEFAULT_DB_DIR) / 'vulnbank_dast.sqlite'}",
)
HOST = os.environ.get("DAST_HOST", "127.0.0.1")
PORT = int(os.environ.get("DAST_PORT", "5000"))

DAST_FIXTURES = (
    {
        "username": "dast_alice",
        "email": "dast-alice@example.com",
        "password": "dast-example-password",
        "account_number": "VBDASTALICE001",
        "balance": Decimal("100.00"),
    },
    {
        "username": "dast_bob",
        "email": "dast-bob@example.com",
        "password": "dast-example-password",
        "account_number": "VBDASTBOB00001",
        "balance": Decimal("0.00"),
    },
)


def _remove_sqlite_file(database_url: str) -> None:
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "", 1)
        path = Path(db_path)
        if path.exists():
            path.unlink()


def seed_dast_fixtures() -> None:
    """Seed CI-only users and accounts for authenticated DAST checks."""
    for fixture in DAST_FIXTURES:
        user = User.query.filter_by(email=fixture["email"]).first()
        if user is None:
            user = User(
                username=fixture["username"],
                email=fixture["email"],
                password_hash=generate_password_hash(fixture["password"]),
            )
            db.session.add(user)
            db.session.flush()

        account = Account.query.filter_by(user_id=user.id).first()
        if account is None:
            account = Account(
                user_id=user.id,
                account_number=fixture["account_number"],
                balance=fixture["balance"],
                currency="GBP",
            )
            db.session.add(account)
        else:
            account.balance = fixture["balance"]

    db.session.commit()


def create_ci_app():
    database_url = CI_DATABASE_URL
    _remove_sqlite_file(database_url)

    app = create_app(
        {
            "TESTING": False,
            "SQLALCHEMY_DATABASE_URI": database_url,
            "JWT_SECRET_KEY": CI_JWT_SECRET,
            "JWT_ALGORITHM": "HS256",
            "JWT_EXPIRATION_SECONDS": 3600,
        }
    )

    with app.app_context():
        db.create_all()
        seed_dast_fixtures()

    return app


if __name__ == "__main__":
    application = create_ci_app()
    application.run(host=HOST, port=PORT, debug=False, use_reloader=False)
