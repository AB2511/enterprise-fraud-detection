"""SQLAlchemy ORM Models - Base and common mixins.

NOTE: Actual table models (transactions, predictions, etc.) will be added in future phases.
This file establishes the base model structure and common patterns.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.infrastructure.database.types import PortableJSON


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class UUIDMixin:
    """Mixin for UUID primary key."""

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete support."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark record as deleted."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore soft deleted record."""
        self.deleted_at = None


class AuditMixin:
    """Mixin for audit fields (who created/modified)."""

    created_by: Mapped[str] = mapped_column(
        String(255),
        default="system",
        nullable=False,
    )

    updated_by: Mapped[str] = mapped_column(
        String(255),
        default="system",
        nullable=False,
    )


# =============================================================================
# Domain Models
# =============================================================================


class UserModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CustomerModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Customer model representing bank customers."""

    __tablename__ = "customers"

    customer_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    country: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    kyc_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    customer_risk_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    historical_fraud_count: Mapped[int] = mapped_column(default=0, nullable=False)
    credit_score: Mapped[int] = mapped_column(default=650, nullable=False)
    lifetime_transaction_volume: Mapped[float] = mapped_column(default=0.0, nullable=False)
    account_age_days: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class MerchantModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Merchant model representing businesses accepting payments."""

    __tablename__ = "merchants"

    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mcc: Mapped[str] = mapped_column(String(4), nullable=False, index=True)
    merchant_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    risk_rating: Mapped[int] = mapped_column(default=50, nullable=False)
    historical_fraud_rate: Mapped[float] = mapped_column(default=0.0, nullable=False)
    total_transactions: Mapped[int] = mapped_column(default=0, nullable=False)
    total_volume: Mapped[float] = mapped_column(default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class TransactionModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Transaction model representing financial transactions."""

    __tablename__ = "transactions"

    customer_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    merchant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Payment details
    payment_channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    terminal_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Device and location
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    
    # Velocity metrics
    velocity_1h: Mapped[float | None] = mapped_column(nullable=True)
    velocity_24h: Mapped[float | None] = mapped_column(nullable=True)
    velocity_7d: Mapped[float | None] = mapped_column(nullable=True)
    
    # Fraud information
    is_fraud: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    fraud_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PredictionModel(Base, UUIDMixin, TimestampMixin):
    """Prediction model for ML fraud predictions."""

    __tablename__ = "predictions"

    transaction_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    model_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Prediction results
    prediction_class: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    fraud_probability: Mapped[float] = mapped_column(nullable=False)
    anomaly_score: Mapped[float | None] = mapped_column(nullable=True)
    risk_score: Mapped[float | None] = mapped_column(nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    
    # Decision
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Performance
    latency_ms: Mapped[float | None] = mapped_column(nullable=True)
    
    # Flexible explanation data
    explanation_data: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)


class AlertModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Alert model for fraud alerts requiring analyst review."""

    __tablename__ = "alerts"

    transaction_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    prediction_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Alert details
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Assignment
    assigned_analyst_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Resolution
    resolution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # SLA tracking
    sla_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_sla_breached: Mapped[bool] = mapped_column(default=False, nullable=False)


class AuditLogModel(Base, UUIDMixin):
    """Audit log model for immutable audit trail."""

    __tablename__ = "audit_logs"

    # Immutable - no updated_at, no soft delete
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    
    # Entity information
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Action details
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Changes
    old_value: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    
    # Context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ModelModel(Base, UUIDMixin, TimestampMixin):
    """Model metadata tracking ML model versions and deployments."""

    __tablename__ = "models"

    # Model identification
    version: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    model_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Artifact storage
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Model metadata and metrics (stored as JSON) - renamed to avoid SQLAlchemy reserved word
    model_metadata: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)
    metrics: Mapped[dict] = mapped_column(PortableJSON, nullable=False, default=dict)
    
    # Lifecycle
    training_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="training", index=True)
    
    # Tracking
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, default="system")


class AnalystFeedbackModel(Base, UUIDMixin, TimestampMixin):
    """Analyst feedback model for tracking human corrections."""

    __tablename__ = "analyst_feedback"

    prediction_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    analyst_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Feedback
    is_fraud: Mapped[bool] = mapped_column(nullable=False)
    confidence: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    # Context
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
