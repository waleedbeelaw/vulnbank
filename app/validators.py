import re
import secrets
import string
from decimal import Decimal, InvalidOperation

SUPPORTED_CURRENCIES = {"GBP", "EUR", "USD"}
USERNAME_MAX_LENGTH = 80
EMAIL_MAX_LENGTH = 120
PASSWORD_MIN_LENGTH = 8
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_missing(value):
    return value is None or (isinstance(value, str) and not value.strip())


def validate_user_payload(data):
    """Return a list of validation error messages."""
    errors = []

    if data is None:
        return ["Request body must be JSON"]

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if _is_missing(username):
        errors.append("username is required")
    elif len(username.strip()) > USERNAME_MAX_LENGTH:
        errors.append(f"username must be at most {USERNAME_MAX_LENGTH} characters")

    if _is_missing(email):
        errors.append("email is required")
    elif len(email.strip()) > EMAIL_MAX_LENGTH:
        errors.append(f"email must be at most {EMAIL_MAX_LENGTH} characters")
    elif not EMAIL_PATTERN.match(email.strip()):
        errors.append("email format is invalid")

    if _is_missing(password):
        errors.append("password is required")
    elif len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"password must be at least {PASSWORD_MIN_LENGTH} characters")

    return errors


def validate_login_payload(data):
    """Return a list of validation error messages."""
    errors = []

    if data is None:
        return ["Request body must be JSON"]

    if _is_missing(data.get("email")):
        errors.append("email is required")

    if _is_missing(data.get("password")):
        errors.append("password is required")

    return errors


def validate_account_payload(data):
    """Return a list of validation error messages."""
    errors = []

    if data is None:
        return ["Request body must be JSON"]

    currency = data.get("currency")

    if _is_missing(currency):
        errors.append("currency is required")
    elif currency.strip().upper() not in SUPPORTED_CURRENCIES:
        errors.append("currency must be one of: GBP, EUR, USD")

    return errors


def validate_transaction_payload(data):
    """Validate transfer input and return (errors, parsed_payload)."""
    errors = []

    if data is None:
        return ["Request body must be JSON"], None

    from_account_id = data.get("from_account_id")
    to_account_id = data.get("to_account_id")
    amount = data.get("amount")
    currency = data.get("currency")

    if from_account_id is None:
        errors.append("from_account_id is required")
    if to_account_id is None:
        errors.append("to_account_id is required")
    if _is_missing(amount):
        errors.append("amount is required")
    if _is_missing(currency):
        errors.append("currency is required")

    if errors:
        return errors, None

    try:
        from_account_id = int(from_account_id)
        to_account_id = int(to_account_id)
    except (TypeError, ValueError):
        return ["account IDs must be integers"], None

    try:
        amount_decimal = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        return ["amount is invalid"], None

    if amount_decimal <= Decimal("0"):
        errors.append("amount must be greater than zero")

    currency = currency.strip().upper()
    if currency not in SUPPORTED_CURRENCIES:
        errors.append("currency must be one of: GBP, EUR, USD")

    if from_account_id == to_account_id:
        errors.append("source and destination accounts must be different")

    if errors:
        return errors, None

    return [], {
        "from_account_id": from_account_id,
        "to_account_id": to_account_id,
        "amount": amount_decimal.quantize(Decimal("0.01")),
        "currency": currency,
    }


def generate_account_number(existing_checker):
    """Generate a unique account number using a collision check callback."""
    while True:
        suffix = "".join(secrets.choice(string.digits) for _ in range(10))
        account_number = f"VB{suffix}"
        if not existing_checker(account_number):
            return account_number
