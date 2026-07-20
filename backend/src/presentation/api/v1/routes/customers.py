"""Customer API Routes.

Provides CRUD endpoints for customer management.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.application.dtos.customer_dtos import (
    CreateCustomerRequest,
    CustomerResponse,
    UpdateCustomerRequest,
)
from src.application.use_cases.customer_use_cases import (
    CreateCustomerUseCase,
    DeleteCustomerUseCase,
    GetCustomerUseCase,
    UpdateCustomerUseCase,
)
from src.config.logging_config import get_logger
from src.domain.entities.user import User
from src.infrastructure.security.authorization import require_authenticated
from src.presentation.api.dependencies import (
    get_create_customer_use_case,
    get_delete_customer_use_case,
    get_get_customer_use_case,
    get_update_customer_use_case,
)
from src.presentation.api.response import APIResponse, success_response

logger = get_logger(__name__)

router = APIRouter(
    prefix="/customers",
    tags=["customers"],
)


@router.post(
    "",
    response_model=APIResponse[CustomerResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
    description="Create a new customer account with KYC validation",
    responses={
        201: {
            "description": "Customer created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Customer created successfully",
                        "data": {
                            "customer_id": "123e4567-e89b-12d3-a456-426614174000",
                            "customer_name": "John Doe",
                            "email": "john.doe@example.com",
                            "country": "USA",
                            "kyc_status": "not_started",
                            "customer_risk_category": "medium",
                            "credit_score": 650,
                            "historical_fraud_count": 0,
                            "lifetime_transaction_volume": 0.0,
                            "account_age_days": 0,
                            "is_active": True,
                            "is_verified": False,
                            "can_transact": False,
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z",
                        },
                        "metadata": {
                            "request_id": "550e8400-e29b-41d4-a716-446655440000",
                            "timestamp": "2024-01-15T10:30:00Z",
                            "api_version": "v1",
                        },
                    }
                }
            },
        },
        409: {"description": "Customer with this email already exists"},
        422: {"description": "Validation error"},
    },
)
async def create_customer(
    request: CreateCustomerRequest,
    current_user: Annotated[User, Depends(require_authenticated)],
    use_case: CreateCustomerUseCase = Depends(get_create_customer_use_case),
) -> APIResponse[CustomerResponse]:
    """Create a new customer.

    Args:
        request: Customer creation request
        use_case: Create customer use case

    Returns:
        API response with created customer data
    """
    logger.info(
        "Creating customer",
        email=request.email,
        country=request.country,
    )

    customer = await use_case.execute(request)

    logger.info(
        "Customer created",
        customer_id=str(customer.customer_id),
        email=customer.email,
    )

    return success_response(
        data=customer,
        message="Customer created successfully",
    )


@router.get(
    "/{customer_id}",
    response_model=APIResponse[CustomerResponse],
    status_code=status.HTTP_200_OK,
    summary="Get customer by ID",
    description="Retrieve customer details by unique identifier",
    responses={
        200: {"description": "Customer found"},
        404: {"description": "Customer not found"},
    },
)
async def get_customer(
    customer_id: UUID,
    current_user: Annotated[User, Depends(require_authenticated)],
    use_case: GetCustomerUseCase = Depends(get_get_customer_use_case),
) -> APIResponse[CustomerResponse]:
    """Get customer by ID.

    Args:
        customer_id: Customer UUID
        use_case: Get customer use case

    Returns:
        API response with customer data
    """
    logger.info("Retrieving customer", customer_id=str(customer_id))

    customer = await use_case.execute(customer_id)

    return success_response(
        data=customer,
        message="Customer retrieved successfully",
    )


@router.put(
    "/{customer_id}",
    response_model=APIResponse[CustomerResponse],
    status_code=status.HTTP_200_OK,
    summary="Update customer",
    description="Update customer information",
    responses={
        200: {"description": "Customer updated successfully"},
        404: {"description": "Customer not found"},
        422: {"description": "Validation error"},
    },
)
async def update_customer(
    customer_id: UUID,
    request: UpdateCustomerRequest,
    current_user: Annotated[User, Depends(require_authenticated)],
    use_case: UpdateCustomerUseCase = Depends(get_update_customer_use_case),
) -> APIResponse[CustomerResponse]:
    """Update customer information.

    Args:
        customer_id: Customer UUID
        request: Customer update request
        use_case: Update customer use case

    Returns:
        API response with updated customer data
    """
    logger.info(
        "Updating customer",
        customer_id=str(customer_id),
        fields=request.model_dump(exclude_unset=True),
    )

    customer = await use_case.execute(customer_id, request)

    logger.info("Customer updated", customer_id=str(customer_id))

    return success_response(
        data=customer,
        message="Customer updated successfully",
    )


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete customer",
    description="Soft delete customer account (deactivate)",
    responses={
        204: {"description": "Customer deleted successfully"},
        404: {"description": "Customer not found"},
    },
)
async def delete_customer(
    customer_id: UUID,
    current_user: Annotated[User, Depends(require_authenticated)],
    reason: str
    | None = Query(
        default="User requested deletion",
        description="Reason for deletion",
    ),
    use_case: DeleteCustomerUseCase = Depends(get_delete_customer_use_case),
) -> None:
    """Delete (deactivate) customer account.

    Args:
        customer_id: Customer UUID
        reason: Reason for deletion
        use_case: Delete customer use case
    """
    logger.info(
        "Deleting customer",
        customer_id=str(customer_id),
        reason=reason,
    )

    await use_case.execute(
        customer_id,
        reason=reason if reason is not None else "User requested deletion",
    )

    logger.info("Customer deleted", customer_id=str(customer_id))
