"""Validation Error Exception."""

from typing import Any

from .base import DomainException


class ValidationError(DomainException):
    """Exception raised when entity validation fails.

    Represents violations of entity invariants or business rules.
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Human-readable error message
            field: Name of the field that failed validation
            value: Value that caused validation to fail
        """
        super().__init__(message, code="VALIDATION_ERROR")
        self.field = field
        self.value = value

    def __str__(self) -> str:
        """Return string representation."""
        if self.field:
            return f"[{self.code}] {self.field}: {self.message}"
        return f"[{self.code}] {self.message}"
