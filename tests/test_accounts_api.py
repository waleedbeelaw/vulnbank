def test_create_account_for_existing_user(client, created_user):
    response = client.post(
        "/accounts",
        json={"user_id": created_user["id"], "currency": "GBP"},
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["user_id"] == created_user["id"]
    assert data["currency"] == "GBP"
    assert data["account_number"].startswith("VB")


def test_account_starts_with_zero_balance(client, created_user):
    response = client.post(
        "/accounts",
        json={"user_id": created_user["id"], "currency": "GBP"},
    )

    assert response.get_json()["balance"] == "0.00"


def test_account_number_generated_server_side(client, created_user):
    response = client.post(
        "/accounts",
        json={
            "user_id": created_user["id"],
            "currency": "GBP",
            "account_number": "CLIENT123",
        },
    )

    data = response.get_json()
    assert data["account_number"] != "CLIENT123"
    assert data["account_number"].startswith("VB")


def test_create_account_fails_for_nonexistent_user(client):
    response = client.post(
        "/accounts",
        json={"user_id": 999, "currency": "GBP"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_unsupported_currency_rejected(client, created_user):
    response = client.post(
        "/accounts",
        json={"user_id": created_user["id"], "currency": "JPY"},
    )

    assert response.status_code == 400
    assert "currency must be one of: GBP, EUR, USD" in response.get_json()["errors"]


def test_get_account_returns_account(client, created_user):
    create_response = client.post(
        "/accounts",
        json={"user_id": created_user["id"], "currency": "EUR"},
    )
    account = create_response.get_json()

    response = client.get(f"/accounts/{account['id']}")

    assert response.status_code == 200
    assert response.get_json() == account


def test_get_account_returns_404_for_nonexistent_account(client):
    response = client.get("/accounts/999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "account not found"


def test_get_user_accounts_returns_accounts(client, created_user):
    client.post(
        "/accounts",
        json={"user_id": created_user["id"], "currency": "GBP"},
    )
    client.post(
        "/accounts",
        json={"user_id": created_user["id"], "currency": "USD"},
    )

    response = client.get(f"/users/{created_user['id']}/accounts")

    assert response.status_code == 200
    accounts = response.get_json()
    assert len(accounts) == 2
    assert {account["currency"] for account in accounts} == {"GBP", "USD"}


def test_get_user_accounts_returns_404_for_nonexistent_user(client):
    response = client.get("/users/999/accounts")

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_get_user_accounts_returns_empty_list(client, created_user):
    response = client.get(f"/users/{created_user['id']}/accounts")

    assert response.status_code == 200
    assert response.get_json() == []
