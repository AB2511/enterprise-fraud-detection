"""Transaction Entity - Aggregate Root."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass
class Transaction:
    """Transaction aggregate root representing a financial transaction.

    This is the primary entity for fraud detection analysis.
    Contains all transaction details and optional fraud label (ground truth).

    Attributes:
        transaction_id: Unique identifier for the transaction
        customer_id: Customer making the transaction
        merchant_id: Merchant receiving payment
        amount: Transaction amount
        currency: Currency code (e.g., USD, EUR)
        timestamp: When the transaction occurred
        payment_channel: Channel (online, pos, atm, mobile)
        payment_method: Method (card, bank_transfer, wallet)
        device_id: Device identifier used for transaction
        ip_address: IP address of the transaction origin
        latitude: Geographic latitude
        longitude: Geographic longitude
        terminal_id: Terminal identifier for POS transactions
        merchant_category: Category of merchant business
        mcc: Merchant Category Code
        card_type: Type of card used (visa, mastercard, etc.)
        card_last_four: Last 4 digits of card
        status: Transaction status (pending, approved, declined, failed)
        is_fraud: Ground truth label (None if unlabeled)
        velocity_1h: Transactions by customer in last 1 hour
        velocity_24h: Transactions by customer in last 24 hours
        velocity_7d: Transactions by customer in last 7 days
        created_at: When this record was created
        updated_at: Last update timestamp
    """

    transaction_id: UUID = field(default_factory=uuid4)
    customer_id: UUID = field(default_factory=uuid4)
    merchant_id: UUID = field(default_factory=uuid4)
    amount: Decimal = Decimal("0.00")
    currency: str = "USD"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    payment_channel: str = "online"
    payment_method: str = "card"
    device_id: str | None = None
    ip_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    terminal_id: str | None = None
    merchant_category: str = ""
    mcc: str = ""
    card_type: str | None = None
    card_last_four: str | None = None
    status: str = "pending"
    is_fraud: bool | None = None
    velocity_1h: int = 0
    velocity_24h: int = 0
    velocity_7d: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate transaction business rules."""
        if self.amount < Decimal("0"):
            raise ValueError("Transaction amount cannot be negative")

        if not self.currency or len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter code")

        if self.timestamp > datetime.utcnow():
            raise ValueError("Transaction timestamp cannot be in the future")

        valid_channels = ["online", "pos", "atm", "mobile", "phone"]
        if self.payment_channel not in valid_channels:
            raise ValueError(f"Payment channel must be one of: {valid_channels}")

        valid_methods = ["card", "bank_transfer", "wallet", "cash", "crypto"]
        if self.payment_method not in valid_methods:
            raise ValueError(f"Payment method must be one of: {valid_methods}")

        valid_statuses = ["pending", "approved", "declined", "failed", "reversed"]
        if self.status not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")

        if self.card_last_four and len(self.card_last_four) != 4:
            raise ValueError("Card last four must be exactly 4 characters")

    def validate(self) -> bool:
        """Validate transaction against business rules.

        Returns:
            True if transaction passes validation
        """
        # Negative amount check
        if self.amount <= Decimal("0"):
            return False

        # Future timestamp check
        if self.timestamp > datetime.utcnow():
            return False

        # Fraud label immutability check
        if self.is_fraud is not None and self.status != "approved":
            return False

        return True

    def approve(self) -> None:
        """Approve the transaction."""
        if self.status == "approved":
            raise ValueError("Transaction is already approved")

        self.status = "approved"
        self.updated_at = datetime.utcnow()

    def decline(self, reason: str = "fraud_suspected") -> None:
        """Decline the transaction.

        Args:
            reason: Reason for decline
        """
        if self.status in ["approved", "declined"]:
            raise ValueError(f"Cannot decline transaction with status: {self.status}")

        self.status = "declined"
        self.updated_at = datetime.utcnow()

    def mark_as_fraud(self) -> None:
        """Mark this transaction as confirmed fraud."""
        if self.is_fraud is not None:
            raise ValueError("Fraud label is immutable once set")

        self.is_fraud = True
        self.updated_at = datetime.utcnow()

    def mark_as_legitimate(self) -> None:
        """Mark this transaction as confirmed legitimate."""
        if self.is_fraud is not None:
            raise ValueError("Fraud label is immutable once set")

        self.is_fraud = False
        self.updated_at = datetime.utcnow()

    def calculate_velocity(self, transactions_1h: int, transactions_24h: int, transactions_7d: int) -> None:
        """Calculate and store velocity metrics.

        Args:
            transactions_1h: Count in last 1 hour
            transactions_24h: Count in last 24 hours
            transactions_7d: Count in last 7 days
        """
        self.velocity_1h = transactions_1h
        self.velocity_24h = transactions_24h
        self.velocity_7d = transactions_7d
        self.updated_at = datetime.utcnow()

    def risk_snapshot(self) -> dict[str, any]:
        """Generate risk snapshot for this transaction.

        Returns:
            Dictionary with risk indicators
        """
        return {
            "amount": float(self.amount),
            "is_high_value": self.amount > Decimal("1000.00"),
            "payment_channel": self.payment_channel,
            "velocity_1h": self.velocity_1h,
            "velocity_24h": self.velocity_24h,
            "has_geolocation": self.has_geolocation,
            "is_international": self.is_international_transaction(),
            "is_night_transaction": self.is_night_time(),
        }

    def is_international_transaction(self) -> bool:
        """Check if transaction appears to be international.

        Returns:
            True if likely international (based on heuristics)
        """
        # This would need merchant country in a real system
        return self.payment_channel == "online" and self.amount > Decimal("500.00")

    def is_night_time(self) -> bool:
        """Check if transaction occurred during night hours (10 PM - 6 AM).

        Returns:
            True if night transaction
        """
        hour = self.timestamp.hour
        return hour >= 22 or hour < 6

    @property
    def has_label(self) -> bool:
        """Check if transaction has a ground truth label."""
        return self.is_fraud is not None

    @property
    def has_geolocation(self) -> bool:
        """Check if transaction has geolocation data."""
        return self.latitude is not None and self.longitude is not None

    @property
    def is_approved(self) -> bool:
        """Check if transaction was approved."""
        return self.status == "approved"

    @property
    def is_declined(self) -> bool:
        """Check if transaction was declined."""
        return self.status == "declined"

    @property
    def is_high_velocity(self) -> bool:
        """Check if transaction has high velocity (> 5 in 1 hour)."""
        return self.velocity_1h > 5
