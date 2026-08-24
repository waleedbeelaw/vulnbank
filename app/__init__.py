from flask import Flask

from app.config import Config
from app.extensions import db


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    if test_config:
        app.config.update(test_config)
    else:
        Config.validate()
        app.config.from_object(Config)

    db.init_app(app)

    from app.security_logging import configure_security_logging, register_request_id_hooks

    configure_security_logging(app)
    register_request_id_hooks(app)

    # Import models so SQLAlchemy registers them before create_all().
    from app import models  # noqa: F401

    from app.routes import register_blueprints

    register_blueprints(app)

    return app
