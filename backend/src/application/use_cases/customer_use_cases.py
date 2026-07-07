"""Customer Use Cases (CQRS Pattern)."""

from uuid import UUID

from src.application.dtos.customer_dtos import (
    CreateCustomerRequest,
    CustomerResponse,
    UpdateCustomerRequest,
)
from src.application.services.customer_service import CustomerService
from src.domain.entities.customer import Customer


class CreateCustomerUseCase:
    """Use case for creating a new customer.

    Responsibility: Create a customer and return response DTO.
    """

    def __init__(self, customer_service: CustomerService) -> None:
        """Initialize use case.

        Args:
            customer_service: Customer service instance
        """
        self._service = customer_service

    async def execute(
        self,
        request: CreateCustomerRequest,
        user_id: UUID | None = None,
    ) -> CustomerResponse:
        """Execute create customer use case.

        Args:
            request: Create customer request DTO
            user_id: User performing the action

        Returns:
            Customer response DTO

        Raises:
            ValidationException: If validation fails
            ConflictException: If email already exists
        """
        # Create customer via service
        customer = await self._service.create_customer(
            customer_name=request.customer_name,
            email=request.email,
            country=request.country,
            date_of_birth=request.date_of_birth,
            user_id=user_id,
        )

        # Convert to response DTO
        return self._to_response(customer)

    @staticmethod
    def _to_response(customer: Customer) -> CustomerResponse:
        """Convert domain entity to response DTO."""
        return CustomerResponse(
            customer_id=customer.customer_id,
            customer_name=customer.customer_name,
            email=customer.email,
            country=customer.country,
            kyc_status=customer.kyc_status,
            customer_risk_category=customer.customer_risk_category,
            credit_score=customer.credit_score,
            historical_fraud_count=customer.historical_fraud_count,
            lifetime_transaction_volume=float(customer.lifetime_transaction_volume),
            account_age_days=customer.account_age_days,
            is_active=customer.is_active,
            is_verified=customer.is_verified,
            can_transact=customer.can_transact,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
        )


class UpdateCustomerUseCase:
    """Use case for updating a customer.

    Responsibility: Update customer and return response DTO.
    """

    def __init__(self, customer_service: CustomerService) -> None:
        """Initialize use case.

        Args:
            customer_service: Customer service instance
        """
        self._service = customer_service

    async def execute(
        self,
        customer_id: UUID,
        request: UpdateCustomerRequest,
        user_id: UUID | None = None,
    ) -> CustomerResponse:
        """Execute update customer use case.

        Args:
            customer_id: Customer UUID
            request: Update customer request DTO
            user_id: User performing the action

        Returns:
            Customer response DTO

        Raises:
            EntityNotFoundException: If customer not found
            ValidationException: If validation fails
        """
        # Build updates dictionary
        updates = {}
        if request.customer_name is not None:
            updates["customer_name"] = request.customer_name
        if request.credit_score is not None:
            updates["credit_score"] = request.credit_score

        # Update customer via service
        customer = await self._service.update_customer(
            customer_id=customer_id,
            updates=updates,
            user_id=user_id,
        )

        # Convert to response DTO
        return CreateCustomerUseCase._to_response(customer)


class DeleteCustomerUseCase:
    """Use case for deleting (deactivating) a customer.

    Responsibility: Deactivate customer (soft delete).
    """

    def __init__(self, customer_service: CustomerService) -> None:
        """Initialize use case.

        Args:
            customer_service: Customer service instance
        """
        self._service = customer_service

    async def execute(
        self,
        customer_id: UUID,
        reason: str = "User requested deletion",
        user_id: UUID | None = None,
    ) -> None:
        """Execute delete customer use case.

        Args:
            customer_id: Customer UUID
            reason: Reason for deletion
            user_id: User performing the action

        Raises:
            EntityNotFoundException: If customer not found
        """
        await self._service.deactivate_customer(
            customer_id=customer_id,
            reason=reason,
            user_id=user_id,
        )


class GetCustomerUseCase:
    """Use case for retrieving a customer.

    Responsibility: Get customer by ID and return response DTO.
    """

    def __init__(self, customer_service: CustomerService) -> None:
        """Initialize use case.

        Args:
            customer_service: Customer service instance
        """
        self._service = customer_service

    async def execute(
        self,
        customer_id: UUID,
    ) -> CustomerResponse:
        """Execute get customer use case.

        Args:
            customer_id: Customer UUID

        Returns:
            Customer response DTO

        Raises:
            EntityNotFoundException: If customer not found
        """
        # Get customer profile (includes all calculated fields)
        profile = await self._service.calculate_customer_profile(customer_id)

        # Convert to response DTO
        return CustomerResponse(
            customer_id=UUID(profile["customer_id"]),
            customer_name=profile["customer_name"],
            email=profile["email"],
            country=profile["country"],
            kyc_status=profile["kyc_status"],
            customer_risk_category=profile["risk_category"],
            credit_score=profile["credit_score"],
            historical_fraud_count=profile["historical_fraud_count"],
            lifetime_transaction_volume=profile["lifetime_transaction_volume"],
            account_age_days=profile["account_age_days"],
            is_active=profile["is_active"],
            is_verified=profile["is_verified"],
            can_transact=profile["can_transact"],
            created_at=profile["created_at"],
            updated_at=profile["updated_at"],
        )
