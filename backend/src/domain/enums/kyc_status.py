"""KYC Status Enumeration."""

from enum import StrEnum


class KYCStatus(StrEnum):
    """Know Your Customer (KYC) verification status.

    Attributes:
        PENDING: KYC verification in progress
        VERIFIED: KYC successfully verified
        REJECTED: KYC verification failed
        EXPIRED: KYC verification expired
        NOT_STARTED: KYC not yet initiated
    """

    NOT_STARTED = "not_started"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"

    def is_valid(self) -> bool:
        """Check if KYC is currently valid.

        Returns:
            True if KYC is verified
        """
        return self == KYCStatus.VERIFIED

    def requires_action(self) -> bool:
        """Check if KYC requires customer action.

        Returns:
            True if customer needs to complete KYC
        """
        return self in {
            KYCStatus.NOT_STARTED,
            KYCStatus.REJECTED,
            KYCStatus.EXPIRED,
        }

    def blocks_transactions(self) -> bool:
        """Check if KYC status blocks transactions.

        Returns:
            True if transactions should be blocked
        """
        return self in {
            KYCStatus.NOT_STARTED,
            KYCStatus.REJECTED,
            KYCStatus.EXPIRED,
        }
