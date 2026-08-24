XSS_PAYLOAD = '<script>alert("VulnBank XSS")</script>'


def test_idor_vulnerability_alice_can_view_bob_account(client, alice, bob):
    """
    VULNERABILITY TEST — EXPECTED TO FAIL AFTER REMEDIATION.

    Demonstrates IDOR/BOLA on GET /accounts/<id>.
    After remediation, this test must expect HTTP 403.
    """
    bob_account = client.post(
        "/accounts",
        json={"currency": "GBP"},
        headers=bob["headers"],
    ).get_json()

    response = client.get(f"/accounts/{bob_account['id']}", headers=alice["headers"])

    assert response.status_code == 200
    assert response.get_json()["user_id"] == bob["user"]["id"]


def test_sql_injection_vulnerability_returns_extra_users(client, alice, bob):
    """
    VULNERABILITY TEST — EXPECTED TO FAIL AFTER REMEDIATION.

    Demonstrates SQL injection on GET /search/users.
    After remediation, the injection payload must not return all users.
    """
    response = client.get("/search/users?q=' OR '1'='1")

    assert response.status_code == 200
    users = response.get_json()
    assert len(users) >= 2


def test_stored_xss_vulnerability_renders_unescaped_script(client, alice):
    """
    VULNERABILITY TEST — EXPECTED TO FAIL AFTER REMEDIATION.

    Demonstrates stored XSS via display_name rendered in GET /profile/<id>/view.
    After remediation, the payload must be escaped and not appear as raw HTML.
    """
    client.put(
        "/users/me/profile",
        json={"display_name": XSS_PAYLOAD},
        headers=alice["headers"],
    )

    response = client.get(f"/profile/{alice['user']['id']}/view")

    assert response.status_code == 200
    assert XSS_PAYLOAD in response.get_data(as_text=True)


def test_business_logic_vulnerability_micro_transfer_overdraft(client, alice, bob, app):
    """
    VULNERABILITY TEST — EXPECTED TO FAIL AFTER REMEDIATION.

    Demonstrates the micro-transfer business logic flaw.
    Transfers below £1000 skip insufficient funds checks.
    After remediation, this transfer must be rejected with HTTP 400.
    """
    from decimal import Decimal

    from app.extensions import db
    from app.models import Account

    alice_account = client.post(
        "/accounts",
        json={"currency": "GBP"},
        headers=alice["headers"],
    ).get_json()
    bob_account = client.post(
        "/accounts",
        json={"currency": "GBP"},
        headers=bob["headers"],
    ).get_json()

    with app.app_context():
        account = db.session.get(Account, alice_account["id"])
        account.balance = Decimal("100.00")
        db.session.commit()

    response = client.post(
        "/transactions",
        json={
            "from_account_id": alice_account["id"],
            "to_account_id": bob_account["id"],
            "amount": "500.00",
            "currency": "GBP",
        },
        headers=alice["headers"],
    )

    assert response.status_code == 201

    with app.app_context():
        source = db.session.get(Account, alice_account["id"])
        assert source.balance == Decimal("-400.00")
