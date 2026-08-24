from flask import Blueprint, jsonify

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Return basic API information."""
    return jsonify({"name": "VulnBank", "status": "online"}), 200


@main_bp.route("/health")
def health():
    """Return application health status."""
    return jsonify({"status": "healthy"}), 200


def register_blueprints(app):
    from app.routes.accounts import accounts_bp
    from app.routes.auth import auth_bp
    from app.routes.transactions import transactions_bp
    from app.routes.users import users_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(transactions_bp)
