"""Transaction Repository Implementation using SQLAlchemy Async."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, case, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.transaction_repository import TransactionRepository
from src.domain.entities.transaction import Transaction
from src.domain.exceptions.base import DomainException
from src.infrastructure.database.models import TransactionModel


class TransactionNotFoundError(DomainException):
    """Raised when transaction is not found."""

    def __init__(self, transaction_id: UUID) -> None:
        super().__init__(f"Transaction with ID {transaction_id} not found", "TRANSACTION_NOT_FOUND")


class TransactionRepositoryImpl(TransactionRepository):
    """SQLAlchemy implementation of TransactionRepository.

    Provides async database operations for Transaction entities with
    comprehensive querying, velocity calculations, and bulk operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, transaction: Transaction) -> Transaction:
        """Persist a transaction.

        Args:
            transaction: Transaction entity to save

        Returns:
            Saved transaction with any generated fields populated
        """
        try:
            # Convert domain entity to database model
            transaction_model = TransactionModel(
                id=transaction.transaction_id,
                customer_id=transaction.customer_id,
                merchant_id=transaction.merchant_id,
                amount=float(transaction.amount),
                currency=transaction.currency,
                transaction_type=transaction.transaction_type,
                status=transaction.status,
                payment_channel=transaction.payment_channel,
                payment_method=transaction.payment_method,
                terminal_id=transaction.terminal_id,
                device_id=transaction.device_id,
                ip_address=transaction.ip_address,
                latitude=transaction.latitude,
                longitude=transaction.longitude,
                velocity_1h=transaction.velocity_1h,
                velocity_24h=transaction.velocity_24h,
                velocity_7d=transaction.velocity_7d,
                is_fraud=transaction.is_fraud,
                fraud_confirmed_at=None,  # Will be set when fraud is confirmed
                created_at=transaction.created_at,
                updated_at=transaction.updated_at,
            )

            self._session.add(transaction_model)
            await self._session.flush()
            await self._session.refresh(transaction_model)

            return self._model_to_entity(transaction_model)

        except IntegrityError as e:
            await self._session.rollback()
            raise DomainException(
                f"Database constraint violation: {e}", "DB_CONSTRAINT_ERROR"
            ) from e

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to save transaction: {e}", "REPOSITORY_ERROR") from e

    async def save(self, transaction: Transaction) -> Transaction:
        """Backward-compatible alias for create."""
        return await self.create(transaction)

    async def get_by_id(self, transaction_id: UUID) -> Transaction | None:
        """Retrieve transaction by ID.

        Args:
            transaction_id: Unique identifier

        Returns:
            Transaction if found, None otherwise
        """
        try:
            result = await self._session.execute(
                select(TransactionModel).where(
                    and_(
                        TransactionModel.id == transaction_id, TransactionModel.deleted_at.is_(None)
                    )
                )
            )
            transaction_model = result.scalar_one_or_none()

            if transaction_model:
                return self._model_to_entity(transaction_model)
            return None

        except Exception as e:
            raise DomainException(
                f"Failed to get transaction by ID: {e}", "REPOSITORY_ERROR"
            ) from e

    async def get_by_user(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[Transaction]:
        """Get transactions for a specific user.

        Args:
            user_id: User identifier (customer_id)
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of transactions to return

        Returns:
            List of transactions
        """
        try:
            query = select(TransactionModel).where(
                and_(
                    TransactionModel.customer_id == UUID(user_id),
                    TransactionModel.deleted_at.is_(None),
                )
            )

            # Add date filters if provided
            if start_date:
                query = query.where(TransactionModel.created_at >= start_date)
            if end_date:
                query = query.where(TransactionModel.created_at <= end_date)

            query = query.order_by(desc(TransactionModel.created_at)).limit(limit)

            result = await self._session.execute(query)
            transactions = result.scalars().all()

            return [self._model_to_entity(txn) for txn in transactions]

        except Exception as e:
            raise DomainException(
                f"Failed to get transactions by user: {e}", "REPOSITORY_ERROR"
            ) from e

    async def count_recent_transactions(
        self,
        user_id: str,
        minutes: int,
    ) -> int:
        """Count recent transactions for a user (for velocity features).

        Args:
            user_id: User identifier (customer_id)
            minutes: Time window in minutes

        Returns:
            Count of transactions in time window
        """
        try:
            cutoff_time = datetime.now(UTC) - timedelta(minutes=minutes)

            result = await self._session.execute(
                select(func.count(TransactionModel.id)).where(
                    and_(
                        TransactionModel.customer_id == UUID(user_id),
                        TransactionModel.created_at >= cutoff_time,
                        TransactionModel.deleted_at.is_(None),
                    )
                )
            )

            return result.scalar() or 0

        except Exception as e:
            raise DomainException(
                f"Failed to count recent transactions: {e}", "REPOSITORY_ERROR"
            ) from e

    async def delete(self, transaction_id: UUID) -> bool:
        """Delete a transaction (soft delete).

        Args:
            transaction_id: Unique identifier

        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self._session.execute(
                update(TransactionModel)
                .where(
                    and_(
                        TransactionModel.id == transaction_id, TransactionModel.deleted_at.is_(None)
                    )
                )
                .values(deleted_at=datetime.now(UTC))
            )

            return result.rowcount > 0

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to delete transaction: {e}", "REPOSITORY_ERROR") from e

    async def update(self, transaction: Transaction) -> Transaction:
        """Update existing transaction.

        Args:
            transaction: Transaction entity with updated data

        Returns:
            Updated transaction

        Raises:
            TransactionNotFoundError: If transaction doesn't exist
            RepositoryError: If update fails
        """
        try:
            # Check if transaction exists
            existing = await self._session.execute(
                select(TransactionModel).where(
                    and_(
                        TransactionModel.id == transaction.transaction_id,
                        TransactionModel.deleted_at.is_(None),
                    )
                )
            )
            if not existing.scalar_one_or_none():
                raise TransactionNotFoundError(transaction.transaction_id)

            # Update fields
            await self._session.execute(
                update(TransactionModel)
                .where(TransactionModel.id == transaction.transaction_id)
                .values(
                    status=transaction.status,
                    velocity_1h=transaction.velocity_1h,
                    velocity_24h=transaction.velocity_24h,
                    velocity_7d=transaction.velocity_7d,
                    is_fraud=transaction.is_fraud,
                    fraud_confirmed_at=datetime.now(UTC) if transaction.is_fraud else None,
                    updated_at=datetime.now(UTC),
                )
            )

            # Fetch updated record
            result = await self._session.execute(
                select(TransactionModel).where(TransactionModel.id == transaction.transaction_id)
            )
            updated_model = result.scalar_one()

            return self._model_to_entity(updated_model)

        except TransactionNotFoundError:
            raise
        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to update transaction: {e}", "REPOSITORY_ERROR") from e

    async def search(
        self,
        *,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        currency: str | None = None,
        transaction_type: str | None = None,
        payment_channel: str | None = None,
        payment_method: str | None = None,
        status: str | None = None,
        is_fraud: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """Search transactions by multiple criteria."""
        return await self._search_with_criteria(
            customer_id=customer_id,
            merchant_id=merchant_id,
            min_amount=min_amount,
            max_amount=max_amount,
            currency=currency,
            transaction_type=transaction_type,
            payment_channel=payment_channel,
            payment_method=payment_method,
            status=status,
            is_fraud=is_fraud,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

    async def list_recent(self, *, limit: int = 100, offset: int = 0) -> list[Transaction]:
        """List most recent transactions."""
        try:
            result = await self._session.execute(
                select(TransactionModel)
                .where(TransactionModel.deleted_at.is_(None))
                .order_by(desc(TransactionModel.created_at))
                .limit(limit)
                .offset(offset)
            )
            return [self._model_to_entity(txn) for txn in result.scalars().all()]
        except Exception as e:
            raise DomainException(f"Failed to list recent transactions: {e}", "REPOSITORY_ERROR") from e

    async def list_by_customer(
        self,
        *,
        customer_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        """List transactions for a customer."""
        try:
            query = (
                select(TransactionModel)
                .where(
                    and_(
                        TransactionModel.customer_id == customer_id,
                        TransactionModel.deleted_at.is_(None),
                    )
                )
                .order_by(desc(TransactionModel.created_at))
                .limit(limit)
                .offset(offset)
            )
            if start_date is not None:
                query = query.where(TransactionModel.created_at >= start_date)
            if end_date is not None:
                query = query.where(TransactionModel.created_at <= end_date)
            result = await self._session.execute(query)
            return [self._model_to_entity(txn) for txn in result.scalars().all()]
        except Exception as e:
            raise DomainException(f"Failed to list customer transactions: {e}", "REPOSITORY_ERROR") from e

    async def list_by_merchant(
        self,
        *,
        merchant_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        """List transactions for a merchant."""
        try:
            query = (
                select(TransactionModel)
                .where(
                    and_(
                        TransactionModel.merchant_id == merchant_id,
                        TransactionModel.deleted_at.is_(None),
                    )
                )
                .order_by(desc(TransactionModel.created_at))
                .limit(limit)
                .offset(offset)
            )
            if start_date is not None:
                query = query.where(TransactionModel.created_at >= start_date)
            if end_date is not None:
                query = query.where(TransactionModel.created_at <= end_date)
            result = await self._session.execute(query)
            return [self._model_to_entity(txn) for txn in result.scalars().all()]
        except Exception as e:
            raise DomainException(f"Failed to list merchant transactions: {e}", "REPOSITORY_ERROR") from e

    async def list_by_date_range(
        self,
        *,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        """List transactions within a date range."""
        try:
            result = await self._session.execute(
                select(TransactionModel)
                .where(
                    and_(
                        TransactionModel.created_at >= start_date,
                        TransactionModel.created_at <= end_date,
                        TransactionModel.deleted_at.is_(None),
                    )
                )
                .order_by(desc(TransactionModel.created_at))
                .limit(limit)
                .offset(offset)
            )
            return [self._model_to_entity(txn) for txn in result.scalars().all()]
        except Exception as e:
            raise DomainException(f"Failed to list transactions by date range: {e}", "REPOSITORY_ERROR") from e

    async def _search_with_criteria(
        self,
        *,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        currency: str | None = None,
        transaction_type: str | None = None,
        payment_channel: str | None = None,
        payment_method: str | None = None,
        status: str | None = None,
        is_fraud: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """Find transactions by multiple criteria."""
        try:
            query = select(TransactionModel).where(TransactionModel.deleted_at.is_(None))

            if customer_id is not None:
                query = query.where(TransactionModel.customer_id == customer_id)
            if merchant_id is not None:
                query = query.where(TransactionModel.merchant_id == merchant_id)
            if min_amount is not None:
                query = query.where(TransactionModel.amount >= float(min_amount))
            if max_amount is not None:
                query = query.where(TransactionModel.amount <= float(max_amount))
            if currency:
                query = query.where(TransactionModel.currency == currency)
            if transaction_type:
                query = query.where(TransactionModel.transaction_type == transaction_type)
            if payment_channel:
                query = query.where(TransactionModel.payment_channel == payment_channel)
            if payment_method:
                query = query.where(TransactionModel.payment_method == payment_method)
            if status:
                query = query.where(TransactionModel.status == status)
            if is_fraud is not None:
                query = query.where(TransactionModel.is_fraud == is_fraud)
            if start_date is not None:
                query = query.where(TransactionModel.created_at >= start_date)
            if end_date is not None:
                query = query.where(TransactionModel.created_at <= end_date)

            query = query.order_by(desc(TransactionModel.created_at)).limit(limit).offset(offset)

            result = await self._session.execute(query)
            transactions = result.scalars().all()
            return [self._model_to_entity(txn) for txn in transactions], len(transactions)

        except Exception as e:
            raise DomainException(
                f"Failed to find transactions by criteria: {e}", "REPOSITORY_ERROR"
            ) from e
    async def get_velocity_data(
        self,
        customer_id: UUID,
        reference_time: datetime,
        hours_1: int = 1,
        hours_24: int = 24,
        days_7: int = 7,
    ) -> dict[str, int]:
        """Get velocity data for a customer at a specific reference time.

        Args:
            customer_id: Customer ID
            reference_time: Reference timestamp for velocity calculation
            hours_1: Hours for 1-hour velocity (default 1)
            hours_24: Hours for 24-hour velocity (default 24)
            days_7: Days for 7-day velocity (default 7)

        Returns:
            Dictionary with velocity counts
        """
        try:
            # Calculate cutoff times
            cutoff_1h = reference_time - timedelta(hours=hours_1)
            cutoff_24h = reference_time - timedelta(hours=hours_24)
            cutoff_7d = reference_time - timedelta(days=days_7)

            # Get counts for each time window
            result_1h = await self._session.execute(
                select(func.count(TransactionModel.id)).where(
                    and_(
                        TransactionModel.customer_id == customer_id,
                        TransactionModel.created_at >= cutoff_1h,
                        TransactionModel.created_at < reference_time,
                        TransactionModel.deleted_at.is_(None),
                    )
                )
            )

            result_24h = await self._session.execute(
                select(func.count(TransactionModel.id)).where(
                    and_(
                        TransactionModel.customer_id == customer_id,
                        TransactionModel.created_at >= cutoff_24h,
                        TransactionModel.created_at < reference_time,
                        TransactionModel.deleted_at.is_(None),
                    )
                )
            )

            result_7d = await self._session.execute(
                select(func.count(TransactionModel.id)).where(
                    and_(
                        TransactionModel.customer_id == customer_id,
                        TransactionModel.created_at >= cutoff_7d,
                        TransactionModel.created_at < reference_time,
                        TransactionModel.deleted_at.is_(None),
                    )
                )
            )

            return {
                "velocity_1h": result_1h.scalar() or 0,
                "velocity_24h": result_24h.scalar() or 0,
                "velocity_7d": result_7d.scalar() or 0,
            }

        except Exception as e:
            raise DomainException(f"Failed to get velocity data: {e}", "REPOSITORY_ERROR") from e

    async def get_fraud_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        group_by: str = "day",
    ) -> list[dict[str, object]]:
        """Get fraud statistics over time.

        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            group_by: Grouping period ('day', 'week', 'month')

        Returns:
            List of fraud statistics by time period
        """
        try:
            # Default to last 30 days if no dates provided
            if not start_date:
                start_date = datetime.now(UTC) - timedelta(days=30)
            if not end_date:
                end_date = datetime.now(UTC)

            # Select appropriate date truncation function
            if group_by == "day":
                date_trunc = func.date(TransactionModel.created_at)
            elif group_by == "week":
                date_trunc = func.date_trunc("week", TransactionModel.created_at)
            else:  # month
                date_trunc = func.date_trunc("month", TransactionModel.created_at)

            result = await self._session.execute(
                select(
                    date_trunc.label("period"),
                    func.count(TransactionModel.id).label("total_transactions"),
                    func.sum(case((TransactionModel.is_fraud, 1), else_=0)).label("fraud_count"),
                    func.avg(TransactionModel.amount).label("avg_amount"),
                    func.sum(TransactionModel.amount).label("total_amount"),
                )
                .where(
                    and_(
                        TransactionModel.created_at >= start_date,
                        TransactionModel.created_at <= end_date,
                        TransactionModel.deleted_at.is_(None),
                    )
                )
                .group_by(date_trunc)
                .order_by(date_trunc)
            )

            stats = []
            for row in result:
                total_txns = row.total_transactions or 0
                fraud_count = row.fraud_count or 0
                fraud_rate = (fraud_count / total_txns * 100) if total_txns > 0 else 0.0

                stats.append(
                    {
                        "period": row.period,
                        "total_transactions": total_txns,
                        "fraud_count": fraud_count,
                        "fraud_rate": fraud_rate,
                        "avg_amount": float(row.avg_amount or 0),
                        "total_amount": float(row.total_amount or 0),
                    }
                )

            return stats

        except Exception as e:
            raise DomainException(f"Failed to get fraud statistics: {e}", "REPOSITORY_ERROR") from e

    async def bulk_update_fraud_status(
        self, transaction_ids: list[UUID], is_fraud: bool, confirmed_by: str | None = None
    ) -> int:
        """Bulk update fraud status for multiple transactions.

        Args:
            transaction_ids: List of transaction IDs to update
            is_fraud: New fraud status
            confirmed_by: User who confirmed the fraud status

        Returns:
            Number of transactions updated
        """
        try:
            if not transaction_ids:
                return 0

            update_values = {"is_fraud": is_fraud, "updated_at": datetime.now(UTC)}

            if is_fraud:
                update_values["fraud_confirmed_at"] = datetime.now(UTC)

            result = await self._session.execute(
                update(TransactionModel)
                .where(
                    and_(
                        TransactionModel.id.in_(transaction_ids),
                        TransactionModel.deleted_at.is_(None),
                    )
                )
                .values(update_values)
            )

            return result.rowcount

        except Exception as e:
            await self._session.rollback()
            raise DomainException(
                f"Failed to bulk update fraud status: {e}", "REPOSITORY_ERROR"
            ) from e

    def _model_to_entity(self, model: TransactionModel) -> Transaction:
        """Convert database model to domain entity.

        Args:
            model: SQLAlchemy model instance

        Returns:
            Domain entity
        """
        from decimal import Decimal

        return Transaction(
            transaction_id=UUID(str(model.id)), 
            customer_id=UUID(str(model.customer_id)), 
            merchant_id=UUID(str(model.merchant_id)), 
            amount=Decimal(str(model.amount)),
            currency=model.currency,
            timestamp=model.created_at,
            payment_channel=model.payment_channel,
            payment_method=model.payment_method,
            device_id=model.device_id,
            ip_address=model.ip_address,
            latitude=model.latitude,
            longitude=model.longitude,
            terminal_id=model.terminal_id,
            merchant_category="",  # Would need join to merchant table
            mcc="",  # Would need join to merchant table
            card_type=None,  # Not in current model
            card_last_four=None,  # Not in current model
            status=model.status,
            is_fraud=model.is_fraud,
            velocity_1h=int(model.velocity_1h or 0),
            velocity_24h=int(model.velocity_24h or 0),
            velocity_7d=int(model.velocity_7d or 0),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
