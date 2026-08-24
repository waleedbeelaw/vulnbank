from decimal import Decimal

from app.models import Account


def user_to_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }


def account_to_dict(account):
    return {
        "id": account.id,
        "user_id": account.user_id,
        "account_number": account.account_number,
        "balance": format(account.balance, "f"),
        "currency": account.currency,
    }


def transaction_to_dict(transaction):
    return {
        "id": transaction.id,
        "from_account_id": transaction.from_account_id,
        "to_account_id": transaction.to_account_id,
        "amount": format(transaction.amount, "f"),
        "currency": transaction.currency,
        "created_at": transaction.created_at.isoformat(),
    }


def account_exists_checker():
    def checker(account_number):
        return Account.query.filter_by(account_number=account_number).first() is not None

    return checker
