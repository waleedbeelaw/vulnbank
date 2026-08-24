import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.security_logging import SECURITY_LOGGER_NAME
from tests.conftest import VALID_USER


def parse_security_logs(caplog):
    return [
        json.loads(record.message)
        for record in caplog.records
        if record.name == SECURITY_LOGGER_NAME
    ]


def security_log_text(caplog):
    return "\n".join(record.message for record in caplog.records)


@pytest.fixture
def security_logs(caplog):
    with caplog.at_level(logging.INFO, logger=SECURITY_LOGGER_NAME):
        yield caplog


def create_account(client, headers, currency="GBP"):
    response = client.post("/accounts", json={"currency": currency}, headers=headers)
    return response.get_json()


def test_successful_login_logs_auth_login_success(client, created_user, security_logs):
    response = client.post(
        "/login",
        json={"email": VALID_USER["email"], "password": VALID_USER["password"]},
    )

    assert response.status_code == 200
    events = parse_security_logs(security_logs)
    login_events = [event for event in events if event["event"] == "auth.login.success"]
    assert len(login_events) == 1
    assert login_events[0]["outcome"] == "success"
    assert login_events[0]["user_id"] == created_user["id"]


def test_failed_login_logs_auth_login_failure(client, created_user, security_logs):
    response = client.post(
        "/login",
        json={"email": VALID_USER["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401
    events = parse_security_logs(security_logs)
    failure_events = [event for event in events if event["event"] == "auth.login.failure"]
    assert len(failure_events) == 1
    assert failure_events[0]["outcome"] == "failure"
    assert failure_events[0]["reason"] == "invalid_credentials"


def test_password_is_never_present_in_security_logs(client, created_user, security_logs):
    secret_password = "super-secret-password-123"
    client.post(
        "/login",
        json={"email": VALID_USER["email"], "password": secret_password},
    )

    log_output = security_log_text(security_logs)
    assert secret_password not in log_output
    assert "password_hash" not in log_output


def test_jwt_is_never_present_in_security_logs(client, created_user, security_logs):
    response = client.post(
        "/login",
        json={"email": VALID_USER["email"], "password": VALID_USER["password"]},
    )
    token = response.get_json()["access_token"]

    security_logs.clear()
    client.get("/accounts/1", headers={"Authorization": f"Bearer {token}"})

    log_output = security_log_text(security_logs)
    assert token not in log_output
    assert "Authorization" not in log_output
    assert "Bearer" not in log_output


def test_authorization_denial_logs_authorization_denied(client, alice, bob, security_logs):
    alice_account = create_account(client, alice["headers"])

    security_logs.clear()
    response = client.get(
        f"/accounts/{alice_account['id']}",
        headers=bob["headers"],
    )

    assert response.status_code == 403
    events = parse_security_logs(security_logs)
    denied_events = [event for event in events if event["event"] == "authorization.denied"]
    assert len(denied_events) == 1
    assert denied_events[0]["resource_type"] == "account"
    assert denied_events[0]["resource_id"] == alice_account["id"]
    assert denied_events[0]["reason"] == "account_ownership"


def test_account_creation_logs_account_created(client, auth_headers, created_user, security_logs):
    response = client.post("/accounts", json={"currency": "GBP"}, headers=auth_headers)

    assert response.status_code == 201
    account = response.get_json()
    events = parse_security_logs(security_logs)
    created_events = [event for event in events if event["event"] == "account.created"]
    assert len(created_events) == 1
    assert created_events[0]["user_id"] == created_user["id"]
    assert created_events[0]["resource_id"] == account["id"]


def test_successful_transfer_logs_transaction_created(client, alice, bob, app, security_logs):
    alice_account = create_account(client, alice["headers"])
    bob_account = create_account(client, bob["headers"])

    from decimal import Decimal

    from app.extensions import db
    from app.models import Account

    with app.app_context():
        account = db.session.get(Account, alice_account["id"])
        account.balance = Decimal("100.00")
        db.session.commit()

    security_logs.clear()
    response = client.post(
        "/transactions",
        json={
            "from_account_id": alice_account["id"],
            "to_account_id": bob_account["id"],
            "amount": "25.00",
            "currency": "GBP",
        },
        headers=alice["headers"],
    )

    assert response.status_code == 201
    transaction = response.get_json()
    events = parse_security_logs(security_logs)
    created_events = [event for event in events if event["event"] == "transaction.created"]
    assert len(created_events) == 1
    assert created_events[0]["resource_id"] == transaction["id"]
    assert created_events[0]["outcome"] == "success"


def test_insufficient_funds_logs_transaction_rejected(client, alice, bob, security_logs):
    alice_account = create_account(client, alice["headers"])
    bob_account = create_account(client, bob["headers"])

    security_logs.clear()
    response = client.post(
        "/transactions",
        json={
            "from_account_id": alice_account["id"],
            "to_account_id": bob_account["id"],
            "amount": "10.00",
            "currency": "GBP",
        },
        headers=alice["headers"],
    )

    assert response.status_code == 400
    events = parse_security_logs(security_logs)
    rejected_events = [event for event in events if event["event"] == "transaction.rejected"]
    assert len(rejected_events) == 1
    assert rejected_events[0]["reason"] == "insufficient_funds"


def test_request_id_is_generated_when_missing(client):
    response = client.get("/health")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    uuid.UUID(request_id)


def test_client_request_id_is_preserved(client):
    response = client.get("/health", headers={"X-Request-ID": "client-req-123"})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "client-req-123"


def test_malicious_request_id_is_safely_handled(client, security_logs):
    malicious_id = "good-id auth.login.success fake!!!"
    response = client.get("/health", headers={"X-Request-ID": malicious_id})

    assert response.status_code == 200
    response_id = response.headers.get("X-Request-ID")
    assert response_id
    assert response_id != malicious_id
    uuid.UUID(response_id)


def test_control_characters_are_stripped_from_log_values():
    from app.security_logging import normalize_request_id, sanitize_log_value

    malicious = "trace-id\rINFO fake-security-event injected"
    cleaned = sanitize_log_value(malicious)
    assert cleaned is not None
    assert "\r" not in cleaned
    assert "\n" not in cleaned
    assert normalize_request_id("good-id\nauth.login.success fake") is None


def test_malicious_request_id_cannot_create_fake_log_lines(client, created_user, security_logs):
    client.post(
        "/login",
        json={"email": VALID_USER["email"], "password": "wrong-password"},
        headers={"X-Request-ID": "invalid id with spaces"},
    )

    log_output = security_log_text(security_logs)
    assert "fake-security-event injected" not in log_output
    assert "\r" not in log_output

    events = parse_security_logs(security_logs)
    assert len(events) == 1
    assert events[0]["event"] == "auth.login.failure"
    uuid.UUID(events[0]["request_id"])


def test_security_logs_include_structured_fields(client, created_user, security_logs):
    client.post(
        "/login",
        json={"email": VALID_USER["email"], "password": VALID_USER["password"]},
    )

    event = parse_security_logs(security_logs)[0]
    assert event["event"] == "auth.login.success"
    assert "timestamp" in event
    assert event["level"] == "INFO"
    assert "request_id" in event
    assert "remote_addr" in event
    assert event["user_id"] == created_user["id"]


def test_invalid_token_logs_auth_token_invalid(client, app, security_logs):
    token = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "wrong-secret-key",
        algorithm="HS256",
    )

    response = client.get("/accounts/1", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    events = parse_security_logs(security_logs)
    token_events = [event for event in events if event["event"] == "auth.token.invalid"]
    assert len(token_events) == 1
    assert token_events[0]["reason"] == "invalid"


def test_unauthenticated_access_logs_auth_unauthenticated(client, security_logs):
    response = client.get("/accounts/1")

    assert response.status_code == 401
    events = parse_security_logs(security_logs)
    unauthenticated_events = [
        event for event in events if event["event"] == "auth.unauthenticated"
    ]
    assert len(unauthenticated_events) == 1


def test_source_account_ownership_rejection_logs_transaction_rejected(
    client, alice, bob, security_logs
):
    bob_account = create_account(client, bob["headers"])
    alice_account = create_account(client, alice["headers"])

    security_logs.clear()
    response = client.post(
        "/transactions",
        json={
            "from_account_id": bob_account["id"],
            "to_account_id": alice_account["id"],
            "amount": "1.00",
            "currency": "GBP",
        },
        headers=alice["headers"],
    )

    assert response.status_code == 403
    events = parse_security_logs(security_logs)
    rejected_events = [event for event in events if event["event"] == "transaction.rejected"]
    assert len(rejected_events) == 1
    assert rejected_events[0]["reason"] == "source_account_ownership"


def test_existing_login_behaviour_unchanged(client, created_user):
    response = client.post(
        "/login",
        json={"email": VALID_USER["email"], "password": VALID_USER["password"]},
    )

    assert response.status_code == 200
    assert "access_token" in response.get_json()
