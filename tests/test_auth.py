from datetime import datetime, timedelta, timezone

import jwt


def test_valid_credentials_return_token(client, created_user):
    response = client.post(
        "/login",
        json={"email": "alice@example.com", "password": "example-password"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert "access_token" in data
    assert isinstance(data["access_token"], str)
    assert data["access_token"]


def test_incorrect_password_returns_401(client, created_user):
    response = client.post(
        "/login",
        json={"email": "alice@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid credentials"}


def test_unknown_email_returns_401(client):
    response = client.post(
        "/login",
        json={"email": "missing@example.com", "password": "example-password"},
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Invalid credentials"}


def test_missing_email_returns_400(client):
    response = client.post("/login", json={"password": "example-password"})

    assert response.status_code == 400
    assert "email is required" in response.get_json()["errors"]


def test_missing_password_returns_400(client):
    response = client.post("/login", json={"email": "alice@example.com"})

    assert response.status_code == 400
    assert "password is required" in response.get_json()["errors"]


def test_password_hash_never_returned_on_login(client, created_user):
    response = client.post(
        "/login",
        json={"email": "alice@example.com", "password": "example-password"},
    )
    data = response.get_json()

    assert "password" not in data
    assert "password_hash" not in data


def test_login_does_not_reveal_account_existence(client, created_user):
    wrong_password = client.post(
        "/login",
        json={"email": "alice@example.com", "password": "wrong-password"},
    )
    unknown_email = client.post(
        "/login",
        json={"email": "missing@example.com", "password": "example-password"},
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.get_json() == unknown_email.get_json()


def test_get_account_without_token_returns_401(client, created_user, auth_headers):
    create_response = client.post(
        "/accounts",
        json={"currency": "GBP"},
        headers=auth_headers,
    )
    account_id = create_response.get_json()["id"]

    response = client.get(f"/accounts/{account_id}")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_get_user_accounts_without_token_returns_401(client, created_user):
    response = client.get(f"/users/{created_user['id']}/accounts")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_post_accounts_without_token_returns_401(client):
    response = client.post("/accounts", json={"currency": "GBP"})

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_alice_can_access_alice_account(client, alice, bob):
    alice_account = client.post(
        "/accounts",
        json={"currency": "GBP"},
        headers=alice["headers"],
    ).get_json()

    response = client.get(
        f"/accounts/{alice_account['id']}",
        headers=alice["headers"],
    )

    assert response.status_code == 200
    assert response.get_json()["id"] == alice_account["id"]


def test_alice_cannot_access_bob_account(client, alice, bob):
    bob_account = client.post(
        "/accounts",
        json={"currency": "GBP"},
        headers=bob["headers"],
    ).get_json()

    response = client.get(
        f"/accounts/{bob_account['id']}",
        headers=alice["headers"],
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Forbidden"


def test_bob_can_access_bob_account(client, alice, bob):
    bob_account = client.post(
        "/accounts",
        json={"currency": "EUR"},
        headers=bob["headers"],
    ).get_json()

    response = client.get(
        f"/accounts/{bob_account['id']}",
        headers=bob["headers"],
    )

    assert response.status_code == 200
    assert response.get_json()["user_id"] == bob["user"]["id"]


def test_bob_cannot_access_alice_account(client, alice, bob):
    alice_account = client.post(
        "/accounts",
        json={"currency": "USD"},
        headers=alice["headers"],
    ).get_json()

    response = client.get(
        f"/accounts/{alice_account['id']}",
        headers=bob["headers"],
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Forbidden"


def test_alice_cannot_create_account_for_bob(client, alice, bob):
    response = client.post(
        "/accounts",
        json={"user_id": bob["user"]["id"], "currency": "GBP"},
        headers=alice["headers"],
    )

    assert response.status_code == 201
    assert response.get_json()["user_id"] == alice["user"]["id"]


def test_bob_cannot_create_account_for_alice(client, alice, bob):
    response = client.post(
        "/accounts",
        json={"user_id": alice["user"]["id"], "currency": "GBP"},
        headers=bob["headers"],
    )

    assert response.status_code == 201
    assert response.get_json()["user_id"] == bob["user"]["id"]


def test_alice_can_only_retrieve_alice_accounts(client, alice, bob):
    client.post("/accounts", json={"currency": "GBP"}, headers=alice["headers"])
    client.post("/accounts", json={"currency": "EUR"}, headers=bob["headers"])

    response = client.get(
        f"/users/{alice['user']['id']}/accounts",
        headers=alice["headers"],
    )

    assert response.status_code == 200
    accounts = response.get_json()
    assert len(accounts) == 1
    assert accounts[0]["user_id"] == alice["user"]["id"]


def test_bob_can_only_retrieve_bob_accounts(client, alice, bob):
    client.post("/accounts", json={"currency": "GBP"}, headers=alice["headers"])
    client.post("/accounts", json={"currency": "USD"}, headers=bob["headers"])
    client.post("/accounts", json={"currency": "EUR"}, headers=bob["headers"])

    response = client.get(
        f"/users/{bob['user']['id']}/accounts",
        headers=bob["headers"],
    )

    assert response.status_code == 200
    accounts = response.get_json()
    assert len(accounts) == 2
    assert all(account["user_id"] == bob["user"]["id"] for account in accounts)


def test_expired_token_returns_401(app, client, created_user):
    expired_token = jwt.encode(
        {
            "sub": str(created_user["id"]),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        app.config["JWT_SECRET_KEY"],
        algorithm=app.config["JWT_ALGORITHM"],
    )
    headers = {"Authorization": f"Bearer {expired_token}"}

    response = client.get(f"/users/{created_user['id']}/accounts", headers=headers)

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_invalid_token_returns_401(client, created_user):
    headers = {"Authorization": "Bearer not-a-valid-token"}

    response = client.get(f"/users/{created_user['id']}/accounts", headers=headers)

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_missing_authorization_header_returns_401(client, created_user):
    response = client.get(f"/users/{created_user['id']}/accounts")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"
