from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Numeric

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    accounts = db.relationship("Account", back_populates="user", lazy=True)


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    balance = db.Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    currency = db.Column(db.String(3), nullable=False, default="GBP")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="accounts")
    transactions_sent = db.relationship(
        "Transaction",
        foreign_keys="Transaction.from_account_id",
        back_populates="from_account",
        lazy=True,
    )
    transactions_received = db.relationship(
        "Transaction",
        foreign_keys="Transaction.to_account_id",
        back_populates="to_account",
        lazy=True,
    )


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    from_account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    to_account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    amount = db.Column(Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    from_account = db.relationship(
        "Account",
        foreign_keys=[from_account_id],
        back_populates="transactions_sent",
    )
    to_account = db.relationship(
        "Account",
        foreign_keys=[to_account_id],
        back_populates="transactions_received",
    )
