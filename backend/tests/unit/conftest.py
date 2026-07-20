"""Unit test fixtures."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from src.domain.entities.customer import Customer


class CustomerFactory:
    """Factory for creating Customer entities for testing."""

    @staticmethod
    def create(**kwargs) -> Customer:
        """Create a customer with default or provided values."""
        defaults = {
            "customer_name": "Test Customer",
            "email": "test@example.com",
            "country": "USA",
            "date_of_birth": date(1990, 1, 1),
            "kyc_status": "verified",
            "credit_score": 750,
            "customer_risk_category": "medium",
            "historical_fraud_count": 0,
            "lifetime_transaction_volume": Decimal("10000.00"),
            "account_age_days": 365,
            "is_active": True,
        }
        defaults.update(kwargs)
        return Customer(**defaults)


@pytest.fixture
def customer_factory():
    """Factory for creating customers."""
    return CustomerFactory


@pytest.fixture
def sample_customer():
    """Create a sample customer entity for testing."""
    return Customer(
        customer_id=uuid4(),
        customer_name="Jane Smith",
        email="jane.smith@example.com",
        country="CAN",
        date_of_birth=date(1985, 3, 15),
        kyc_status="verified",
        credit_score=780,
        customer_risk_category="medium",
        historical_fraud_count=0,
        lifetime_transaction_volume=Decimal("25000.00"),
        account_age_days=500,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )