"""Merchant Entity - Business accepting payments."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass
class Merchant:
    """Merchant entity representing a business that accepts payments.

    Merchants have risk profiles based on historical fraud rates and
    merchant category codes (MCC).

    Attributes:
        merchant_id: Unique identifier
        merchant_name: Business name
        mcc: Merchant Category Code (4-digit code)
        merchant_category: Human-readable category
        country: Country of operation
        risk_rating: Risk rating (0-100, higher is riskier)
        historical_fraud_rate: Historical fraud rate as percentage
        total_transactions: Total number of transactions processed
        total_volume: Total transaction volume
        is_active: Merchant active status
        created_at: Registration timestamp
        updated_at: Last update timestamp
    """

    merchant_id: UUID = field(default_factory=uuid4)
    merchant_name: str = ""
    mcc: str = ""
    merchant_category: str = ""
    country: str = ""
    risk_rating: int = 50
    historical_fraud_rate: Decimal = Decimal("0.00")
    total_transactions: int = 0
    total_volume: Decimal = Decimal("0.00")
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate merchant business rules."""
        if not self.merchant_name:
            raise ValueError("Merchant name is required")

        if not self.mcc or len(self.mcc) != 4 or not self.mcc.isdigit():
            raise ValueError("MCC must be a 4-digit code")

        if not self.merchant_category:
            raise ValueError("Merchant category is required")

        if not self.country:
            raise ValueError("Country is required")

        if self.risk_rating < 0 or self.risk_rating > 100:
            raise ValueError("Risk rating must be between 0 and 100")

        if self.historical_fraud_rate < Decimal("0") or self.historical_fraud_rate > Decimal("100"):
            raise ValueError("Fraud rate must be between 0 and 100")

        if self.total_transactions < 0:
            raise ValueError("Total transactions cannot be negative")

        if self.total_volume < Decimal("0"):
            raise ValueError("Total volume cannot be negative")

    def update_risk_score(self, new_rating: int) -> None:
        """Update merchant risk rating.

        Args:
            new_rating: New risk rating (0-100)

        Raises:
            ValueError: If rating is out of range
        """
        if new_rating < 0 or new_rating > 100:
            raise ValueError("Risk rating must be between 0 and 100")

        self.risk_rating = new_rating
        self.updated_at = datetime.utcnow()

    def calculate_risk(self) -> int:
        """Calculate merchant risk rating based on multiple factors.

        Returns:
            Risk rating (0-100)
        """
        risk_score = 0

        # Base risk by MCC category
        high_risk_categories = [
            "gambling", "cryptocurrency", "adult", "pharmaceuticals",
            "electronics", "jewelry", "travel"
        ]
        if any(cat in self.merchant_category.lower() for cat in high_risk_categories):
            risk_score += 30

        # Historical fraud rate factor
        fraud_rate_float = float(self.historical_fraud_rate)
        if fraud_rate_float >= 5.0:
            risk_score += 40
        elif fraud_rate_float >= 2.0:
            risk_score += 25
        elif fraud_rate_float >= 1.0:
            risk_score += 15
        elif fraud_rate_float >= 0.5:
            risk_score += 10

        # New merchant factor (less than 100 transactions)
        if self.total_transactions < 100:
            risk_score += 20
        elif self.total_transactions < 500:
            risk_score += 10

        # Cap at 100
        return min(risk_score, 100)

    def record_transaction(self, amount: Decimal, is_fraud: bool = False) -> None:
        """Record a transaction and update merchant statistics.

        Args:
            amount: Transaction amount
            is_fraud: Whether transaction was fraud

        Raises:
            ValueError: If amount is negative
        """
        if amount < Decimal("0"):
            raise ValueError("Amount cannot be negative")

        self.total_transactions += 1
        self.total_volume += amount

        # Update fraud rate if fraud was detected
        if is_fraud:
            # Recalculate fraud rate
            total_fraud = int(float(self.historical_fraud_rate) * self.total_transactions / 100)
            total_fraud += 1
            self.historical_fraud_rate = Decimal(
                (total_fraud / self.total_transactions) * 100
            ).quantize(Decimal("0.01"))

        self.updated_at = datetime.utcnow()

        # Recalculate risk rating
        self.risk_rating = self.calculate_risk()

    def suspend(self) -> None:
        """Suspend merchant (high fraud activity)."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def reactivate(self) -> None:
        """Reactivate merchant."""
        if self.historical_fraud_rate > Decimal("10.0"):
            raise ValueError("Cannot reactivate merchant with fraud rate > 10%")

        self.is_active = True
        self.updated_at = datetime.utcnow()

    @property
    def is_high_risk(self) -> bool:
        """Check if merchant is high risk (rating >= 70)."""
        return self.risk_rating >= 70

    @property
    def is_new_merchant(self) -> bool:
        """Check if merchant is new (< 100 transactions)."""
        return self.total_transactions < 100

    @property
    def fraud_rate_percentage(self) -> float:
        """Get fraud rate as float percentage."""
        return float(self.historical_fraud_rate)

    @property
    def average_transaction_amount(self) -> Decimal:
        """Calculate average transaction amount."""
        if self.total_transactions == 0:
            return Decimal("0.00")

        return (self.total_volume / self.total_transactions).quantize(Decimal("0.01"))

    def get_risk_level(self) -> str:
        """Get risk level classification.

        Returns:
            Risk level (low, medium, high, critical)
        """
        if self.risk_rating >= 80:
            return "critical"
        elif self.risk_rating >= 60:
            return "high"
        elif self.risk_rating >= 40:
            return "medium"
        else:
            return "low"
