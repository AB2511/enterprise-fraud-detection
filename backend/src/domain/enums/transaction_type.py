"""Transaction Type Enumeration."""

from enum import StrEnum


class TransactionType(StrEnum):
    """Types of financial transactions."""

    PURCHASE = "purchase"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    REFUND = "refund"
    PAYMENT = "payment"
    DEPOSIT = "deposit"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value
