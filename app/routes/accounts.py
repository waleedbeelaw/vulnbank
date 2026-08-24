from decimal import Decimal

from flask import Blueprint, jsonify, request

from app.auth import get_current_user_id, jwt_required
from app.extensions import db
from app.models import Account, User
from app.serializers import account_exists_checker, account_to_dict, transaction_to_dict
from app.services.transactions import TransferError, get_account_transactions
from app.validators import generate_account_number, validate_account_payload

accounts_bp = Blueprint("accounts", __name__)


@accounts_bp.route("/accounts", methods=["POST"])
@jwt_required()
def create_account():
    data = request.get_json(silent=True)
    errors = validate_account_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    account = Account(
        user_id=get_current_user_id(),
        account_number=generate_account_number(account_exists_checker()),
        balance=Decimal("0.00"),
        currency=data["currency"].strip().upper(),
    )
    db.session.add(account)
    db.session.commit()

    return jsonify(account_to_dict(account)), 201


@accounts_bp.route("/accounts/<int:account_id>")
@jwt_required()
def get_account(account_id):
    account = db.session.get(Account, account_id)
    if account is None:
        return jsonify({"error": "account not found"}), 404

    # INTENTIONAL VULNERABILITY FOR LOCAL APPSEC LAB:
    # This endpoint intentionally omits object-level authorization.
    # Authentication is required, but ownership is not verified.
    # It will be remediated in a later step.

    return jsonify(account_to_dict(account)), 200


@accounts_bp.route("/accounts/<int:account_id>/transactions")
@jwt_required()
def list_account_transactions(account_id):
    try:
        transactions = get_account_transactions(account_id, get_current_user_id())
    except TransferError as exc:
        return jsonify({"error": exc.message}), exc.status_code

    return jsonify([transaction_to_dict(txn) for txn in transactions]), 200
