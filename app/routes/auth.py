from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash

from app.auth import INVALID_CREDENTIALS_RESPONSE, create_access_token
from app.extensions import db
from app.models import User
from app.security_logging import log_security_event
from app.validators import validate_login_payload

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    errors = validate_login_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    email = data["email"].strip()
    password = data["password"]

    user = db.session.query(User).filter_by(email=email).first()
    if user is None or not check_password_hash(user.password_hash, password):
        log_security_event(
            "auth.login.failure",
            outcome="failure",
            reason="invalid_credentials",
        )
        return jsonify(INVALID_CREDENTIALS_RESPONSE), 401

    log_security_event(
        "auth.login.success",
        outcome="success",
        user_id=user.id,
    )
    token = create_access_token(user.id)
    return jsonify({"access_token": token}), 200
