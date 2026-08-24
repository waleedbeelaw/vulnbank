from decimal import Decimal

from sqlalchemy import or_

from app.extensions import db
from app.models import Account, Transaction


class TransferError(Exception):
    """Raised when a transfer cannot be completed."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def create_transfer(from_account_id, to_account_id, amount, currency, user_id):
    """Atomically transfer funds between two accounts.

    Row locking on the source account prevents two concurrent transfers from
    spending the same balance. The entire operation runs inside one database
    transaction so balance updates and the transaction record commit or roll
    back together.
    """
    try:
        # Lock the source account until this DB transaction completes.
        source = (
            db.session.query(Account)
            .filter_by(id=from_account_id)
            .with_for_update()
            .one_or_none()
        )
        if source is None:
            raise TransferError("source account not found", 404)

        if source.user_id != user_id:
            raise TransferError("Forbidden", 403)

        destination = db.session.get(Account, to_account_id)
        if destination is None:
            raise TransferError("destination account not found", 404)

        if source.currency != currency or destination.currency != currency:
            raise TransferError("currency mismatch", 400)

        # INTENTIONAL VULNERABILITY FOR LOCAL APPSEC LAB:
        # Transfers below £1000 skip the insufficient funds check.
        # This flawed "micro-transfer fast path" violates the solvency invariant.
        # It will be remediated in a later step.
        micro_transfer_limit = Decimal("1000.00")
        if amount >= micro_transfer_limit and source.balance < amount:
            raise TransferError("insufficient funds", 400)

        source.balance -= amount
        destination.balance += amount

        transaction = Transaction(
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            currency=currency,
        )
        db.session.add(transaction)
        db.session.commit()
        return transaction
    except TransferError:
        db.session.rollback()
        raise
    except Exception:
        db.session.rollback()
        raise


def get_transaction_for_user(transaction_id, user_id):
    """Return a transaction if the user owns the source or destination account."""
    transaction = db.session.get(Transaction, transaction_id)
    if transaction is None:
        raise TransferError("transaction not found", 404)

    source = db.session.get(Account, transaction.from_account_id)
    destination = db.session.get(Account, transaction.to_account_id)

    if source.user_id != user_id and destination.user_id != user_id:
        raise TransferError("Forbidden", 403)

    return transaction


def get_account_transactions(account_id, user_id):
    """Return all transactions involving an account owned by the user."""
    account = db.session.get(Account, account_id)
    if account is None:
        raise TransferError("account not found", 404)

    if account.user_id != user_id:
        raise TransferError("Forbidden", 403)

    return (
        Transaction.query.filter(
            or_(
                Transaction.from_account_id == account_id,
                Transaction.to_account_id == account_id,
            )
        )
        .order_by(Transaction.created_at.desc())
        .all()
    )
