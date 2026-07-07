"""Domain Exceptions - Business rule violations."""

from .base import DomainException
from .validation_error import ValidationError

__all__ = ["DomainException", "ValidationError"]
