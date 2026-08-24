"""Structured security audit logging for VulnBank."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone

from flask import Flask, g, has_request_context, request

SECURITY_LOGGER_NAME = "vulnbank.security"
MAX_LOG_FIELD_LENGTH = 128
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def get_security_logger() -> logging.Logger:
    return logging.getLogger(SECURITY_LOGGER_NAME)


def sanitize_log_value(value: object) -> str | None:
    """Remove control characters and cap length for user-influenced log fields."""
    if value is None:
        return None
    text = str(value).replace("\r", "").replace("\n", "")
    if len(text) > MAX_LOG_FIELD_LENGTH:
        text = text[:MAX_LOG_FIELD_LENGTH]
    return text


def normalize_request_id(client_value: str | None) -> str | None:
    """Accept only bounded, safe client request IDs."""
    if not client_value:
        return None
    cleaned = sanitize_log_value(client_value.strip())
    if not cleaned or not REQUEST_ID_PATTERN.match(cleaned):
        return None
    return cleaned


def resolve_request_id() -> str:
    """Return the validated client request ID or a server-generated UUID."""
    if has_request_context():
        client_value = request.headers.get("X-Request-ID")
        normalized = normalize_request_id(client_value)
        if normalized:
            return normalized
    return str(uuid.uuid4())


def log_security_event(
    event: str,
    *,
    outcome: str | None = None,
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    reason: str | None = None,
    **extra: object,
) -> None:
    """Emit one JSON security audit record to the security logger."""
    record: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "INFO",
        "event": event,
    }

    if outcome is not None:
        record["outcome"] = sanitize_log_value(outcome)

    if has_request_context():
        record["request_id"] = getattr(g, "request_id", None)
        record["remote_addr"] = request.remote_addr

    if user_id is not None:
        record["user_id"] = user_id

    if resource_type is not None:
        record["resource_type"] = sanitize_log_value(resource_type)

    if resource_id is not None:
        record["resource_id"] = resource_id

    if reason is not None:
        record["reason"] = sanitize_log_value(reason)

    for key, value in extra.items():
        if value is None:
            continue
        if isinstance(value, str):
            record[key] = sanitize_log_value(value)
        else:
            record[key] = value

    get_security_logger().info(json.dumps(record, separators=(",", ":")))


def configure_security_logging(app: Flask) -> None:
    """Configure stdout JSON security logging for the application."""
    log_level_name = app.config.get("LOG_LEVEL", "INFO")
    level = getattr(logging, str(log_level_name).upper(), logging.INFO)

    logger = get_security_logger()
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    logger.propagate = False


def register_request_id_hooks(app: Flask) -> None:
    """Assign a correlation ID per request and echo it in the response."""

    @app.before_request
    def assign_request_id() -> None:
        g.request_id = resolve_request_id()

    @app.after_request
    def add_request_id_header(response):
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response
