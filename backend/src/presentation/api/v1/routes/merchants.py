"""Merchant API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.dtos.common import PageRequest
from src.application.dtos.merchant_dtos import (
    CreateMerchantRequest,
    MerchantListRequest,
    MerchantResponse,
    SuspendMerchantRequest,
    UpdateMerchantRequest,
)
from src.application.use_cases.merchant_use_cases import (
    CreateMerchantUseCase,
    DeleteMerchantUseCase,
    GetMerchantUseCase,
    ListMerchantsUseCase,
    SuspendMerchantUseCase,
    UpdateMerchantUseCase,
)
from src.config.logging_config import get_logger
from src.domain.entities.user import User
from src.infrastructure.security.authorization import require_analyst
from src.presentation.api.dependencies import (
    get_create_merchant_use_case,
    get_delete_merchant_use_case,
    get_get_merchant_use_case,
    get_list_merchants_use_case,
    get_suspend_merchant_use_case,
    get_update_merchant_use_case,
)
from src.presentation.api.response import APIResponse, success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.post(
    "",
    response_model=APIResponse[MerchantResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a merchant",
    description="Create a new merchant profile",
)
async def create_merchant(
    request: CreateMerchantRequest,
    current_user: Annotated[User, Depends(require_analyst)],
    use_case: CreateMerchantUseCase = Depends(get_create_merchant_use_case),
) -> APIResponse[MerchantResponse]:
    """Create a merchant."""
    logger.info("Creating merchant", merchant_name=request.merchant_name)
    merchant = await use_case.execute(request)
    return success_response(data=merchant, message="Merchant created successfully")


@router.get(
    "/{merchant_id}",
    response_model=APIResponse[MerchantResponse],
    status_code=status.HTTP_200_OK,
    summary="Get merchant by ID",
)
async def get_merchant(
    merchant_id: UUID,
    current_user: Annotated[User, Depends(require_analyst)],
    use_case: GetMerchantUseCase = Depends(get_get_merchant_use_case),
) -> APIResponse[MerchantResponse]:
    """Retrieve a merchant by identifier."""
    try:
        merchant = await use_case.execute(merchant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return success_response(data=merchant, message="Merchant retrieved successfully")


@router.get(
    "",
    response_model=APIResponse[list[MerchantResponse]],
    status_code=status.HTTP_200_OK,
    summary="List merchants",
)
async def list_merchants(
    current_user: Annotated[User, Depends(require_analyst)],
    merchant_category: str | None = Query(default=None),
    country: str | None = Query(default=None),
    min_risk_rating: int | None = Query(default=None),
    max_risk_rating: int | None = Query(default=None),
    is_suspended: bool | None = Query(default=None),
    min_fraud_rate: float | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=1000),
    use_case: ListMerchantsUseCase = Depends(get_list_merchants_use_case),
) -> APIResponse[list[MerchantResponse]]:
    """List merchants with optional filters."""
    request = MerchantListRequest(
        merchant_category=merchant_category,
        country=country,
        min_risk_rating=min_risk_rating,
        max_risk_rating=max_risk_rating,
        is_suspended=is_suspended,
        min_fraud_rate=min_fraud_rate,
    )
    page_request = PageRequest(page=page, page_size=page_size)
    result = await use_case.execute(request, page_request)
    return success_response(data=result.items, message="Merchants retrieved successfully")


@router.put(
    "/{merchant_id}",
    response_model=APIResponse[MerchantResponse],
    status_code=status.HTTP_200_OK,
    summary="Update merchant",
)
async def update_merchant(
    merchant_id: UUID,
    request: UpdateMerchantRequest,
    current_user: Annotated[User, Depends(require_analyst)],
    use_case: UpdateMerchantUseCase = Depends(get_update_merchant_use_case),
) -> APIResponse[MerchantResponse]:
    """Update merchant details."""
    merchant = await use_case.execute(merchant_id, request)
    return success_response(data=merchant, message="Merchant updated successfully")


@router.post(
    "/{merchant_id}/suspend",
    response_model=APIResponse[MerchantResponse],
    status_code=status.HTTP_200_OK,
    summary="Suspend merchant",
)
async def suspend_merchant(
    merchant_id: UUID,
    request: SuspendMerchantRequest,
    current_user: Annotated[User, Depends(require_analyst)],
    use_case: SuspendMerchantUseCase = Depends(get_suspend_merchant_use_case),
) -> APIResponse[MerchantResponse]:
    """Suspend a merchant."""
    merchant = await use_case.execute(merchant_id, request)
    return success_response(data=merchant, message="Merchant suspended successfully")


@router.delete(
    "/{merchant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete merchant",
)
async def delete_merchant(
    merchant_id: UUID,
    current_user: Annotated[User, Depends(require_analyst)],
    reason: str | None = Query(default="Business closure"),
    use_case: DeleteMerchantUseCase = Depends(get_delete_merchant_use_case),
) -> None:
    """Delete a merchant."""
    await use_case.execute(
        merchant_id,
        reason=reason if reason is not None else "Business closure",
    )
