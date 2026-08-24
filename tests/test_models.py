from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Account, Transaction, User


def test_user_can_be_created(db_session):
    user = User(
        username="alice",
        email="alice@example.com",
        password_hash="hashed_password",
    )
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    assert user.username == "alice"
    assert user.email == "alice@example.com"


def test_account_associated_with_user(db_session):
    user = User(
        username="bob",
        email="bob@example.com",
        password_hash="hashed_password",
    )
    db_session.add(user)
    db_session.commit()

    account = Account(
        user_id=user.id,
        account_number="ACC001",
        balance=Decimal("100.00"),
        currency="GBP",
    )
    db_session.add(account)
    db_session.commit()

    assert account.user_id == user.id
    assert account.user.username == "bob"


def test_user_can_have_multiple_accounts(db_session):
    user = User(
        username="carol",
        email="carol@example.com",
        password_hash="hashed_password",
    )
    db_session.add(user)
    db_session.commit()

    account_one = Account(
        user_id=user.id,
        account_number="ACC002",
        balance=Decimal("50.00"),
        currency="GBP",
    )
    account_two = Account(
        user_id=user.id,
        account_number="ACC003",
        balance=Decimal("75.00"),
        currency="GBP",
    )
    db_session.add_all([account_one, account_two])
    db_session.commit()

    assert len(user.accounts) == 2


def test_transaction_references_two_accounts(db_session):
    user = User(
        username="dave",
        email="dave@example.com",
        password_hash="hashed_password",
    )
    db_session.add(user)
    db_session.commit()

    from_account = Account(
        user_id=user.id,
        account_number="ACC004",
        balance=Decimal("200.00"),
        currency="GBP",
    )
    to_account = Account(
        user_id=user.id,
        account_number="ACC005",
        balance=Decimal("0.00"),
        currency="GBP",
    )
    db_session.add_all([from_account, to_account])
    db_session.commit()

    transaction = Transaction(
        from_account_id=from_account.id,
        to_account_id=to_account.id,
        amount=Decimal("25.50"),
        currency="GBP",
    )
    db_session.add(transaction)
    db_session.commit()

    assert transaction.from_account.account_number == "ACC004"
    assert transaction.to_account.account_number == "ACC005"


def test_user_email_uniqueness(db_session):
    db_session.add(
        User(
            username="user_one",
            email="duplicate@example.com",
            password_hash="hash_one",
        )
    )
    db_session.commit()

    db_session.add(
        User(
            username="user_two",
            email="duplicate@example.com",
            password_hash="hash_two",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_account_number_uniqueness(db_session):
    user = User(
        username="eve",
        email="eve@example.com",
        password_hash="hashed_password",
    )
    db_session.add(user)
    db_session.commit()

    db_session.add(
        Account(
            user_id=user.id,
            account_number="UNIQUE001",
            balance=Decimal("0.00"),
            currency="GBP",
        )
    )
    db_session.commit()

    db_session.add(
        Account(
            user_id=user.id,
            account_number="UNIQUE001",
            balance=Decimal("0.00"),
            currency="GBP",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
