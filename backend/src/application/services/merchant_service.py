"""Merchant Service - Business workflows for merchant management."""

from datetime import datetime
from decimal import Decimal
from typing import Any
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
    ) -> dict[str, Any]:
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
        updates: dict[str, Any],
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
        reason: str | None = None,
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
            new_value={"is_active": True, "reason": reason},
        )
        await self._audit_repo.create(audit)

        return updated_merchant

    async def get_high_risk_merchants(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get list of high-risk merchants.

        Args:
            limit: Maximum number of results

        Returns:
            List of merchant risk profiles
        """
        merchants = await self._merchant_repo.list_high_risk(limit=limit)

        return [await self.calculate_merchant_risk(m.merchant_id) for m in merchants]

    async def get_merchant_by_id(
        self,
        merchant_id: UUID,
    ) -> Merchant | None:
        """Get merchant by ID.

        Args:
            merchant_id: Merchant UUID

        Returns:
            Merchant if found, None otherwise
        """
        return await self._merchant_repo.get_by_id(merchant_id)

    async def search_merchants(
        self,
        criteria: dict[str, Any],
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Merchant], int]:
        """Search merchants with multiple criteria.

        Args:
            criteria: Search criteria (mcc, country, min_risk_rating, max_risk_rating, etc.)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (list of merchants, total count)
        """
        merchants = []

        # Filter by MCC
        if "mcc" in criteria:
            merchants = await self._merchant_repo.list_by_mcc(
                mcc=criteria["mcc"],
                limit=limit,
                offset=offset,
            )
        # Filter by country
        elif "country" in criteria:
            merchants = await self._merchant_repo.get_by_country(
                country=criteria["country"],
                limit=limit,
                offset=offset,
            )
        # Filter by risk range
        elif "min_risk_rating" in criteria or "max_risk_rating" in criteria:
            min_risk = criteria.get("min_risk_rating", 0)
            max_risk = criteria.get("max_risk_rating", 100)
            merchants = await self._merchant_repo.list_by_risk_level(
                min_risk=min_risk,
                max_risk=max_risk,
                limit=limit,
            )
        else:
            # No specific criteria - return high risk merchants as default
            merchants = await self._merchant_repo.list_high_risk(limit=limit)

        # TODO: Implement actual count - for now return len(merchants)
        total = len(merchants)

        return merchants, total

    async def search_merchants_by_name(
        self,
        search_term: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Merchant], int]:
        """Search merchants by name.

        Args:
            search_term: Name search term
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (list of merchants, total count)

        Note:
            This is a simplified implementation. Full text search would require
            repository support for pattern matching.
        """
        # Use exact match for now (repository supports get_by_name)
        merchant = await self._merchant_repo.get_by_name(search_term)

        if merchant:
            return [merchant], 1
        else:
            return [], 0

    async def get_merchant_statistics(self) -> dict[str, Any]:
        """Get merchant statistics.

        Returns:
            Dictionary with merchant statistics
        """
        # Get all merchants (high risk as proxy for active merchants)
        # Note: This is a simplified implementation
        # Full implementation would require repository count methods

        high_risk_merchants = await self._merchant_repo.list_high_risk(limit=1000)

        total_merchants = len(high_risk_merchants)
        active_merchants = sum(1 for m in high_risk_merchants if m.is_active)
        suspended_merchants = total_merchants - active_merchants

        # Calculate statistics
        by_category: dict[str, int] = {}
        by_risk_level = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        total_risk = 0
        total_fraud_rate = 0.0

        for merchant in high_risk_merchants:
            # Count by category
            category = merchant.merchant_category
            by_category[category] = by_category.get(category, 0) + 1

            # Count by risk level
            risk_level = merchant.get_risk_level()
            by_risk_level[risk_level] += 1

            # Sum for averages
            total_risk += merchant.risk_rating
            total_fraud_rate += float(merchant.historical_fraud_rate)

        avg_risk_rating = total_risk / total_merchants if total_merchants > 0 else 0.0
        avg_fraud_rate = total_fraud_rate / total_merchants if total_merchants > 0 else 0.0

        high_risk_count = sum(1 for m in high_risk_merchants if m.is_high_risk)

        # New merchants this month (approximation - checking if created recently)
        from datetime import datetime, timedelta

        one_month_ago = datetime.utcnow() - timedelta(days=30)
        new_merchants_count = sum(1 for m in high_risk_merchants if m.created_at >= one_month_ago)

        return {
            "total_merchants": total_merchants,
            "active_merchants": active_merchants,
            "suspended_merchants": suspended_merchants,
            "merchants_by_category": by_category,
            "merchants_by_risk_level": by_risk_level,
            "avg_risk_rating": avg_risk_rating,
            "avg_fraud_rate": avg_fraud_rate,
            "high_risk_merchants": high_risk_count,
            "new_merchants_this_month": new_merchants_count,
        }

    async def deactivate_merchant(
        self,
        merchant_id: UUID,
        reason: str,
        user_id: UUID | None = None,
    ) -> None:
        """Deactivate merchant (soft delete).

        Args:
            merchant_id: Merchant UUID
            reason: Reason for deactivation
            user_id: User performing deactivation

        Raises:
            ValueError: If merchant not found
        """
        # Verify merchant exists
        merchant = await self._merchant_repo.get_by_id(merchant_id)
        if not merchant:
            raise ValueError(f"Merchant {merchant_id} not found")

        # Capture old state for audit
        old_state = {
            "merchant_id": str(merchant.merchant_id),
            "merchant_name": merchant.merchant_name,
            "is_active": merchant.is_active,
        }

        # Soft delete via repository
        deleted = await self._merchant_repo.delete(merchant_id)

        if not deleted:
            raise ValueError(f"Merchant {merchant_id} not found")

        # Audit the deletion
        audit = AuditLog.for_deletion(
            entity_type="merchant",
            entity_id=merchant_id,
            old_value=old_state,
            user_id=user_id,
            username="system",
            description=reason,
        )
        await self._audit_repo.create(audit)
