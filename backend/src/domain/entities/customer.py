"""Customer Entity - Bank customer."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass
class Customer:
    """Customer entity representing a bank customer.

    Customers are the users who make transactions. This entity tracks
    customer risk profile, KYC status, and historical fraud patterns.

    Attributes:
        customer_id: Unique identifier
        customer_name: Full name
        email: Customer email
        date_of_birth: Date of birth
        country: Country of residence
        kyc_status: KYC verification status (pending, verified, rejected)
        customer_risk_category: Risk category (low, medium, high, critical)
        historical_fraud_count: Number of confirmed fraud cases
        credit_score: Credit score (300-850)
        lifetime_transaction_volume: Total transaction amount
        account_age_days: Days since account creation
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        is_active: Account active status
    """

    customer_id: UUID = field(default_factory=uuid4)
    customer_name: str = ""
    email: str = ""
    date_of_birth: date | None = None
    country: str = ""
    kyc_status: str = "pending"
    customer_risk_category: str = "medium"
    historical_fraud_count: int = 0
    credit_score: int = 650
    lifetime_transaction_volume: Decimal = Decimal("0.00")
    account_age_days: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True

    def __post_init__(self) -> None:
        """Validate customer business rules."""
        if not self.customer_name:
            raise ValueError("Customer name is required")

        if not self.email or "@" not in self.email:
            raise ValueError("Valid email address is required")

        if not self.country:
            raise ValueError("Country is required")

        valid_kyc_statuses = ["pending", "verified", "rejected", "expired"]
        if self.kyc_status not in valid_kyc_statuses:
            raise ValueError(f"KYC status must be one of: {valid_kyc_statuses}")

        valid_risk_categories = ["low", "medium", "high", "critical"]
        if self.customer_risk_category not in valid_risk_categories:
            raise ValueError(f"Risk category must be one of: {valid_risk_categories}")

        if self.credit_score < 300 or self.credit_score > 850:
            raise ValueError("Credit score must be between 300 and 850")

        if self.historical_fraud_count < 0:
            raise ValueError("Fraud count cannot be negative")

        if self.lifetime_transaction_volume < Decimal("0"):
            raise ValueError("Transaction volume cannot be negative")

        if self.account_age_days < 0:
            raise ValueError("Account age cannot be negative")

    def update_credit_score(self, new_score: int) -> None:
        """Update customer credit score.

        Args:
            new_score: New credit score (300-850)

        Raises:
            ValueError: If score is out of range
        """
        if new_score < 300 or new_score > 850:
            raise ValueError("Credit score must be between 300 and 850")

        self.credit_score = new_score
        self.updated_at = datetime.utcnow()

        # Recalculate risk category based on new score
        self._recalculate_risk_category()

    def increment_fraud_counter(self) -> None:
        """Increment historical fraud count."""
        self.historical_fraud_count += 1
        self.updated_at = datetime.utcnow()

        # Recalculate risk category
        self._recalculate_risk_category()

    def add_transaction_volume(self, amount: Decimal) -> None:
        """Add to lifetime transaction volume.

        Args:
            amount: Transaction amount to add
        """
        if amount < Decimal("0"):
            raise ValueError("Amount cannot be negative")

        self.lifetime_transaction_volume += amount
        self.updated_at = datetime.utcnow()

    def calculate_customer_risk(self) -> str:
        """Calculate customer risk category based on multiple factors.

        Returns:
            Risk category (low, medium, high, critical)
        """
        risk_score = 0

        # Credit score factor
        if self.credit_score < 500:
            risk_score += 3
        elif self.credit_score < 650:
            risk_score += 2
        elif self.credit_score < 750:
            risk_score += 1

        # Fraud history factor
        if self.historical_fraud_count >= 3:
            risk_score += 4
        elif self.historical_fraud_count >= 1:
            risk_score += 2

        # Account age factor (new accounts are riskier)
        if self.account_age_days < 30:
            risk_score += 2
        elif self.account_age_days < 90:
            risk_score += 1

        # KYC factor
        if self.kyc_status == "rejected" or self.kyc_status == "expired":
            risk_score += 3
        elif self.kyc_status == "pending":
            risk_score += 1

        # Determine category
        if risk_score >= 7:
            return "critical"
        elif risk_score >= 5:
            return "high"
        elif risk_score >= 3:
            return "medium"
        else:
            return "low"

    def _recalculate_risk_category(self) -> None:
        """Recalculate and update risk category."""
        self.customer_risk_category = self.calculate_customer_risk()

    def verify_kyc(self) -> None:
        """Mark KYC as verified."""
        self.kyc_status = "verified"
        self.updated_at = datetime.utcnow()
        self._recalculate_risk_category()

    def reject_kyc(self) -> None:
        """Mark KYC as rejected."""
        self.kyc_status = "rejected"
        self.updated_at = datetime.utcnow()
        self._recalculate_risk_category()

    def deactivate(self) -> None:
        """Deactivate customer account."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def reactivate(self) -> None:
        """Reactivate customer account."""
        if self.kyc_status != "verified":
            raise ValueError("Cannot reactivate account without verified KYC")

        self.is_active = True
        self.updated_at = datetime.utcnow()

    @property
    def is_verified(self) -> bool:
        """Check if customer has verified KYC."""
        return self.kyc_status == "verified"

    @property
    def is_high_risk(self) -> bool:
        """Check if customer is high or critical risk."""
        return self.customer_risk_category in ["high", "critical"]

    @property
    def age_years(self) -> int | None:
        """Calculate customer age in years."""
        if not self.date_of_birth:
            return None

        today = date.today()
        age = today.year - self.date_of_birth.year

        # Adjust for birthday not yet occurred this year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age -= 1

        return age

    @property
    def can_transact(self) -> bool:
        """Check if customer can make transactions."""
        return (
            self.is_active and
            self.kyc_status == "verified" and
            self.customer_risk_category != "critical"
        )
