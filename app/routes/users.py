from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from app.auth import FORBIDDEN_RESPONSE, get_current_user_id, jwt_required
from app.extensions import db
from app.models import User
from app.serializers import account_to_dict, user_to_dict
from app.validators import validate_user_payload

users_bp = Blueprint("users", __name__)


@users_bp.route("/users", methods=["POST"])
def create_user():
    data = request.get_json(silent=True)
    errors = validate_user_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    username = data["username"].strip()
    email = data["email"].strip()

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "username already exists"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already exists"}), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(data["password"]),
    )
    db.session.add(user)
    db.session.commit()

    return jsonify(user_to_dict(user)), 201


@users_bp.route("/users/<int:user_id>")
@jwt_required()
def get_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "user not found"}), 404

    if user.id != get_current_user_id():
        return jsonify(FORBIDDEN_RESPONSE), 403

    return jsonify(user_to_dict(user)), 200


@users_bp.route("/users/<int:user_id>/accounts")
@jwt_required()
def list_user_accounts(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "user not found"}), 404

    if user.id != get_current_user_id():
        return jsonify(FORBIDDEN_RESPONSE), 403

    return jsonify([account_to_dict(account) for account in user.accounts]), 200
