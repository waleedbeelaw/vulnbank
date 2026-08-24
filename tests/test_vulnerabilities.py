import re
from decimal import Decimal

XSS_PAYLOAD = '<script>alert("VulnBank XSS")</script>'


# --- VULN-001: IDOR / BOLA ---


def test_idor_remediation_alice_cannot_view_bob_account(client, alice, bob):
    """After remediation, cross-user account access must return 403."""
    bob_account = client.post(
        "/accounts",
        json={"currency": "GBP"},
        headers=bob["headers"],
    ).get_json()

    response = client.get(f"/accounts/{bob_account['id']}", headers=alice["headers"])

    assert response.status_code == 403
    assert response.get_json()["error"] == "Forbidden"


def test_idor_remediation_alice_can_view_own_account(client, alice):
    alice_account = client.post(
        "/accounts",
        json={"currency": "GBP"},
        headers=alice["headers"],
    ).get_json()

    response = client.get(f"/accounts/{alice_account['id']}", headers=alice["headers"])

    assert response.status_code == 200
    assert response.get_json()["user_id"] == alice["user"]["id"]


def test_idor_remediation_bob_cannot_view_alice_account(client, alice, bob):
    alice_account = client.post(
        "/accounts",
        json={"currency": "GBP"},
        headers=alice["headers"],
    ).get_json()

    response = client.get(f"/accounts/{alice_account['id']}", headers=bob["headers"])

    assert response.status_code == 403
    assert response.get_json()["error"] == "Forbidden"


def test_idor_remediation_unauthenticated_access_rejected(client, alice):
    alice_account = client.post(
        "/accounts",
        json={"currency": "GBP"},
        headers=alice["headers"],
    ).get_json()

    response = client.get(f"/accounts/{alice_account['id']}")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_idor_remediation_nonexistent_account_returns_404(client, alice):
    response = client.get("/accounts/99999", headers=alice["headers"])

    assert response.status_code == 404
    assert response.get_json()["error"] == "account not found"


# --- VULN-002: SQL Injection ---


def test_sql_injection_remediation_payload_does_not_return_all_users(client, alice, bob):
    """The classic injection payload must not bypass the search filter."""
    response = client.get("/search/users?q=' OR '1'='1")

    assert response.status_code == 200
    users = response.get_json()
    assert len(users) == 0


def test_sql_injection_remediation_normal_search_by_username(client, alice, bob):
    response = client.get("/search/users?q=alice")

    assert response.status_code == 200
    users = response.get_json()
    assert len(users) == 1
    assert users[0]["username"] == "alice"


def test_sql_injection_remediation_search_by_email(client, alice, bob):
    response = client.get("/search/users?q=bob@example.com")

    assert response.status_code == 200
    users = response.get_json()
    assert len(users) == 1
    assert users[0]["username"] == "bob"


def test_sql_injection_remediation_metacharacters_treated_as_literal(client, alice):
    """SQL syntax characters must be searched literally, not alter query logic."""
    response = client.get("/search/users?q='")

    assert response.status_code == 200
    assert response.get_json() == []


def test_sql_injection_remediation_empty_query_returns_empty_list(client, alice, bob):
    response = client.get("/search/users")

    assert response.status_code == 200
    assert response.get_json() == []


# --- VULN-003: Stored XSS ---


def test_xss_remediation_payload_is_html_escaped(client, alice):
    client.put(
        "/users/me/profile",
        json={"display_name": XSS_PAYLOAD},
        headers=alice["headers"],
    )

    response = client.get(f"/profile/{alice['user']['id']}/view")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert XSS_PAYLOAD not in body
    assert "&lt;script&gt;" in body
    assert "<script>" not in body
    assert re.search(r'alert\s*\(\s*(&#34;|&quot;|" )VulnBank XSS(&#34;|&quot;|" )\s*\)', body)


def test_xss_remediation_normal_display_name_renders(client, alice):
    display_name = "Alice <Banking>"
    client.put(
        "/users/me/profile",
        json={"display_name": display_name},
        headers=alice["headers"],
    )

    response = client.get(f"/profile/{alice['user']['id']}/view")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert display_name not in body
    assert "Alice &lt;Banking&gt;" in body


def test_xss_remediation_quotes_and_special_characters_safe(client, alice):
    display_name = 'Test "name" & \'value\''
    client.put(
        "/users/me/profile",
        json={"display_name": display_name},
        headers=alice["headers"],
    )

    response = client.get(f"/profile/{alice['user']['id']}/view")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert display_name not in body
    assert "Test" in body
    assert "&amp;" in body
    assert "&#34;" in body or "&quot;" in body
    assert "&#39;" in body or "&#x27;" in body


# --- VULN-004: Business Logic ---


def test_business_logic_remediation_micro_transfer_overdraft_rejected(client, alice, bob, app):
    """£100 balance → £500 transfer must fail after remediation."""
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

    assert response.status_code == 400
    assert response.get_json()["error"] == "insufficient funds"

    with app.app_context():
        source = db.session.get(Account, alice_account["id"])
        destination = db.session.get(Account, bob_account["id"])
        assert source.balance == Decimal("100.00")
        assert destination.balance == Decimal("0.00")


def test_business_logic_remediation_exact_balance_transfer_succeeds(client, alice, bob, app):
    """£100 balance → £100 transfer should succeed."""
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
            "amount": "100.00",
            "currency": "GBP",
        },
        headers=alice["headers"],
    )

    assert response.status_code == 201

    with app.app_context():
        source = db.session.get(Account, alice_account["id"])
        assert source.balance == Decimal("0.00")


def test_business_logic_remediation_sub_limit_transfer_succeeds(client, alice, bob, app):
    """£100 balance → £99.99 transfer should succeed."""
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
            "amount": "99.99",
            "currency": "GBP",
        },
        headers=alice["headers"],
    )

    assert response.status_code == 201

    with app.app_context():
        source = db.session.get(Account, alice_account["id"])
        assert source.balance == Decimal("0.01")


def test_business_logic_remediation_failed_transfer_creates_no_record(client, alice, bob, app):
    from app.extensions import db
    from app.models import Account, Transaction

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

    client.post(
        "/transactions",
        json={
            "from_account_id": alice_account["id"],
            "to_account_id": bob_account["id"],
            "amount": "500.00",
            "currency": "GBP",
        },
        headers=alice["headers"],
    )

    with app.app_context():
        assert Transaction.query.count() == 0
