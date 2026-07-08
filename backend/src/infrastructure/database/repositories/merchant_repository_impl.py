"""Merchant Repository Implementation using SQLAlchemy Async."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.merchant_repository import MerchantRepository
from src.domain.entities.merchant import Merchant
from src.domain.exceptions.base import DomainException, NotFoundError, RepositoryError
from src.infrastructure.database.models import MerchantModel


class MerchantNotFoundError(DomainException):
    """Raised when merchant is not found."""

    def __init__(self, merchant_id: UUID) -> None:
        super().__init__(f"Merchant with ID {merchant_id} not found", "MERCHANT_NOT_FOUND")


class MerchantNameExistsError(DomainException):
    """Raised when merchant name already exists."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Merchant with name '{name}' already exists", "MERCHANT_NAME_EXISTS")


class MerchantRepositoryImpl(MerchantRepository):
    """SQLAlchemy implementation of MerchantRepository.

    Provides async database operations for Merchant entities with
    comprehensive filtering, sorting, and bulk operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, merchant: Merchant) -> Merchant:
        """Create a new merchant.

        Args:
            merchant: Merchant entity to create

        Returns:
            Created merchant with generated ID

        Raises:
            MerchantNameExistsError: If merchant name already exists
            RepositoryError: If creation fails
        """
        try:
            # Check if merchant name already exists
            existing = await self._session.execute(
                select(MerchantModel).where(
                    and_(
                        MerchantModel.merchant_name == merchant.merchant_name,
                        MerchantModel.deleted_at.is_(None),
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise MerchantNameExistsError(merchant.merchant_name)

            # Convert domain entity to database model
            merchant_model = MerchantModel(
                id=merchant.merchant_id,
                merchant_name=merchant.merchant_name,
                mcc=merchant.mcc,
                merchant_category=merchant.merchant_category,
                country=merchant.country,
                risk_rating=merchant.risk_rating,
                historical_fraud_rate=float(merchant.historical_fraud_rate),
                total_transactions=merchant.total_transactions,
                total_volume=float(merchant.total_volume),
                is_active=merchant.is_active,
                created_at=merchant.created_at,
                updated_at=merchant.updated_at,
            )

            self._session.add(merchant_model)
            await self._session.flush()
            await self._session.refresh(merchant_model)

            return self._model_to_entity(merchant_model)

        except IntegrityError as e:
            await self._session.rollback()
            if "unique" in str(e).lower():
                raise MerchantNameExistsError(merchant.merchant_name) from e
            raise DomainException(
                f"Database constraint violation: {e}", "DB_CONSTRAINT_ERROR"
            ) from e

        except MerchantNameExistsError:
            # Re-raise MerchantNameExistsError as-is
            raise

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to create merchant: {e}", "REPOSITORY_ERROR") from e

    async def get_by_id(self, merchant_id: UUID) -> Merchant | None:
        """Retrieve merchant by ID.

        Args:
            merchant_id: Merchant UUID

        Returns:
            Merchant if found, None otherwise
        """
        try:
            result = await self._session.execute(
                select(MerchantModel).where(
                    and_(MerchantModel.id == merchant_id, MerchantModel.deleted_at.is_(None))
                )
            )
            merchant_model = result.scalar_one_or_none()

            if merchant_model:
                return self._model_to_entity(merchant_model)
            return None

        except Exception as e:
            raise DomainException(f"Failed to get merchant by ID: {e}", "REPOSITORY_ERROR") from e

    async def get_by_name(self, merchant_name: str) -> Merchant | None:
        """Retrieve merchant by name.

        Args:
            merchant_name: Merchant name

        Returns:
            Merchant if found, None otherwise
        """
        try:
            result = await self._session.execute(
                select(MerchantModel).where(
                    and_(
                        MerchantModel.merchant_name == merchant_name,
                        MerchantModel.deleted_at.is_(None),
                    )
                )
            )
            merchant_model = result.scalar_one_or_none()

            if merchant_model:
                return self._model_to_entity(merchant_model)
            return None

        except Exception as e:
            raise DomainException(f"Failed to get merchant by name: {e}", "REPOSITORY_ERROR") from e

    async def update(self, merchant: Merchant) -> Merchant:
        """Update existing merchant.

        Args:
            merchant: Merchant entity with updated data

        Returns:
            Updated merchant

        Raises:
            MerchantNotFoundError: If merchant doesn't exist
            RepositoryError: If update fails
        """
        try:
            # Check if merchant exists
            existing = await self._session.execute(
                select(MerchantModel).where(
                    and_(
                        MerchantModel.id == merchant.merchant_id, MerchantModel.deleted_at.is_(None)
                    )
                )
            )
            if not existing.scalar_one_or_none():
                raise MerchantNotFoundError(merchant.merchant_id)

            # Update fields
            await self._session.execute(
                update(MerchantModel)
                .where(MerchantModel.id == merchant.merchant_id)
                .values(
                    merchant_name=merchant.merchant_name,
                    mcc=merchant.mcc,
                    merchant_category=merchant.merchant_category,
                    country=merchant.country,
                    risk_rating=merchant.risk_rating,
                    historical_fraud_rate=float(merchant.historical_fraud_rate),
                    total_transactions=merchant.total_transactions,
                    total_volume=float(merchant.total_volume),
                    is_active=merchant.is_active,
                    updated_at=datetime.now(UTC),
                )
            )

            # Fetch updated record
            result = await self._session.execute(
                select(MerchantModel).where(MerchantModel.id == merchant.merchant_id)
            )
            updated_model = result.scalar_one()

            return self._model_to_entity(updated_model)

        except MerchantNotFoundError:
            raise
        except IntegrityError as e:
            await self._session.rollback()
            if "unique" in str(e).lower():
                raise MerchantNameExistsError(merchant.merchant_name) from e
            raise DomainException(
                f"Database constraint violation: {e}", "DB_CONSTRAINT_ERROR"
            ) from e
        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to update merchant: {e}", "REPOSITORY_ERROR") from e

    async def delete(self, merchant_id: UUID) -> bool:
        """Soft delete merchant.

        Args:
            merchant_id: Merchant UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self._session.execute(
                update(MerchantModel)
                .where(and_(MerchantModel.id == merchant_id, MerchantModel.deleted_at.is_(None)))
                .values(deleted_at=datetime.now(UTC))
            )

            return result.rowcount > 0

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to delete merchant: {e}", "REPOSITORY_ERROR") from e

    async def list_by_category(
        self,
        category: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Merchant]:
        """List merchants by category with pagination.

        Args:
            category: Merchant category to filter by
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of merchants
        """
        try:
            result = await self._session.execute(
                select(MerchantModel)
                .where(
                    and_(
                        MerchantModel.merchant_category == category,
                        MerchantModel.deleted_at.is_(None),
                    )
                )
                .order_by(desc(MerchantModel.total_volume))
                .limit(limit)
                .offset(offset)
            )

            merchants = result.scalars().all()
            return [self._model_to_entity(merchant) for merchant in merchants]

        except Exception as e:
            raise DomainException(
                f"Failed to list merchants by category: {e}", "REPOSITORY_ERROR"
            ) from e

    async def list_by_mcc(
        self,
        mcc: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Merchant]:
        """List merchants by MCC code with pagination.

        Args:
            mcc: Merchant Category Code
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of merchants
        """
        try:
            result = await self._session.execute(
                select(MerchantModel)
                .where(and_(MerchantModel.mcc == mcc, MerchantModel.deleted_at.is_(None)))
                .order_by(desc(MerchantModel.total_transactions))
                .limit(limit)
                .offset(offset)
            )

            merchants = result.scalars().all()
            return [self._model_to_entity(merchant) for merchant in merchants]

        except Exception as e:
            raise DomainException(
                f"Failed to list merchants by MCC: {e}", "REPOSITORY_ERROR"
            ) from e

    async def list_high_risk(self, min_risk_rating: int = 70, limit: int = 100) -> list[Merchant]:
        """List high-risk merchants.

        Args:
            min_risk_rating: Minimum risk rating threshold
            limit: Maximum number of results

        Returns:
            List of high-risk merchants
        """
        try:
            result = await self._session.execute(
                select(MerchantModel)
                .where(
                    and_(
                        MerchantModel.risk_rating >= min_risk_rating,
                        MerchantModel.deleted_at.is_(None),
                    )
                )
                .order_by(
                    desc(MerchantModel.risk_rating), desc(MerchantModel.historical_fraud_rate)
                )
                .limit(limit)
            )

            merchants = result.scalars().all()
            return [self._model_to_entity(merchant) for merchant in merchants]

        except Exception as e:
            raise DomainException(
                f"Failed to list high-risk merchants: {e}", "REPOSITORY_ERROR"
            ) from e

    async def count_by_risk_level(self, min_risk_rating: int) -> int:
        """Count merchants above risk threshold.

        Args:
            min_risk_rating: Minimum risk rating

        Returns:
            Number of merchants
        """
        try:
            result = await self._session.execute(
                select(func.count(MerchantModel.id)).where(
                    and_(
                        MerchantModel.risk_rating >= min_risk_rating,
                        MerchantModel.deleted_at.is_(None),
                        MerchantModel.is_active,
                    )
                )
            )

            return result.scalar() or 0

        except Exception as e:
            raise DomainException(
                f"Failed to count merchants by risk level: {e}", "REPOSITORY_ERROR"
            ) from e

    async def find_by_criteria(
        self,
        name_pattern: str | None = None,
        mcc: str | None = None,
        category: str | None = None,
        country: str | None = None,
        min_risk_rating: int | None = None,
        max_risk_rating: int | None = None,
        min_fraud_rate: float | None = None,
        max_fraud_rate: float | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "updated_at",
        sort_desc: bool = True,
    ) -> list[Merchant]:
        """Find merchants by multiple criteria with flexible sorting.

        Args:
            name_pattern: Merchant name pattern (LIKE search)
            mcc: Merchant Category Code
            category: Merchant category
            country: Country filter
            min_risk_rating: Minimum risk rating
            max_risk_rating: Maximum risk rating
            min_fraud_rate: Minimum fraud rate
            max_fraud_rate: Maximum fraud rate
            is_active: Active status filter
            limit: Maximum results
            offset: Results offset
            sort_by: Field to sort by
            sort_desc: Sort descending if True

        Returns:
            List of matching merchants
        """
        try:
            query = select(MerchantModel).where(MerchantModel.deleted_at.is_(None))

            # Add filters dynamically
            if name_pattern:
                query = query.where(MerchantModel.merchant_name.ilike(f"%{name_pattern}%"))
            if mcc:
                query = query.where(MerchantModel.mcc == mcc)
            if category:
                query = query.where(MerchantModel.merchant_category == category)
            if country:
                query = query.where(MerchantModel.country == country)
            if min_risk_rating is not None:
                query = query.where(MerchantModel.risk_rating >= min_risk_rating)
            if max_risk_rating is not None:
                query = query.where(MerchantModel.risk_rating <= max_risk_rating)
            if min_fraud_rate is not None:
                query = query.where(MerchantModel.historical_fraud_rate >= min_fraud_rate)
            if max_fraud_rate is not None:
                query = query.where(MerchantModel.historical_fraud_rate <= max_fraud_rate)
            if is_active is not None:
                query = query.where(MerchantModel.is_active == is_active)

            # Add sorting
            sort_column = getattr(MerchantModel, sort_by, MerchantModel.updated_at)
            if sort_desc:
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)

            query = query.limit(limit).offset(offset)

            result = await self._session.execute(query)
            merchants = result.scalars().all()

            return [self._model_to_entity(merchant) for merchant in merchants]

        except Exception as e:
            raise DomainException(
                f"Failed to find merchants by criteria: {e}", "REPOSITORY_ERROR"
            ) from e

    async def bulk_update_risk_rating(self, merchant_ids: list[UUID], new_rating: int) -> int:
        """Bulk update risk rating for multiple merchants.

        Args:
            merchant_ids: List of merchant IDs to update
            new_rating: New risk rating

        Returns:
            Number of merchants updated
        """
        try:
            if not merchant_ids:
                return 0

            result = await self._session.execute(
                update(MerchantModel)
                .where(and_(MerchantModel.id.in_(merchant_ids), MerchantModel.deleted_at.is_(None)))
                .values(risk_rating=new_rating, updated_at=datetime.now(UTC))
            )

            return result.rowcount

        except Exception as e:
            await self._session.rollback()
            raise DomainException(
                f"Failed to bulk update risk rating: {e}", "REPOSITORY_ERROR"
            ) from e

    async def get_statistics_by_category(self) -> dict[str, dict[str, any]]:
        """Get merchant statistics grouped by category.

        Returns:
            Dictionary with category statistics
        """
        try:
            result = await self._session.execute(
                select(
                    MerchantModel.merchant_category,
                    func.count(MerchantModel.id).label("merchant_count"),
                    func.avg(MerchantModel.risk_rating).label("avg_risk_rating"),
                    func.avg(MerchantModel.historical_fraud_rate).label("avg_fraud_rate"),
                    func.sum(MerchantModel.total_transactions).label("total_transactions"),
                    func.sum(MerchantModel.total_volume).label("total_volume"),
                )
                .where(and_(MerchantModel.deleted_at.is_(None), MerchantModel.is_active))
                .group_by(MerchantModel.merchant_category)
            )

            stats = {}
            for row in result:
                stats[row.merchant_category] = {
                    "merchant_count": row.merchant_count,
                    "avg_risk_rating": float(row.avg_risk_rating or 0),
                    "avg_fraud_rate": float(row.avg_fraud_rate or 0),
                    "total_transactions": row.total_transactions or 0,
                    "total_volume": float(row.total_volume or 0),
                }

            return stats

        except Exception as e:
            raise DomainException(
                f"Failed to get merchant statistics: {e}", "REPOSITORY_ERROR"
            ) from e

    async def get_by_country(
        self,
        country: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Merchant]:
        """List merchants by country.

        Args:
            country: Country code
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of merchants
        """
        try:
            # Validate and cap limit
            limit = min(max(1, limit), 1000)
            offset = max(0, offset)

            query = (
                select(MerchantModel)
                .where(
                    and_(
                        MerchantModel.country == country.upper(),
                        MerchantModel.deleted_at.is_(None),
                    )
                )
                .order_by(MerchantModel.merchant_name)
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(query)
            merchant_models = result.scalars().all()

            return [self._model_to_entity(model) for model in merchant_models]

        except Exception as e:
            raise DomainException(
                f"Failed to list merchants by country: {e}", "REPOSITORY_ERROR"
            ) from e

    async def list_by_risk_level(
        self,
        min_risk: int,
        max_risk: int,
        limit: int = 100,
    ) -> list[Merchant]:
        """List merchants by risk rating range.

        Args:
            min_risk: Minimum risk rating (0-100)
            max_risk: Maximum risk rating (0-100)
            limit: Maximum number of results

        Returns:
            List of merchants
        """
        try:
            # Validate risk range
            min_risk = max(0, min_risk)
            max_risk = min(100, max_risk)
            limit = min(max(1, limit), 1000)

            if min_risk > max_risk:
                raise ValueError(
                    f"min_risk ({min_risk}) cannot be greater than max_risk ({max_risk})"
                )

            query = (
                select(MerchantModel)
                .where(
                    and_(
                        MerchantModel.risk_rating >= min_risk,
                        MerchantModel.risk_rating <= max_risk,
                        MerchantModel.deleted_at.is_(None),
                    )
                )
                .order_by(desc(MerchantModel.risk_rating), MerchantModel.merchant_name)
                .limit(limit)
            )

            result = await self._session.execute(query)
            merchant_models = result.scalars().all()

            return [self._model_to_entity(model) for model in merchant_models]

        except Exception as e:
            raise DomainException(
                f"Failed to list merchants by risk level: {e}", "REPOSITORY_ERROR"
            ) from e

    def _model_to_entity(self, model: MerchantModel) -> Merchant:
        """Convert database model to domain entity.

        Args:
            model: SQLAlchemy model instance

        Returns:
            Domain entity
        """
        from decimal import Decimal

        return Merchant(
            merchant_id=model.id,
            merchant_name=model.merchant_name,
            mcc=model.mcc,
            merchant_category=model.merchant_category,
            country=model.country,
            risk_rating=model.risk_rating,
            historical_fraud_rate=Decimal(str(model.historical_fraud_rate)),
            total_transactions=model.total_transactions,
            total_volume=Decimal(str(model.total_volume)),
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
