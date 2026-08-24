import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_root_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_root_returns_json(client):
    response = client.get("/")
    assert response.is_json


def test_root_contains_name(client):
    response = client.get("/")
    data = response.get_json()
    assert data["name"] == "VulnBank"


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_status(client):
    response = client.get("/health")
    data = response.get_json()
    assert data["status"] == "healthy"
