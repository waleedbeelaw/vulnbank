from flask import Blueprint, jsonify

bp = Blueprint("routes", __name__)


@bp.route("/")
def index():
    """Return basic API information."""
    return jsonify({"name": "VulnBank", "status": "online"}), 200


@bp.route("/health")
def health():
    """Return application health status."""
    return jsonify({"status": "healthy"}), 200
