from flask import Blueprint, jsonify, request

from app.auth import get_current_user_id, jwt_required
from app.extensions import db
from app.models import User

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/users/me/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"errors": ["Request body must be JSON"]}), 400

    user = db.session.get(User, get_current_user_id())
    # INTENTIONAL VULNERABILITY FOR LOCAL APPSEC LAB:
    # display_name is stored without sanitisation for later unsafe rendering.
    user.display_name = data.get("display_name", "")
    db.session.commit()

    return jsonify({"display_name": user.display_name}), 200


@profile_bp.route("/profile/<int:user_id>/view")
def view_profile(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return "User not found", 404

    name = user.display_name or user.username

    # INTENTIONAL VULNERABILITY FOR LOCAL APPSEC LAB:
    # Stored display_name is rendered as HTML without escaping (XSS sink).
    # It will be remediated in a later step.
    html = f"<html><body><h1>{name}</h1><p>Profile for user {user.username}</p></body></html>"
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}
