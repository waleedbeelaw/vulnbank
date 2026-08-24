from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request
from jwt.exceptions import InvalidTokenError

INVALID_CREDENTIALS_RESPONSE = {"error": "Invalid credentials"}
AUTHENTICATION_REQUIRED_RESPONSE = {"error": "Authentication required"}
FORBIDDEN_RESPONSE = {"error": "Forbidden"}


def create_access_token(user_id):
    """Create a signed JWT for the given user ID."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=current_app.config["JWT_EXPIRATION_SECONDS"])
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires,
    }
    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )


def jwt_required():
    """Require a valid Bearer JWT on a route."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify(AUTHENTICATION_REQUIRED_RESPONSE), 401

            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return jsonify(AUTHENTICATION_REQUIRED_RESPONSE), 401

            try:
                payload = jwt.decode(
                    parts[1],
                    current_app.config["JWT_SECRET_KEY"],
                    algorithms=[current_app.config["JWT_ALGORITHM"]],
                )
                user_id = payload.get("sub")
                if user_id is None:
                    return jsonify(AUTHENTICATION_REQUIRED_RESPONSE), 401
                g.current_user_id = int(user_id)
            except jwt.ExpiredSignatureError:
                return jsonify(AUTHENTICATION_REQUIRED_RESPONSE), 401
            except (InvalidTokenError, ValueError, TypeError):
                return jsonify(AUTHENTICATION_REQUIRED_RESPONSE), 401

            return view_func(*args, **kwargs)

        return wrapper

    return decorator


def get_current_user_id():
    """Return the authenticated user's ID from the JWT."""
    return g.current_user_id
