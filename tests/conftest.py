import pytest

from app import create_app
from app.extensions import db

TEST_JWT_SECRET = "test-secret-key-for-pytest-only-32bytes!"

VALID_USER = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "example-password",
}

ALICE = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "example-password",
}

BOB = {
    "username": "bob",
    "email": "bob@example.com",
    "password": "example-password",
}

CHARLIE = {
    "username": "charlie",
    "email": "charlie@example.com",
    "password": "example-password",
}

# vulnerable-lab branch: xfail secure tests that conflict with intentional flaws
VULNERABLE_LAB = True
VULNERABLE_LAB_XFAIL_TESTS = {
    "test_alice_cannot_access_bob_account",
    "test_bob_cannot_access_alice_account",
    "test_insufficient_funds_rejected",
    "test_failed_transfer_does_not_modify_source_balance",
    "test_failed_transfer_does_not_modify_destination_balance",
    "test_failed_transfer_does_not_create_record",
}


def pytest_collection_modifyitems(config, items):
    if not VULNERABLE_LAB:
        return

    for item in items:
        if item.name in VULNERABLE_LAB_XFAIL_TESTS:
            item.add_marker(
                pytest.mark.xfail(
                    reason="Intentional vulnerability on vulnerable-lab branch",
                    strict=False,
                )
            )


@pytest.fixture
def app():
    """Create a test app with an isolated in-memory database."""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "JWT_SECRET_KEY": TEST_JWT_SECRET,
            "JWT_ALGORITHM": "HS256",
            "JWT_EXPIRATION_SECONDS": 3600,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture
def db_session(app):
    with app.app_context():
        yield db.session


def login(client, email, password):
    response = client.post("/login", json={"email": email, "password": password})
    token = response.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def created_user(client):
    response = client.post("/users", json=VALID_USER)
    return response.get_json()


@pytest.fixture
def auth_headers(client, created_user):
    return login(client, VALID_USER["email"], VALID_USER["password"])


@pytest.fixture
def alice(client):
    response = client.post("/users", json=ALICE)
    user = response.get_json()
    headers = login(client, ALICE["email"], ALICE["password"])
    return {"user": user, "headers": headers}


@pytest.fixture
def bob(client):
    response = client.post("/users", json=BOB)
    user = response.get_json()
    headers = login(client, BOB["email"], BOB["password"])
    return {"user": user, "headers": headers}


@pytest.fixture
def charlie(client):
    response = client.post("/users", json=CHARLIE)
    user = response.get_json()
    headers = login(client, CHARLIE["email"], CHARLIE["password"])
    return {"user": user, "headers": headers}
