from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import jwt
import pytest

from app.extensions import db
from app.models import Account, Transaction


def create_account(client, headers, currency="GBP"):
    response = client.post("/accounts", json={"currency": currency}, headers=headers)
    return response.get_json()


def fund_account(app, account_id, balance):
    with app.app_context():
        account = db.session.get(Account, account_id)
        account.balance = Decimal(str(balance))
        db.session.commit()


def get_balance(client, account_id, headers):
    response = client.get(f"/accounts/{account_id}", headers=headers)
    return response.get_json()["balance"]


def post_transfer(client, headers, from_account_id, to_account_id, amount, currency="GBP"):
    return client.post(
        "/transactions",
        json={
            "from_account_id": from_account_id,
            "to_account_id": to_account_id,
            "amount": str(amount),
            "currency": currency,
        },
        headers=headers,
    )


def transaction_count(app):
    with app.app_context():
        return db.session.query(Transaction).count()


@pytest.fixture
def alice_bob_gbp_accounts(client, alice, bob, app):
    alice_account = create_account(client, alice["headers"], "GBP")
    bob_account = create_account(client, bob["headers"], "GBP")
    fund_account(app, alice_account["id"], "100.00")
    fund_account(app, bob_account["id"], "50.00")
    return {
        "alice": alice,
        "bob": bob,
        "alice_account": alice_account,
        "bob_account": bob_account,
    }


def test_authenticated_user_can_transfer_from_own_account(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "40.00",
    )

    assert response.status_code == 201


def test_source_balance_decreases_correctly(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "40.00",
    )

    balance = get_balance(client, data["alice_account"]["id"], data["alice"]["headers"])
    assert balance == "60.00"


def test_destination_balance_increases_correctly(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "40.00",
    )

    balance = get_balance(client, data["bob_account"]["id"], data["bob"]["headers"])
    assert balance == "90.00"


def test_transaction_record_is_created(client, alice_bob_gbp_accounts, app):
    data = alice_bob_gbp_accounts
    post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "40.00",
    )

    assert transaction_count(app) == 1


def test_returned_transaction_contains_correct_fields(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "40.00",
    )
    txn = response.get_json()

    assert txn["from_account_id"] == data["alice_account"]["id"]
    assert txn["to_account_id"] == data["bob_account"]["id"]
    assert txn["amount"] == "40.00"
    assert txn["currency"] == "GBP"
    assert "id" in txn
    assert "created_at" in txn


def test_unauthenticated_transfer_returns_401(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        {},
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "10.00",
    )

    assert response.status_code == 401


def test_invalid_token_returns_401(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    headers = {"Authorization": "Bearer invalid-token"}
    response = post_transfer(
        client,
        headers,
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "10.00",
    )

    assert response.status_code == 401


def test_expired_token_returns_401(app, client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    expired_token = jwt.encode(
        {
            "sub": str(data["alice"]["user"]["id"]),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        app.config["JWT_SECRET_KEY"],
        algorithm=app.config["JWT_ALGORITHM"],
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = post_transfer(
        client,
        headers,
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "10.00",
    )

    assert response.status_code == 401


def test_alice_cannot_transfer_from_bob_account(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["alice"]["headers"],
        data["bob_account"]["id"],
        data["alice_account"]["id"],
        "10.00",
    )

    assert response.status_code == 403


def test_bob_cannot_transfer_from_alice_account(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["bob"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "10.00",
    )

    assert response.status_code == 403


def test_alice_can_transfer_to_bob(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "25.00",
    )

    assert response.status_code == 201


def test_bob_can_transfer_to_alice(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["bob"]["headers"],
        data["bob_account"]["id"],
        data["alice_account"]["id"],
        "15.00",
    )

    assert response.status_code == 201


def test_missing_source_account_id_rejected(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = client.post(
        "/transactions",
        json={
            "to_account_id": data["bob_account"]["id"],
            "amount": "10.00",
            "currency": "GBP",
        },
        headers=data["alice"]["headers"],
    )

    assert response.status_code == 400
    assert "from_account_id is required" in response.get_json()["errors"]


def test_missing_destination_account_id_rejected(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = client.post(
        "/transactions",
        json={
            "from_account_id": data["alice_account"]["id"],
            "amount": "10.00",
            "currency": "GBP",
        },
        headers=data["alice"]["headers"],
    )

    assert response.status_code == 400
    assert "to_account_id is required" in response.get_json()["errors"]


def test_missing_amount_rejected(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = client.post(
        "/transactions",
        json={
            "from_account_id": data["alice_account"]["id"],
            "to_account_id": data["bob_account"]["id"],
            "currency": "GBP",
        },
        headers=data["alice"]["headers"],
    )

    assert response.status_code == 400
    assert "amount is required" in response.get_json()["errors"]


def test_missing_currency_rejected(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = client.post(
        "/transactions",
        json={
            "from_account_id": data["alice_account"]["id"],
            "to_account_id": data["bob_account"]["id"],
            "amount": "10.00",
        },
        headers=data["alice"]["headers"],
    )

    assert response.status_code == 400
    assert "currency is required" in response.get_json()["errors"]


def test_zero_amount_rejected(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "0.00",
    )

    assert response.status_code == 400
    assert "amount must be greater than zero" in response.get_json()["errors"]


def test_negative_amount_rejected(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "-10.00",
    )

    assert response.status_code == 400
    assert "amount must be greater than zero" in response.get_json()["errors"]


def test_invalid_amount_rejected(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = client.post(
        "/transactions",
        json={
            "from_account_id": data["alice_account"]["id"],
            "to_account_id": data["bob_account"]["id"],
            "amount": "not-a-number",
            "currency": "GBP",
        },
        headers=data["alice"]["headers"],
    )

    assert response.status_code == 400
    assert "amount is invalid" in response.get_json()["errors"]


def test_unsupported_currency_rejected(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "10.00",
        currency="JPY",
    )

    assert response.status_code == 400


def test_nonexistent_source_account_rejected(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["alice"]["headers"],
        999,
        data["bob_account"]["id"],
        "10.00",
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "source account not found"


def test_nonexistent_destination_account_rejected(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        999,
        "10.00",
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "destination account not found"


def test_same_source_and_destination_rejected(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["alice_account"]["id"],
        "10.00",
    )

    assert response.status_code == 400
    assert "source and destination accounts must be different" in response.get_json()["errors"]


def test_insufficient_funds_rejected(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "150.00",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "insufficient funds"


def test_failed_transfer_does_not_modify_source_balance(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "150.00",
    )

    balance = get_balance(client, data["alice_account"]["id"], data["alice"]["headers"])
    assert balance == "100.00"


def test_failed_transfer_does_not_modify_destination_balance(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "150.00",
    )

    balance = get_balance(client, data["bob_account"]["id"], data["bob"]["headers"])
    assert balance == "50.00"


def test_failed_transfer_does_not_create_record(client, alice_bob_gbp_accounts, app):
    data = alice_bob_gbp_accounts
    post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "150.00",
    )

    assert transaction_count(app) == 0


def test_gbp_to_gbp_works(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    response = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "10.00",
        currency="GBP",
    )

    assert response.status_code == 201
    assert response.get_json()["currency"] == "GBP"


def test_gbp_to_eur_rejected(client, alice, bob, app):
    alice_account = create_account(client, alice["headers"], "GBP")
    bob_account = create_account(client, bob["headers"], "EUR")
    fund_account(app, alice_account["id"], "100.00")

    response = post_transfer(
        client,
        alice["headers"],
        alice_account["id"],
        bob_account["id"],
        "10.00",
        currency="GBP",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "currency mismatch"


def test_eur_to_gbp_rejected(client, alice, bob, app):
    alice_account = create_account(client, alice["headers"], "EUR")
    bob_account = create_account(client, bob["headers"], "GBP")
    fund_account(app, alice_account["id"], "100.00")

    response = post_transfer(
        client,
        alice["headers"],
        alice_account["id"],
        bob_account["id"],
        "10.00",
        currency="EUR",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "currency mismatch"


def test_sender_can_retrieve_transaction(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    txn = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "10.00",
    ).get_json()

    response = client.get(f"/transactions/{txn['id']}", headers=data["alice"]["headers"])

    assert response.status_code == 200
    assert response.get_json()["id"] == txn["id"]


def test_recipient_can_retrieve_transaction(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    txn = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "10.00",
    ).get_json()

    response = client.get(f"/transactions/{txn['id']}", headers=data["bob"]["headers"])

    assert response.status_code == 200


def test_unrelated_user_cannot_retrieve_transaction(
    client, alice_bob_gbp_accounts, charlie
):
    data = alice_bob_gbp_accounts
    txn = post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "10.00",
    ).get_json()

    response = client.get(f"/transactions/{txn['id']}", headers=charlie["headers"])

    assert response.status_code == 403


def test_nonexistent_transaction_returns_404(client, alice):
    response = client.get("/transactions/999", headers=alice["headers"])

    assert response.status_code == 404


def test_account_owner_can_retrieve_transaction_history(client, alice_bob_gbp_accounts):
    data = alice_bob_gbp_accounts
    post_transfer(
        client,
        data["alice"]["headers"],
        data["alice_account"]["id"],
        data["bob_account"]["id"],
        "10.00",
    )

    response = client.get(
        f"/accounts/{data['alice_account']['id']}/transactions",
        headers=data["alice"]["headers"],
    )

    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_account_owner_receives_incoming_and_outgoing_transactions(
    client, alice, bob, app
):
    alice_account = create_account(client, alice["headers"], "GBP")
    bob_account = create_account(client, bob["headers"], "GBP")
    fund_account(app, alice_account["id"], "200.00")
    fund_account(app, bob_account["id"], "100.00")

    post_transfer(client, alice["headers"], alice_account["id"], bob_account["id"], "20.00")
    post_transfer(client, bob["headers"], bob_account["id"], alice_account["id"], "15.00")

    response = client.get(
        f"/accounts/{alice_account['id']}/transactions",
        headers=alice["headers"],
    )

    assert response.status_code == 200
    assert len(response.get_json()) == 2


def test_other_user_cannot_retrieve_account_transaction_history(
    client, alice_bob_gbp_accounts, charlie
):
    data = alice_bob_gbp_accounts
    response = client.get(
        f"/accounts/{data['alice_account']['id']}/transactions",
        headers=charlie["headers"],
    )

    assert response.status_code == 403


def test_nonexistent_account_history_returns_404(client, alice):
    response = client.get("/accounts/999/transactions", headers=alice["headers"])

    assert response.status_code == 404


def test_failed_transfer_rolls_back_all_changes(client, alice_bob_gbp_accounts, app):
    data = alice_bob_gbp_accounts

    with patch(
        "app.services.transactions.db.session.commit",
        side_effect=Exception("simulated database failure"),
    ):
        response = post_transfer(
            client,
            data["alice"]["headers"],
            data["alice_account"]["id"],
            data["bob_account"]["id"],
            "10.00",
        )

    assert response.status_code == 500
    assert get_balance(client, data["alice_account"]["id"], data["alice"]["headers"]) == "100.00"
    assert get_balance(client, data["bob_account"]["id"], data["bob"]["headers"]) == "50.00"
    assert transaction_count(app) == 0
