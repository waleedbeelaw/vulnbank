import pytest
from werkzeug.security import check_password_hash

from app.models import User

VALID_USER = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "example-password",
}


def test_create_user_successfully(client):
    response = client.post("/users", json=VALID_USER)

    assert response.status_code == 201
    data = response.get_json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"
    assert "id" in data


def test_password_is_stored_hashed(client, db_session):
    client.post("/users", json=VALID_USER)

    user = db_session.query(User).filter_by(username="alice").one()
    assert user.password_hash != VALID_USER["password"]
    assert check_password_hash(user.password_hash, VALID_USER["password"])


def test_password_hash_not_returned_on_create(client):
    response = client.post("/users", json=VALID_USER)
    data = response.get_json()

    assert "password" not in data
    assert "password_hash" not in data


def test_missing_username_rejected(client):
    payload = {"email": "alice@example.com", "password": "example-password"}
    response = client.post("/users", json=payload)

    assert response.status_code == 400
    assert "username is required" in response.get_json()["errors"]


def test_missing_email_rejected(client):
    payload = {"username": "alice", "password": "example-password"}
    response = client.post("/users", json=payload)

    assert response.status_code == 400
    assert "email is required" in response.get_json()["errors"]


def test_missing_password_rejected(client):
    payload = {"username": "alice", "email": "alice@example.com"}
    response = client.post("/users", json=payload)

    assert response.status_code == 400
    assert "password is required" in response.get_json()["errors"]


def test_duplicate_username_rejected(client):
    client.post("/users", json=VALID_USER)

    duplicate = {
        "username": "alice",
        "email": "other@example.com",
        "password": "example-password",
    }
    response = client.post("/users", json=duplicate)

    assert response.status_code == 409
    assert response.get_json()["error"] == "username already exists"


def test_duplicate_email_rejected(client):
    client.post("/users", json=VALID_USER)

    duplicate = {
        "username": "otheruser",
        "email": "alice@example.com",
        "password": "example-password",
    }
    response = client.post("/users", json=duplicate)

    assert response.status_code == 409
    assert response.get_json()["error"] == "email already exists"


def test_get_user_returns_correct_user(client, created_user):
    response = client.get(f"/users/{created_user['id']}")

    assert response.status_code == 200
    data = response.get_json()
    assert data == created_user
    assert "password_hash" not in data


def test_get_user_returns_404_for_nonexistent_user(client):
    response = client.get("/users/999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"
