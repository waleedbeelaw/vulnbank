from decimal import Decimal

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Account, User
from app.serializers import account_exists_checker, account_to_dict
from app.validators import generate_account_number, validate_account_payload

accounts_bp = Blueprint("accounts", __name__)


@accounts_bp.route("/accounts", methods=["POST"])
def create_account():
    data = request.get_json(silent=True)
    errors = validate_account_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    user = db.session.get(User, data["user_id"])
    if user is None:
        return jsonify({"error": "user not found"}), 404

    account = Account(
        user_id=user.id,
        account_number=generate_account_number(account_exists_checker()),
        balance=Decimal("0.00"),
        currency=data["currency"].strip().upper(),
    )
    db.session.add(account)
    db.session.commit()

    return jsonify(account_to_dict(account)), 201


@accounts_bp.route("/accounts/<int:account_id>")
def get_account(account_id):
    account = db.session.get(Account, account_id)
    if account is None:
        return jsonify({"error": "account not found"}), 404

    return jsonify(account_to_dict(account)), 200
