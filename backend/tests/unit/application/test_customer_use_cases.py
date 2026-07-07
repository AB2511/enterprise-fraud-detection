"""Unit Tests for Customer Use Cases.

Tests the CQRS use case layer in isolation using mocks.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.dtos.customer_dtos import (
    CreateCustomerRequest,
    CustomerResponse,
    UpdateCustomerRequest,
)
from src.application.services.customer_service import CustomerService
from src.application.use_cases.customer_use_cases import (
    CreateCustomerUseCase,
    DeleteCustomerUseCase,
    GetCustomerUseCase,
    UpdateCustomerUseCase,
)
from src.domain.entities.customer import Customer


@pytest.fixture
def mock_customer_service():
    """Create mock customer service."""
    return MagicMock(spec=CustomerService)


class TestCreateCustomerUseCase:
    """Test CreateCustomerUseCase."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        mock_customer_service: MagicMock,
        customer_factory,
    ):
        """Test successful customer creation."""
        # Arrange
        expected_customer = customer_factory.create(
            customer_name="John Doe",
            email="john.doe@example.com",
            country="USA",
            date_of_birth=date(1990, 1, 15),
        )
        
        mock_customer_service.create_customer = AsyncMock(return_value=expected_customer)
        use_case = CreateCustomerUseCase(mock_customer_service)

        request = CreateCustomerRequest(
            customer_name="John Doe",
            email="john.doe@example.com",
            country="USA",
            date_of_birth=date(1990, 1, 15),
        )

        # Act
        result = await use_case.execute(request)

        # Assert
        assert isinstance(result, CustomerResponse)
        assert result.customer_id == expected_customer.customer_id
        assert result.customer_name == "John Doe"
        assert result.email == "john.doe@example.com"
        assert result.country == "USA"

        mock_customer_service.create_customer.assert_called_once_with(
            customer_name="John Doe",
            email="john.doe@example.com",
            country="USA",
            date_of_birth=date(1990, 1, 15),
            user_id=None,
        )

    @pytest.mark.asyncio
    async def test_execute_with_user_id(
        self,
        mock_customer_service: MagicMock,
        sample_customer: Customer,
    ):
        """Test customer creation with user ID."""
        # Arrange
        mock_customer_service.create_customer = AsyncMock(return_value=sample_customer)
        use_case = CreateCustomerUseCase(mock_customer_service)
        user_id = uuid4()

        request = CreateCustomerRequest(
            customer_name="John Doe",
            email="john.doe@example.com",
            country="USA",
        )

        # Act
        result = await use_case.execute(request, user_id=user_id)

        # Assert
        assert isinstance(result, CustomerResponse)
        mock_customer_service.create_customer.assert_called_once()
        call_args = mock_customer_service.create_customer.call_args
        assert call_args.kwargs["user_id"] == user_id


class TestUpdateCustomerUseCase:
    """Test UpdateCustomerUseCase."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        mock_customer_service: MagicMock,
        sample_customer: Customer,
    ):
        """Test successful customer update."""
        # Arrange
        updated_customer = Customer(**sample_customer.__dict__)
        updated_customer.customer_name = "John Smith"
        updated_customer.credit_score = 750

        mock_customer_service.update_customer = AsyncMock(return_value=updated_customer)
        use_case = UpdateCustomerUseCase(mock_customer_service)

        request = UpdateCustomerRequest(
            customer_name="John Smith",
            credit_score=750,
        )

        # Act
        result = await use_case.execute(sample_customer.customer_id, request)

        # Assert
        assert isinstance(result, CustomerResponse)
        assert result.customer_name == "John Smith"
        assert result.credit_score == 750

        mock_customer_service.update_customer.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_partial_update(
        self,
        mock_customer_service: MagicMock,
        sample_customer: Customer,
    ):
        """Test partial customer update (only one field)."""
        # Arrange
        mock_customer_service.update_customer = AsyncMock(return_value=sample_customer)
        use_case = UpdateCustomerUseCase(mock_customer_service)

        request = UpdateCustomerRequest(credit_score=750)

        # Act
        result = await use_case.execute(sample_customer.customer_id, request)

        # Assert
        assert isinstance(result, CustomerResponse)
        call_args = mock_customer_service.update_customer.call_args
        updates = call_args.kwargs["updates"]
        assert "credit_score" in updates
        assert "customer_name" not in updates


class TestDeleteCustomerUseCase:
    """Test DeleteCustomerUseCase."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        mock_customer_service: MagicMock,
        sample_customer: Customer,
    ):
        """Test successful customer deletion."""
        # Arrange
        mock_customer_service.deactivate_customer = AsyncMock(return_value=sample_customer)
        use_case = DeleteCustomerUseCase(mock_customer_service)

        # Act
        await use_case.execute(sample_customer.customer_id)

        # Assert
        mock_customer_service.deactivate_customer.assert_called_once_with(
            customer_id=sample_customer.customer_id,
            reason="User requested deletion",
            user_id=None,
        )

    @pytest.mark.asyncio
    async def test_execute_with_custom_reason(
        self,
        mock_customer_service: MagicMock,
        sample_customer: Customer,
    ):
        """Test customer deletion with custom reason."""
        # Arrange
        mock_customer_service.deactivate_customer = AsyncMock(return_value=sample_customer)
        use_case = DeleteCustomerUseCase(mock_customer_service)

        # Act
        await use_case.execute(
            sample_customer.customer_id,
            reason="Compliance violation",
        )

        # Assert
        call_args = mock_customer_service.deactivate_customer.call_args
        assert call_args.kwargs["reason"] == "Compliance violation"


class TestGetCustomerUseCase:
    """Test GetCustomerUseCase."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        mock_customer_service: MagicMock,
        sample_customer: Customer,
    ):
        """Test successful customer retrieval."""
        # Arrange
        profile = {
            "customer_id": str(sample_customer.customer_id),
            "customer_name": sample_customer.customer_name,
            "email": sample_customer.email,
            "country": sample_customer.country,
            "kyc_status": sample_customer.kyc_status,
            "risk_category": sample_customer.customer_risk_category,
            "credit_score": sample_customer.credit_score,
            "historical_fraud_count": sample_customer.historical_fraud_count,
            "lifetime_transaction_volume": float(sample_customer.lifetime_transaction_volume),
            "account_age_days": sample_customer.account_age_days,
            "is_verified": sample_customer.is_verified,
            "can_transact": sample_customer.can_transact,
            "is_active": sample_customer.is_active,
            "created_at": sample_customer.created_at,
            "updated_at": sample_customer.updated_at,
        }

        mock_customer_service.calculate_customer_profile = AsyncMock(return_value=profile)
        use_case = GetCustomerUseCase(mock_customer_service)

        # Act
        result = await use_case.execute(sample_customer.customer_id)

        # Assert
        assert isinstance(result, CustomerResponse)
        assert result.customer_id == sample_customer.customer_id
        assert result.customer_name == sample_customer.customer_name
        assert result.email == sample_customer.email

        mock_customer_service.calculate_customer_profile.assert_called_once_with(
            sample_customer.customer_id
        )
