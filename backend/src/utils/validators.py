"""Validation Utilities."""

from uuid import UUID


def validate_uuid(uuid_string: str) -> bool:
    """Validate if string is a valid UUID.

    Args:
        uuid_string: String to validate

    Returns:
        True if valid UUID, False otherwise
    """
    try:
        UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False


def validate_email(email: str) -> bool:
    """Validate if string is a valid email address.

    Basic validation only - checks for @ and . in correct positions.

    Args:
        email: Email address to validate

    Returns:
        True if valid format, False otherwise
    """
    if not email or "@" not in email:
        return False

    local, domain = email.rsplit("@", 1)

    if not local or not domain or "." not in domain:
        return False

    return True


def validate_currency_code(code: str) -> bool:
    """Validate if string is a valid 3-letter currency code.

    Args:
        code: Currency code to validate

    Returns:
        True if valid format, False otherwise
    """
    return isinstance(code, str) and len(code) == 3 and code.isalpha()


def validate_probability(value: float) -> bool:
    """Validate if value is a valid probability [0, 1].

    Args:
        value: Value to validate

    Returns:
        True if valid probability, False otherwise
    """
    return isinstance(value, (int, float)) and 0.0 <= value <= 1.0


def validate_risk_score(value: int) -> bool:
    """Validate if value is a valid risk score [0, 100].

    Args:
        value: Value to validate

    Returns:
        True if valid risk score, False otherwise
    """
    return isinstance(value, int) and 0 <= value <= 100
