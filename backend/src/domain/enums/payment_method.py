"""Payment Method Enumeration."""

from enum import StrEnum


class PaymentMethod(StrEnum):
    """Method of payment used for transaction.

    Attributes:
        CREDIT_CARD: Credit card payment
        DEBIT_CARD: Debit card payment
        BANK_TRANSFER: Direct bank transfer
        WALLET: Digital wallet (PayPal, Apple Pay, etc.)
        CASH: Cash payment
        CRYPTO: Cryptocurrency payment
        CHECK: Check payment
    """

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    WALLET = "wallet"
    CASH = "cash"
    CRYPTO = "crypto"
    CHECK = "check"

    def is_reversible(self) -> bool:
        """Check if payment method allows chargebacks/reversals.

        Returns:
            True if reversible
        """
        return self in {
            PaymentMethod.CREDIT_CARD,
            PaymentMethod.DEBIT_CARD,
            PaymentMethod.BANK_TRANSFER,
        }

    def get_risk_level(self) -> str:
        """Get base risk level for payment method.

        Returns:
            Risk level (low, medium, high)
        """
        high_risk = {PaymentMethod.CRYPTO, PaymentMethod.WALLET}
        low_risk = {PaymentMethod.CASH, PaymentMethod.CHECK, PaymentMethod.BANK_TRANSFER}

        if self in high_risk:
            return "high"
        elif self in low_risk:
            return "low"
        else:
            return "medium"
