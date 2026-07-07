"""Transaction Status Enumeration."""

from enum import Enum


class TransactionStatus(str, Enum):
    """Status of a transaction in its lifecycle.

    Attributes:
        PENDING: Transaction initiated but not yet processed
        APPROVED: Transaction approved and completed
        DECLINED: Transaction declined by fraud system or issuer
        FAILED: Transaction failed due to technical error
        REVERSED: Transaction reversed/refunded
    """

    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    FAILED = "failed"
    REVERSED = "reversed"

    def is_final(self) -> bool:
        """Check if status is final (terminal state).

        Returns:
            True if status is terminal
        """
        return self in {
            TransactionStatus.APPROVED,
            TransactionStatus.DECLINED,
            TransactionStatus.FAILED,
            TransactionStatus.REVERSED,
        }

    def is_successful(self) -> bool:
        """Check if status indicates success.

        Returns:
            True if transaction was successful
        """
        return self == TransactionStatus.APPROVED
