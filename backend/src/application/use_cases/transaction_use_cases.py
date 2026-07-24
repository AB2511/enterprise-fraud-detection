"""Transaction Use Cases (CQRS Pattern)."""

from uuid import UUID

from src.application.dtos.common import PageRequest, PageResponse
from src.application.dtos.transaction_dtos import (
    CreateTransactionRequest,
    SearchTransactionRequest,
    TransactionResponse,
    UpdateTransactionRequest,
)
from src.application.services.transaction_service import (
    TransactionSearchCriteria,
    TransactionService,
)
from src.domain.entities.transaction import Transaction


class CreateTransactionUseCase:
    """Use case for creating a new transaction."""

    def __init__(self, transaction_service: TransactionService) -> None:
        """Initialize use case."""
        self._service = transaction_service

    async def execute(
        self,
        request: CreateTransactionRequest,
        user_id: UUID | None = None,
    ) -> TransactionResponse:
        """Execute create transaction use case."""
        transaction = await self._service.create_transaction(
            customer_id=request.customer_id,
            merchant_id=request.merchant_id,
            amount=request.amount,
            currency=request.currency,
            transaction_type=request.transaction_type,
            payment_channel=request.payment_channel,
            payment_method=request.payment_method,
            device_id=request.device_id,
            ip_address=request.ip_address,
            latitude=request.latitude,
            longitude=request.longitude,
            user_id=user_id,
        )

        return self._to_response(transaction)

    @staticmethod
    def _to_response(transaction: Transaction | None) -> TransactionResponse:
        """Convert domain entity to response DTO."""
        if transaction is None:
            raise ValueError("Transaction not found")

        return TransactionResponse(
            transaction_id=transaction.transaction_id,
            customer_id=transaction.customer_id,
            merchant_id=transaction.merchant_id,
            amount=float(transaction.amount),
            currency=transaction.currency,
            transaction_type=transaction.transaction_type,
            status=transaction.status,
            payment_channel=transaction.payment_channel,
            payment_method=transaction.payment_method,
            device_id=transaction.device_id,
            ip_address=transaction.ip_address,
            latitude=transaction.latitude,
            longitude=transaction.longitude,
            velocity_1h=transaction.velocity_1h,
            velocity_24h=transaction.velocity_24h,
            velocity_7d=transaction.velocity_7d,
            is_fraud=transaction.is_fraud,
            timestamp=transaction.timestamp,
            created_at=transaction.created_at,
        )


class UpdateTransactionUseCase:
    """Use case for updating a transaction."""

    def __init__(self, transaction_service: TransactionService) -> None:
        """Initialize use case."""
        self._service = transaction_service

    async def execute(
        self,
        transaction_id: UUID,
        request: UpdateTransactionRequest,
        user_id: UUID | None = None,
    ) -> TransactionResponse:
        """Execute update transaction use case."""
        updates: dict[str, object] = {}
        if request.status is not None:
            updates["status"] = request.status
        if request.is_fraud is not None:
            updates["is_fraud"] = request.is_fraud

        transaction = await self._service.update_transaction(
            transaction_id=transaction_id,
            updates=updates,
            user_id=user_id,
        )

        return CreateTransactionUseCase._to_response(transaction)


class GetTransactionUseCase:
    """Use case for retrieving a transaction."""

    def __init__(self, transaction_service: TransactionService) -> None:
        """Initialize use case."""
        self._service = transaction_service

    async def execute(self, transaction_id: UUID) -> TransactionResponse:
        """Execute get transaction use case."""
        transaction = await self._service.get_transaction_by_id(transaction_id)
        return CreateTransactionUseCase._to_response(transaction)


class SearchTransactionsUseCase:
    """Use case for searching transactions."""

    def __init__(self, transaction_service: TransactionService) -> None:
        """Initialize use case."""
        self._service = transaction_service

    async def execute(
        self,
        request: SearchTransactionRequest,
        page_request: PageRequest,
    ) -> PageResponse:
        """Execute search transactions use case."""
        # Build search criteria
        criteria: TransactionSearchCriteria = {}
        if request.customer_id is not None:
            criteria["customer_id"] = request.customer_id
        if request.merchant_id is not None:
            criteria["merchant_id"] = request.merchant_id
        if request.min_amount is not None:
            criteria["min_amount"] = request.min_amount
        if request.max_amount is not None:
            criteria["max_amount"] = request.max_amount
        if request.currency is not None:
            criteria["currency"] = request.currency
        if request.transaction_type is not None:
            criteria["transaction_type"] = request.transaction_type
        if request.payment_channel is not None:
            criteria["payment_channel"] = request.payment_channel
        if request.is_fraud is not None:
            criteria["is_fraud"] = request.is_fraud
        if request.start_date is not None:
            criteria["start_date"] = request.start_date
        if request.end_date is not None:
            criteria["end_date"] = request.end_date

        transactions, total = await self._service.search_transactions(
            criteria=criteria,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        transaction_responses = [CreateTransactionUseCase._to_response(t) for t in transactions]

        return PageResponse.create(
            items=transaction_responses,
            total=total,
            page_request=page_request,
        )


class GetCustomerTransactionsUseCase:
    """Use case for retrieving customer transactions."""

    def __init__(self, transaction_service: TransactionService) -> None:
        """Initialize use case."""
        self._service = transaction_service

    async def execute(
        self,
        customer_id: UUID,
        page_request: PageRequest,
    ) -> PageResponse:
        """Execute get customer transactions use case."""
        transactions, total = await self._service.get_customer_transactions(
            customer_id=customer_id,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        transaction_responses = [CreateTransactionUseCase._to_response(t) for t in transactions]

        return PageResponse.create(
            items=transaction_responses,
            total=total,
            page_request=page_request,
        )
