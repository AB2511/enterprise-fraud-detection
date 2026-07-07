"""Merchant Service - Business workflows for merchant management."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.application.interfaces.audit_repository import AuditRepository
from src.application.interfaces.merchant_repository import MerchantRepository
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.merchant import Merchant


class MerchantService:
    """Service for merchant management business workflows.

    This service handles merchant onboarding, risk calculation,
    and lifecycle management.
    """

    def __init__(
        self,
        merchant_repository: MerchantRepository,
        audit_repository: AuditRepository,
    ) -> None:
        """Initialize merchant service.

        Args:
            merchant_repository: Repository for merchant persistence
            audit_repository: Repository for audit logging
        """
        self._merchant_repo = merchant_repository
        self._audit_repo = audit_repository

    async def onboard_merchant(
        self,
        merchant_name: str,
        mcc: str,
        merchant_category: str,
        country: str,
        user_id: UUID | None = None,
    ) -> Merchant:
        """Onboard a new merchant with validation.

        Args:
            merchant_name: Business name
            mcc: Merchant Category Code (4-digit)
            merchant_category: Human-readable category
            country: Country code
            user_id: User performing onboarding

        Returns:
            Created merchant entity

        Raises:
            ValueError: If validation fails
        """
        # Create merchant entity
        merchant = Merchant(
            merchant_name=merchant_name,
            mcc=mcc,
            merchant_category=merchant_category,
            country=country,
        )

        # Calculate initial risk
        merchant.risk_rating = merchant.calculate_risk()

        # Persist merchant
        created_merchant = await self._merchant_repo.create(merchant)

        # Create audit log
        audit = AuditLog.for_creation(
            entity_type="merchant",
            entity_id=created_merchant.merchant_id,
            user_id=user_id,
            username="system",
            new_value={
                "name": merchant_name,
                "mcc": mcc,
                "category": merchant_category,
                "country": country,
                "risk_rating": merchant.risk_rating,
            },
        )
        await self._audit_repo.create(audit)

        return created_merchant

    async def calculate_merchant_risk(
        self,
        merchant_id: UUID,
    ) -> dict:
        """Calculate comprehensive merchant risk profile.

        Args:
            merchant_id: Merchant UUID

        Returns:
            Risk profile dictionary

        Raises:
            NotFoundError: If merchant doesn't exist
        """
        merchant = await self._merchant_repo.get_by_id(merchant_id)
        if not merchant:
            raise ValueError(f"Merchant {merchant_id} not found")

        # Calculate current risk
        calculated_risk = merchant.calculate_risk()

        return {
            "merchant_id": str(merchant.merchant_id),
            "merchant_name": merchant.merchant_name,
            "mcc": merchant.mcc,
            "category": merchant.merchant_category,
            "risk_rating": merchant.risk_rating,
            "calculated_risk": calculated_risk,
            "risk_level": merchant.get_risk_level(),
            "is_high_risk": merchant.is_high_risk,
            "is_new_merchant": merchant.is_new_merchant,
            "historical_fraud_rate": float(merchant.historical_fraud_rate),
            "total_transactions": merchant.total_transactions,
            "total_volume": float(merchant.total_volume),
            "average_transaction_amount": float(merchant.average_transaction_amount),
        }

    async def update_merchant_profile(
        self,
        merchant_id: UUID,
        updates: dict,
        user_id: UUID | None = None,
    ) -> Merchant:
        """Update merchant profile information.

        Args:
            merchant_id: Merchant UUID
            updates: Dictionary of fields to update
            user_id: User performing the action

        Returns:
            Updated merchant

        Raises:
            NotFoundError: If merchant doesn't exist
        """
        merchant = await self._merchant_repo.get_by_id(merchant_id)
        if not merchant:
            raise ValueError(f"Merchant {merchant_id} not found")

        # Store old values
        old_values = {
            "name": merchant.merchant_name,
            "mcc": merchant.mcc,
            "category": merchant.merchant_category,
            "risk_rating": merchant.risk_rating,
        }

        # Apply updates
        if "merchant_name" in updates:
            merchant.merchant_name = updates["merchant_name"]
        if "risk_rating" in updates:
            merchant.update_risk_score(updates["risk_rating"])
        if "merchant_category" in updates:
            merchant.merchant_category = updates["merchant_category"]

        # Update timestamp
        merchant.updated_at = datetime.utcnow()

        # Persist
        updated_merchant = await self._merchant_repo.update(merchant)

        # Audit
        new_values = {
            "name": merchant.merchant_name,
            "mcc": merchant.mcc,
            "category": merchant.merchant_category,
            "risk_rating": merchant.risk_rating,
        }

        audit = AuditLog.for_update(
            entity_type="merchant",
            entity_id=merchant_id,
            user_id=user_id,
            username="system",
            old_value=old_values,
            new_value=new_values,
        )
        await self._audit_repo.create(audit)

        return updated_merchant

    async def lookup_merchant(
        self,
        merchant_id: UUID | None = None,
        merchant_name: str | None = None,
    ) -> Merchant | None:
        """Lookup merchant by ID or name.

        Args:
            merchant_id: Merchant UUID
            merchant_name: Merchant name

        Returns:
            Merchant if found, None otherwise

        Raises:
            ValueError: If neither ID nor name provided
        """
        if merchant_id:
            return await self._merchant_repo.get_by_id(merchant_id)
        elif merchant_name:
            return await self._merchant_repo.get_by_name(merchant_name)
        else:
            raise ValueError("Either merchant_id or merchant_name must be provided")

    async def record_merchant_transaction(
        self,
        merchant_id: UUID,
        amount: Decimal,
        is_fraud: bool = False,
        user_id: UUID | None = None,
    ) -> Merchant:
        """Record a transaction for merchant and update statistics.

        Args:
            merchant_id: Merchant UUID
            amount: Transaction amount
            is_fraud: Whether transaction was fraud
            user_id: User recording the transaction

        Returns:
            Updated merchant

        Raises:
            NotFoundError: If merchant doesn't exist
        """
        merchant = await self._merchant_repo.get_by_id(merchant_id)
        if not merchant:
            raise ValueError(f"Merchant {merchant_id} not found")

        # Store old values
        old_fraud_rate = merchant.historical_fraud_rate
        old_transactions = merchant.total_transactions

        # Record transaction
        merchant.record_transaction(amount, is_fraud)

        # Persist
        updated_merchant = await self._merchant_repo.update(merchant)

        # Audit if fraud
        if is_fraud:
            audit = AuditLog.for_update(
                entity_type="merchant",
                entity_id=merchant_id,
                user_id=user_id,
                username="system",
                old_value={
                    "fraud_rate": float(old_fraud_rate),
                    "total_transactions": old_transactions,
                },
                new_value={
                    "fraud_rate": float(merchant.historical_fraud_rate),
                    "total_transactions": merchant.total_transactions,
                },
            )
            await self._audit_repo.create(audit)

        return updated_merchant

    async def suspend_merchant(
        self,
        merchant_id: UUID,
        reason: str,
        user_id: UUID | None = None,
    ) -> Merchant:
        """Suspend merchant due to high fraud activity.

        Args:
            merchant_id: Merchant UUID
            reason: Reason for suspension
            user_id: User performing suspension

        Returns:
            Suspended merchant

        Raises:
            NotFoundError: If merchant doesn't exist
        """
        merchant = await self._merchant_repo.get_by_id(merchant_id)
        if not merchant:
            raise ValueError(f"Merchant {merchant_id} not found")

        # Suspend
        merchant.suspend()

        # Persist
        updated_merchant = await self._merchant_repo.update(merchant)

        # Audit
        audit = AuditLog.for_update(
            entity_type="merchant",
            entity_id=merchant_id,
            user_id=user_id,
            username="system",
            old_value={"is_active": True},
            new_value={"is_active": False, "reason": reason},
        )
        await self._audit_repo.create(audit)

        return updated_merchant

    async def reactivate_merchant(
        self,
        merchant_id: UUID,
        user_id: UUID | None = None,
    ) -> Merchant:
        """Reactivate suspended merchant.

        Args:
            merchant_id: Merchant UUID
            user_id: User performing reactivation

        Returns:
            Reactivated merchant

        Raises:
            NotFoundError: If merchant doesn't exist
            ValueError: If fraud rate too high
        """
        merchant = await self._merchant_repo.get_by_id(merchant_id)
        if not merchant:
            raise ValueError(f"Merchant {merchant_id} not found")

        # Reactivate (will raise if fraud rate > 10%)
        merchant.reactivate()

        # Persist
        updated_merchant = await self._merchant_repo.update(merchant)

        # Audit
        audit = AuditLog.for_update(
            entity_type="merchant",
            entity_id=merchant_id,
            user_id=user_id,
            username="system",
            old_value={"is_active": False},
            new_value={"is_active": True},
        )
        await self._audit_repo.create(audit)

        return updated_merchant

    async def get_high_risk_merchants(
        self,
        limit: int = 100,
    ) -> list[dict]:
        """Get list of high-risk merchants.

        Args:
            limit: Maximum number of results

        Returns:
            List of merchant risk profiles
        """
        merchants = await self._merchant_repo.list_high_risk(limit=limit)

        return [await self.calculate_merchant_risk(m.merchant_id) for m in merchants]
