"""Merchant Use Cases (CQRS Pattern)."""

from typing import Any
from uuid import UUID

from src.application.dtos.common import PageRequest, PageResponse
from src.application.dtos.merchant_dtos import (
    CreateMerchantRequest,
    MerchantListRequest,
    MerchantResponse,
    MerchantStatisticsResponse,
    SuspendMerchantRequest,
    UpdateMerchantRequest,
)
from src.application.services.merchant_service import MerchantService
from src.domain.entities.merchant import Merchant


class CreateMerchantUseCase:
    """Use case for creating a new merchant."""

    def __init__(self, merchant_service: MerchantService) -> None:
        """Initialize use case.

        Args:
            merchant_service: Merchant service instance
        """
        self._service = merchant_service

    async def execute(
        self,
        request: CreateMerchantRequest,
        user_id: UUID | None = None,
    ) -> MerchantResponse:
        """Execute create merchant use case.

        Args:
            request: Create merchant request DTO
            user_id: User performing the action

        Returns:
            Merchant response DTO

        Raises:
            ValidationException: If validation fails
            ConflictException: If merchant already exists
        """
        # Call onboard_merchant (not create_merchant)
        # merchant_category in DTO maps to MCC (Merchant Category Code)
        merchant = await self._service.onboard_merchant(
            merchant_name=request.merchant_name,
            mcc=request.merchant_category,  # DTO field is merchant_category (MCC code)
            merchant_category=request.merchant_category,  # Also pass as category
            country=request.country,
            user_id=user_id,
        )

        return self._to_response(merchant)

    @staticmethod
    def _to_response(merchant: Merchant | None) -> MerchantResponse:
        """Convert domain entity to response DTO."""
        if merchant is None:
            raise ValueError("Merchant not found")

        return MerchantResponse(
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.merchant_name,
            merchant_category=merchant.merchant_category,
            country=merchant.country,
            contact_email=getattr(merchant, "contact_email", None),
            business_registration=getattr(merchant, "business_registration", None),
            risk_rating=getattr(merchant, "risk_rating", 0),
            fraud_rate=float(getattr(merchant, "historical_fraud_rate", 0.0)),
            transaction_count=getattr(merchant, "total_transactions", 0),
            total_volume=float(getattr(merchant, "total_volume", 0.0)),
            avg_transaction_amount=float(getattr(merchant, "average_transaction_amount", 0.0)),
            is_suspended=not getattr(merchant, "is_active", True),
            suspension_reason=getattr(merchant, "suspension_reason", None),
            last_transaction_date=getattr(merchant, "last_transaction_date", None),
            created_at=getattr(merchant, "created_at", None),
            updated_at=getattr(merchant, "updated_at", None),
        )


class UpdateMerchantUseCase:
    """Use case for updating a merchant."""

    def __init__(self, merchant_service: MerchantService) -> None:
        """Initialize use case.

        Args:
            merchant_service: Merchant service instance
        """
        self._service = merchant_service

    async def execute(
        self,
        merchant_id: UUID,
        request: UpdateMerchantRequest,
        user_id: UUID | None = None,
    ) -> MerchantResponse:
        """Execute update merchant use case.

        Args:
            merchant_id: Merchant UUID
            request: Update merchant request DTO
            user_id: User performing the action

        Returns:
            Merchant response DTO

        Raises:
            EntityNotFoundException: If merchant not found
            ValidationException: If validation fails
        """
        # Build updates dictionary
        updates: dict[str, Any] = {}
        if request.merchant_name is not None:
            updates["merchant_name"] = request.merchant_name
        if request.contact_email is not None:
            updates["contact_email"] = request.contact_email
        if request.risk_rating is not None:
            updates["risk_rating"] = request.risk_rating
        if request.is_suspended is not None:
            updates["is_suspended"] = request.is_suspended

        # Call update_merchant_profile (not update_merchant)
        merchant = await self._service.update_merchant_profile(
            merchant_id=merchant_id,
            updates=updates,
            user_id=user_id,
        )

        return CreateMerchantUseCase._to_response(merchant)


class DeleteMerchantUseCase:
    """Use case for deleting (soft delete) a merchant."""

    def __init__(self, merchant_service: MerchantService) -> None:
        """Initialize use case.

        Args:
            merchant_service: Merchant service instance
        """
        self._service = merchant_service

    async def execute(
        self,
        merchant_id: UUID,
        reason: str = "Business closure",
        user_id: UUID | None = None,
    ) -> None:
        """Execute delete merchant use case.

        Args:
            merchant_id: Merchant UUID
            reason: Reason for deletion
            user_id: User performing the action

        Raises:
            EntityNotFoundException: If merchant not found
        """
        await self._service.deactivate_merchant(
            merchant_id=merchant_id,
            reason=reason,
            user_id=user_id,
        )


class GetMerchantUseCase:
    """Use case for retrieving a merchant."""

    def __init__(self, merchant_service: MerchantService) -> None:
        """Initialize use case.

        Args:
            merchant_service: Merchant service instance
        """
        self._service = merchant_service

    async def execute(self, merchant_id: UUID) -> MerchantResponse:
        """Execute get merchant use case.

        Args:
            merchant_id: Merchant UUID

        Returns:
            Merchant response DTO

        Raises:
            EntityNotFoundException: If merchant not found
        """
        merchant = await self._service.get_merchant_by_id(merchant_id)
        return CreateMerchantUseCase._to_response(merchant)


class ListMerchantsUseCase:
    """Use case for listing merchants."""

    def __init__(self, merchant_service: MerchantService) -> None:
        """Initialize use case.

        Args:
            merchant_service: Merchant service instance
        """
        self._service = merchant_service

    async def execute(
        self,
        request: MerchantListRequest,
        page_request: PageRequest,
    ) -> PageResponse:
        """Execute list merchants use case.

        Args:
            request: Merchant list request with filters
            page_request: Pagination parameters

        Returns:
            Paginated merchant responses
        """
        # Build search criteria
        criteria: dict[str, Any] = {}
        if request.merchant_category:
            criteria["merchant_category"] = request.merchant_category
        if request.country:
            criteria["country"] = request.country
        if request.min_risk_rating is not None:
            criteria["min_risk_rating"] = request.min_risk_rating
        if request.max_risk_rating is not None:
            criteria["max_risk_rating"] = request.max_risk_rating
        if request.is_suspended is not None:
            criteria["is_suspended"] = request.is_suspended
        if request.min_fraud_rate is not None:
            criteria["min_fraud_rate"] = request.min_fraud_rate

        merchants, total = await self._service.search_merchants(
            criteria=criteria,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        merchant_responses = [CreateMerchantUseCase._to_response(m) for m in merchants]

        return PageResponse.create(
            items=merchant_responses,
            total=total,
            page_request=page_request,
        )


class SuspendMerchantUseCase:
    """Use case for suspending a merchant."""

    def __init__(self, merchant_service: MerchantService) -> None:
        """Initialize use case.

        Args:
            merchant_service: Merchant service instance
        """
        self._service = merchant_service

    async def execute(
        self,
        merchant_id: UUID,
        request: SuspendMerchantRequest,
        user_id: UUID | None = None,
    ) -> MerchantResponse:
        """Execute suspend merchant use case.

        Args:
            merchant_id: Merchant UUID
            request: Suspension request with reason and type
            user_id: User performing the action

        Returns:
            Merchant response DTO

        Raises:
            EntityNotFoundException: If merchant not found
        """
        merchant = await self._service.suspend_merchant(
            merchant_id=merchant_id,
            reason=request.reason,
            user_id=user_id,
        )

        return CreateMerchantUseCase._to_response(merchant)


class ReactivateMerchantUseCase:
    """Use case for reactivating a suspended merchant."""

    def __init__(self, merchant_service: MerchantService) -> None:
        """Initialize use case.

        Args:
            merchant_service: Merchant service instance
        """
        self._service = merchant_service

    async def execute(
        self,
        merchant_id: UUID,
        reason: str = "Suspension review completed",
        user_id: UUID | None = None,
    ) -> MerchantResponse:
        """Execute reactivate merchant use case.

        Args:
            merchant_id: Merchant UUID
            reason: Reason for reactivation
            user_id: User performing the action

        Returns:
            Merchant response DTO

        Raises:
            EntityNotFoundException: If merchant not found
        """
        merchant = await self._service.reactivate_merchant(
            merchant_id=merchant_id,
            reason=reason,
            user_id=user_id,
        )

        return CreateMerchantUseCase._to_response(merchant)


class GetMerchantStatisticsUseCase:
    """Use case for getting merchant statistics."""

    def __init__(self, merchant_service: MerchantService) -> None:
        """Initialize use case.

        Args:
            merchant_service: Merchant service instance
        """
        self._service = merchant_service

    async def execute(self) -> MerchantStatisticsResponse:
        """Execute get merchant statistics use case.

        Returns:
            Merchant statistics response DTO
        """
        stats = await self._service.get_merchant_statistics()

        return MerchantStatisticsResponse(
            total_merchants=stats["total_merchants"],
            active_merchants=stats["active_merchants"],
            suspended_merchants=stats["suspended_merchants"],
            merchants_by_category=stats["merchants_by_category"],
            merchants_by_risk_level=stats["merchants_by_risk_level"],
            avg_risk_rating=stats["avg_risk_rating"],
            avg_fraud_rate=stats["avg_fraud_rate"],
            high_risk_merchants=stats["high_risk_merchants"],
            new_merchants_this_month=stats["new_merchants_this_month"],
        )


class GetHighRiskMerchantsUseCase:
    """Use case for getting high-risk merchants."""

    def __init__(self, merchant_service: MerchantService) -> None:
        """Initialize use case.

        Args:
            merchant_service: Merchant service instance
        """
        self._service = merchant_service

    async def execute(
        self,
        min_risk_rating: int = 70,
        page_request: PageRequest | None = None,
    ) -> PageResponse:
        """Execute get high-risk merchants use case.

        Args:
            min_risk_rating: Minimum risk rating threshold
            page_request: Pagination parameters

        Returns:
            Paginated high-risk merchant responses
        """
        if page_request is None:
            page_request = PageRequest(page=1, page_size=100)

        merchants = await self._service.get_high_risk_merchants(limit=page_request.limit)
        total = len(merchants)

        merchant_responses = [self._to_response_from_profile(m) for m in merchants]

        return PageResponse.create(
            items=merchant_responses,
            total=total,
            page_request=page_request,
        )

    @staticmethod
    def _to_response_from_profile(profile: dict[str, Any]) -> MerchantResponse:
        """Convert a high-risk merchant profile dictionary to a response DTO."""
        merchant_id = profile.get("merchant_id")
        if isinstance(merchant_id, str):
            merchant_id_value = UUID(merchant_id)
        else:
            merchant_id_value = UUID(int=0)

        return MerchantResponse(
            merchant_id=merchant_id_value,
            merchant_name=str(profile.get("merchant_name", "")),
            merchant_category=str(profile.get("category", "")),
            country=str(profile.get("country", "")),
            contact_email=None,
            business_registration=None,
            risk_rating=int(profile.get("risk_rating", 0)),
            fraud_rate=float(profile.get("historical_fraud_rate", 0.0)),
            transaction_count=int(profile.get("total_transactions", 0)),
            total_volume=float(profile.get("total_volume", 0.0)),
            avg_transaction_amount=float(profile.get("average_transaction_amount", 0.0)),
            is_suspended=False,
            suspension_reason=None,
            last_transaction_date=None,
            created_at=None,
            updated_at=None,
        )


class SearchMerchantsByNameUseCase:
    """Use case for searching merchants by name."""

    def __init__(self, merchant_service: MerchantService) -> None:
        """Initialize use case.

        Args:
            merchant_service: Merchant service instance
        """
        self._service = merchant_service

    async def execute(
        self,
        search_term: str,
        page_request: PageRequest | None = None,
    ) -> PageResponse:
        """Execute search merchants by name use case.

        Args:
            search_term: Name search term
            page_request: Pagination parameters

        Returns:
            Paginated merchant search results
        """
        if page_request is None:
            page_request = PageRequest(page=1, page_size=50)

        merchants, total = await self._service.search_merchants_by_name(
            search_term=search_term,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        merchant_responses = [CreateMerchantUseCase._to_response(m) for m in merchants]

        return PageResponse.create(
            items=merchant_responses,
            total=total,
            page_request=page_request,
        )
