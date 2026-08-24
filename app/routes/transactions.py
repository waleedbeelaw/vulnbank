from flask import Blueprint, jsonify, request

from app.auth import get_current_user_id, jwt_required
from app.serializers import transaction_to_dict
from app.services.transactions import TransferError, create_transfer, get_transaction_for_user
from app.validators import validate_transaction_payload

transactions_bp = Blueprint("transactions", __name__)


@transactions_bp.route("/transactions", methods=["POST"])
@jwt_required()
def post_transaction():
    data = request.get_json(silent=True)
    errors, payload = validate_transaction_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        transaction = create_transfer(
            payload["from_account_id"],
            payload["to_account_id"],
            payload["amount"],
            payload["currency"],
            get_current_user_id(),
        )
    except TransferError as exc:
        return jsonify({"error": exc.message}), exc.status_code
    except Exception:
        return jsonify({"error": "internal server error"}), 500

    return jsonify(transaction_to_dict(transaction)), 201


@transactions_bp.route("/transactions/<int:transaction_id>")
@jwt_required()
def get_transaction(transaction_id):
    try:
        transaction = get_transaction_for_user(transaction_id, get_current_user_id())
    except TransferError as exc:
        return jsonify({"error": exc.message}), exc.status_code

    return jsonify(transaction_to_dict(transaction)), 200
