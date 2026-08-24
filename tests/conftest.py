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
