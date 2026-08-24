from flask import Flask


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    if test_config:
        app.config.update(test_config)

    from app import routes

    app.register_blueprint(routes.bp)

    return app
