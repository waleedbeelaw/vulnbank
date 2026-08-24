from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from app.models import User

search_bp = Blueprint("search", __name__)


@search_bp.route("/search/users")
def search_users():
    query_term = request.args.get("q", "").strip()

    if not query_term:
        return jsonify([]), 200

    pattern = f"%{query_term}%"
    users = User.query.filter(
        or_(
            User.username.ilike(pattern),
            User.email.ilike(pattern),
        )
    ).all()

    return jsonify(
        [{"id": user.id, "username": user.username, "email": user.email} for user in users]
    ), 200
