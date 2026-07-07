"""Money Value Object."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    """Money value object representing an amount in a specific currency.

    Immutable representation of money with currency.

    Attributes:
        amount: Monetary amount
        currency: Currency code (ISO 4217)
    """

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        """Validate money value object."""
        if self.amount < Decimal("0"):
            raise ValueError("Amount cannot be negative")

        if not self.currency or len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter ISO code")

        if not self.currency.isupper():
            raise ValueError("Currency must be uppercase")

    def add(self, other: "Money") -> "Money":
        """Add two money amounts.

        Args:
            other: Another money instance

        Returns:
            New Money instance with sum

        Raises:
            ValueError: If currencies don't match
        """
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")

        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        """Subtract money amount.

        Args:
            other: Another money instance

        Returns:
            New Money instance with difference

        Raises:
            ValueError: If currencies don't match or result is negative
        """
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")

        result = self.amount - other.amount
        if result < Decimal("0"):
            raise ValueError("Result cannot be negative")

        return Money(result, self.currency)

    def multiply(self, factor: Decimal) -> "Money":
        """Multiply money by a factor.

        Args:
            factor: Multiplication factor

        Returns:
            New Money instance
        """
        return Money((self.amount * factor).quantize(Decimal("0.01")), self.currency)

    def is_zero(self) -> bool:
        """Check if amount is zero."""
        return self.amount == Decimal("0")

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.currency} {self.amount:.2f}"
