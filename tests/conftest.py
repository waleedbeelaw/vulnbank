import pytest

from app import create_app
from app.extensions import db

VALID_USER = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "example-password",
}


@pytest.fixture
def app():
    """Create a test app with an isolated in-memory database."""
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
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


@pytest.fixture
def created_user(client):
    response = client.post("/users", json=VALID_USER)
    return response.get_json()
