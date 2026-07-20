"""Transaction API routes."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.application.dtos.common import PageRequest
from src.application.dtos.transaction_dtos import (
    CreateTransactionRequest,
    SearchTransactionRequest,
    TransactionResponse,
    UpdateTransactionRequest,
)
from src.application.use_cases.transaction_use_cases import (
    CreateTransactionUseCase,
    GetTransactionUseCase,
    SearchTransactionsUseCase,
    UpdateTransactionUseCase,
)
from src.config.logging_config import get_logger
from src.domain.entities.user import User
from src.infrastructure.security.authorization import require_analyst
from src.presentation.api.dependencies import (
    get_create_transaction_use_case,
    get_get_transaction_use_case,
    get_search_transactions_use_case,
    get_update_transaction_use_case,
)
from src.presentation.api.response import APIResponse, success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post(
    "",
    response_model=APIResponse[TransactionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a transaction",
)
async def create_transaction(
    request: CreateTransactionRequest,
    current_user: Annotated[User, Depends(require_analyst)],
    use_case: CreateTransactionUseCase = Depends(get_create_transaction_use_case),
) -> APIResponse[TransactionResponse]:
    """Create a transaction."""
    logger.info("Creating transaction", customer_id=str(request.customer_id))
    transaction = await use_case.execute(request)
    return success_response(data=transaction, message="Transaction created successfully")


@router.get(
    "/{transaction_id}",
    response_model=APIResponse[TransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get transaction by ID",
)
async def get_transaction(
    transaction_id: UUID,
    current_user: Annotated[User, Depends(require_analyst)],
    use_case: GetTransactionUseCase = Depends(get_get_transaction_use_case),
) -> APIResponse[TransactionResponse]:
    """Retrieve a transaction by identifier."""
    transaction = await use_case.execute(transaction_id)
    return success_response(data=transaction, message="Transaction retrieved successfully")


@router.get(
    "",
    response_model=APIResponse[list[TransactionResponse]],
    status_code=status.HTTP_200_OK,
    summary="Search transactions",
)
async def search_transactions(
    current_user: Annotated[User, Depends(require_analyst)],
    customer_id: UUID | None = Query(default=None),
    merchant_id: UUID | None = Query(default=None),
    min_amount: float | None = Query(default=None),
    max_amount: float | None = Query(default=None),
    currency: str | None = Query(default=None),
    transaction_type: str | None = Query(default=None),
    payment_channel: str | None = Query(default=None),
    is_fraud: bool | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=1000),
    use_case: SearchTransactionsUseCase = Depends(get_search_transactions_use_case),
) -> APIResponse[list[TransactionResponse]]:
    """Search transactions with optional filters."""
    request = SearchTransactionRequest(
        customer_id=customer_id,
        merchant_id=merchant_id,
        min_amount=None if min_amount is None else Decimal(str(min_amount)),
        max_amount=None if max_amount is None else Decimal(str(max_amount)),
        currency=currency,
        transaction_type=transaction_type,
        payment_channel=payment_channel,
        is_fraud=is_fraud,
        start_date=None
        if start_date is None
        else datetime.fromisoformat(start_date.replace("Z", "+00:00")),
        end_date=None
        if end_date is None
        else datetime.fromisoformat(end_date.replace("Z", "+00:00")),
    )
    page_request = PageRequest(page=page, page_size=page_size)
    result = await use_case.execute(request, page_request)
    return success_response(data=result.items, message="Transactions retrieved successfully")


@router.put(
    "/{transaction_id}",
    response_model=APIResponse[TransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="Update transaction",
)
async def update_transaction(
    transaction_id: UUID,
    request: UpdateTransactionRequest,
    current_user: Annotated[User, Depends(require_analyst)],
    use_case: UpdateTransactionUseCase = Depends(get_update_transaction_use_case),
) -> APIResponse[TransactionResponse]:
    """Update a transaction."""
    transaction = await use_case.execute(transaction_id, request)
    return success_response(data=transaction, message="Transaction updated successfully")
