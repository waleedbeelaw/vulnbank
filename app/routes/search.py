from flask import Blueprint, jsonify, request
from sqlalchemy import text

from app.extensions import db

search_bp = Blueprint("search", __name__)


@search_bp.route("/search/users")
def search_users():
    query_term = request.args.get("q", "")

    # INTENTIONAL VULNERABILITY FOR LOCAL APPSEC LAB:
    # User input is concatenated directly into SQL.
    # This enables SQL injection. It will be remediated in a later step.
    sql = (
        "SELECT id, username, email FROM users "
        f"WHERE username LIKE '%{query_term}%' OR email LIKE '%{query_term}%'"
    )
    results = db.session.execute(text(sql)).fetchall()

    users = [{"id": row.id, "username": row.username, "email": row.email} for row in results]
    return jsonify(users), 200
