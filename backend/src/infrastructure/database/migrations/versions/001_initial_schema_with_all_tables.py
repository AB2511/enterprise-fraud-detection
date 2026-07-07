"""initial_schema_with_all_tables

Revision ID: 001
Revises:
Create Date: 2026-07-07 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all tables for fraud detection system."""

    # Users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])

    # Customers table
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("date_of_birth", sa.DateTime(timezone=False), nullable=True),
        sa.Column("country", sa.String(3), nullable=False),
        sa.Column("kyc_status", sa.String(50), nullable=False),
        sa.Column("customer_risk_category", sa.String(50), nullable=False),
        sa.Column("historical_fraud_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("credit_score", sa.Integer, nullable=False, server_default="650"),
        sa.Column("lifetime_transaction_volume", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("account_age_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_customers_customer_name", "customers", ["customer_name"])
    op.create_index("ix_customers_email", "customers", ["email"])
    op.create_index("ix_customers_country", "customers", ["country"])
    op.create_index("ix_customers_kyc_status", "customers", ["kyc_status"])
    op.create_index("ix_customers_risk_category", "customers", ["customer_risk_category"])

    # Merchants table
    op.create_table(
        "merchants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_name", sa.String(255), nullable=False),
        sa.Column("mcc", sa.String(4), nullable=False),
        sa.Column("merchant_category", sa.String(100), nullable=False),
        sa.Column("country", sa.String(3), nullable=False),
        sa.Column("risk_rating", sa.Integer, nullable=False, server_default="50"),
        sa.Column("historical_fraud_rate", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_transactions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_volume", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_merchants_merchant_name", "merchants", ["merchant_name"])
    op.create_index("ix_merchants_mcc", "merchants", ["mcc"])
    op.create_index("ix_merchants_category", "merchants", ["merchant_category"])
    op.create_index("ix_merchants_country", "merchants", ["country"])

    # Transactions table
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("transaction_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("payment_channel", sa.String(50), nullable=False),
        sa.Column("payment_method", sa.String(50), nullable=False),
        sa.Column("terminal_id", sa.String(100), nullable=True),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("velocity_1h", sa.Float, nullable=True),
        sa.Column("velocity_24h", sa.Float, nullable=True),
        sa.Column("velocity_7d", sa.Float, nullable=True),
        sa.Column("is_fraud", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("fraud_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_transactions_customer_id", "transactions", ["customer_id"])
    op.create_index("ix_transactions_merchant_id", "transactions", ["merchant_id"])
    op.create_index("ix_transactions_type", "transactions", ["transaction_type"])
    op.create_index("ix_transactions_status", "transactions", ["status"])
    op.create_index("ix_transactions_channel", "transactions", ["payment_channel"])
    op.create_index("ix_transactions_method", "transactions", ["payment_method"])
    op.create_index("ix_transactions_device_id", "transactions", ["device_id"])
    op.create_index("ix_transactions_is_fraud", "transactions", ["is_fraud"])
    op.create_index("ix_transactions_created_at", "transactions", ["created_at"])

    # Composite indexes for common queries
    op.create_index(
        "ix_transactions_customer_created", "transactions", ["customer_id", "created_at"]
    )
    op.create_index(
        "ix_transactions_merchant_created", "transactions", ["merchant_id", "created_at"]
    )

    # Predictions table
    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("prediction_class", sa.String(50), nullable=False),
        sa.Column("fraud_probability", sa.Float, nullable=False),
        sa.Column("anomaly_score", sa.Float, nullable=True),
        sa.Column("risk_score", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column("explanation_data", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_predictions_transaction_id", "predictions", ["transaction_id"])
    op.create_index("ix_predictions_model_id", "predictions", ["model_id"])
    op.create_index("ix_predictions_class", "predictions", ["prediction_class"])

    # Alerts table
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("assigned_analyst_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_sla_breached", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_analyst_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_alerts_transaction_id", "alerts", ["transaction_id"])
    op.create_index("ix_alerts_prediction_id", "alerts", ["prediction_id"])
    op.create_index("ix_alerts_type", "alerts", ["alert_type"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_analyst_id", "alerts", ["assigned_analyst_id"])

    # Audit logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("old_value", postgresql.JSONB, nullable=True),
        sa.Column("new_value", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])

    # Composite index for entity audit trail
    op.create_index(
        "ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id", "created_at"]
    )

    # Analyst feedback table
    op.create_table(
        "analyst_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analyst_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_fraud", sa.Boolean, nullable=False),
        sa.Column("confidence", sa.String(50), nullable=False),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column(
            "reviewed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analyst_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_analyst_feedback_prediction_id", "analyst_feedback", ["prediction_id"])
    op.create_index("ix_analyst_feedback_analyst_id", "analyst_feedback", ["analyst_id"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("analyst_feedback")
    op.drop_table("audit_logs")
    op.drop_table("alerts")
    op.drop_table("predictions")
    op.drop_table("transactions")
    op.drop_table("merchants")
    op.drop_table("customers")
    op.drop_table("users")
