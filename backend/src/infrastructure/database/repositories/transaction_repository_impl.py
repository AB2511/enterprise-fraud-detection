"""Transaction Repository Implementation using SQLAlchemy Async."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, desc, func, select, update
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

    async def save(self, transaction: Transaction) -> Transaction:
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
                transaction_type=transaction.payment_channel,
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
                updated_at=transaction.updated_at
            )

            self._session.add(transaction_model)
            await self._session.flush()
            await self._session.refresh(transaction_model)

            return self._model_to_entity(transaction_model)

        except IntegrityError as e:
            await self._session.rollback()
            raise DomainException(f"Database constraint violation: {e}", "DB_CONSTRAINT_ERROR")

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to save transaction: {e}", "REPOSITORY_ERROR")

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
                        TransactionModel.id == transaction_id,
                        TransactionModel.deleted_at.is_(None)
                    )
                )
            )
            transaction_model = result.scalar_one_or_none()

            if transaction_model:
                return self._model_to_entity(transaction_model)
            return None

        except Exception as e:
            raise DomainException(f"Failed to get transaction by ID: {e}", "REPOSITORY_ERROR")

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
                    TransactionModel.deleted_at.is_(None)
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
            raise DomainException(f"Failed to get transactions by user: {e}", "REPOSITORY_ERROR")

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
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

            result = await self._session.execute(
                select(func.count(TransactionModel.id))
                .where(
                    and_(
                        TransactionModel.customer_id == UUID(user_id),
                        TransactionModel.created_at >= cutoff_time,
                        TransactionModel.deleted_at.is_(None)
                    )
                )
            )

            return result.scalar() or 0

        except Exception as e:
            raise DomainException(f"Failed to count recent transactions: {e}", "REPOSITORY_ERROR")

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
                        TransactionModel.id == transaction_id,
                        TransactionModel.deleted_at.is_(None)
                    )
                )
                .values(deleted_at=datetime.utcnow())
            )

            return result.rowcount > 0

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to delete transaction: {e}", "REPOSITORY_ERROR")

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
                        TransactionModel.deleted_at.is_(None)
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
                    fraud_confirmed_at=datetime.utcnow() if transaction.is_fraud else None,
                    updated_at=datetime.utcnow()
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
            raise DomainException(f"Failed to update transaction: {e}", "REPOSITORY_ERROR")

    async def find_by_criteria(
        self,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        currency: str | None = None,
        payment_channel: str | None = None,
        payment_method: str | None = None,
        status: str | None = None,
        is_fraud: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        country: str | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> list[Transaction]:
        """Find transactions by multiple criteria.

        Args:
            customer_id: Customer ID filter
            merchant_id: Merchant ID filter
            min_amount: Minimum amount filter
            max_amount: Maximum amount filter
            currency: Currency filter
            payment_channel: Payment channel filter
            payment_method: Payment method filter
            status: Transaction status filter
            is_fraud: Fraud status filter
            start_date: Start date filter
            end_date: End date filter
            country: Country filter (based on IP geolocation)
            limit: Maximum results
            offset: Results offset
            sort_by: Field to sort by
            sort_desc: Sort descending if True

        Returns:
            List of matching transactions
        """
        try:
            query = select(TransactionModel).where(TransactionModel.deleted_at.is_(None))

            # Add filters dynamically
            if customer_id:
                query = query.where(TransactionModel.customer_id == customer_id)
            if merchant_id:
                query = query.where(TransactionModel.merchant_id == merchant_id)
            if min_amount is not None:
                query = query.where(TransactionModel.amount >= min_amount)
            if max_amount is not None:
                query = query.where(TransactionModel.amount <= max_amount)
            if currency:
                query = query.where(TransactionModel.currency == currency)
            if payment_channel:
                query = query.where(TransactionModel.payment_channel == payment_channel)
            if payment_method:
                query = query.where(TransactionModel.payment_method == payment_method)
            if status:
                query = query.where(TransactionModel.status == status)
            if is_fraud is not None:
                query = query.where(TransactionModel.is_fraud == is_fraud)
            if start_date:
                query = query.where(TransactionModel.created_at >= start_date)
            if end_date:
                query = query.where(TransactionModel.created_at <= end_date)

            # Add sorting
            sort_column = getattr(TransactionModel, sort_by, TransactionModel.created_at)
            if sort_desc:
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)

            query = query.limit(limit).offset(offset)

            result = await self._session.execute(query)
            transactions = result.scalars().all()

            return [self._model_to_entity(txn) for txn in transactions]

        except Exception as e:
            raise DomainException(f"Failed to find transactions by criteria: {e}", "REPOSITORY_ERROR")

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
                select(func.count(TransactionModel.id))
                .where(
                    and_(
                        TransactionModel.customer_id == customer_id,
                        TransactionModel.created_at >= cutoff_1h,
                        TransactionModel.created_at < reference_time,
                        TransactionModel.deleted_at.is_(None)
                    )
                )
            )

            result_24h = await self._session.execute(
                select(func.count(TransactionModel.id))
                .where(
                    and_(
                        TransactionModel.customer_id == customer_id,
                        TransactionModel.created_at >= cutoff_24h,
                        TransactionModel.created_at < reference_time,
                        TransactionModel.deleted_at.is_(None)
                    )
                )
            )

            result_7d = await self._session.execute(
                select(func.count(TransactionModel.id))
                .where(
                    and_(
                        TransactionModel.customer_id == customer_id,
                        TransactionModel.created_at >= cutoff_7d,
                        TransactionModel.created_at < reference_time,
                        TransactionModel.deleted_at.is_(None)
                    )
                )
            )

            return {
                "velocity_1h": result_1h.scalar() or 0,
                "velocity_24h": result_24h.scalar() or 0,
                "velocity_7d": result_7d.scalar() or 0,
            }

        except Exception as e:
            raise DomainException(f"Failed to get velocity data: {e}", "REPOSITORY_ERROR")

    async def get_fraud_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        group_by: str = "day"
    ) -> list[dict[str, any]]:
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
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()

            # Select appropriate date truncation function
            if group_by == "day":
                date_trunc = func.date(TransactionModel.created_at)
            elif group_by == "week":
                date_trunc = func.date_trunc('week', TransactionModel.created_at)
            else:  # month
                date_trunc = func.date_trunc('month', TransactionModel.created_at)

            result = await self._session.execute(
                select(
                    date_trunc.label('period'),
                    func.count(TransactionModel.id).label('total_transactions'),
                    func.sum(func.cast(TransactionModel.is_fraud, func.Integer)).label('fraud_count'),
                    func.avg(TransactionModel.amount).label('avg_amount'),
                    func.sum(TransactionModel.amount).label('total_amount')
                )
                .where(
                    and_(
                        TransactionModel.created_at >= start_date,
                        TransactionModel.created_at <= end_date,
                        TransactionModel.deleted_at.is_(None)
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

                stats.append({
                    "period": row.period,
                    "total_transactions": total_txns,
                    "fraud_count": fraud_count,
                    "fraud_rate": fraud_rate,
                    "avg_amount": float(row.avg_amount or 0),
                    "total_amount": float(row.total_amount or 0)
                })

            return stats

        except Exception as e:
            raise DomainException(f"Failed to get fraud statistics: {e}", "REPOSITORY_ERROR")

    async def bulk_update_fraud_status(
        self,
        transaction_ids: list[UUID],
        is_fraud: bool,
        confirmed_by: str | None = None
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

            update_values = {
                "is_fraud": is_fraud,
                "updated_at": datetime.utcnow()
            }

            if is_fraud:
                update_values["fraud_confirmed_at"] = datetime.utcnow()

            result = await self._session.execute(
                update(TransactionModel)
                .where(
                    and_(
                        TransactionModel.id.in_(transaction_ids),
                        TransactionModel.deleted_at.is_(None)
                    )
                )
                .values(update_values)
            )

            return result.rowcount

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to bulk update fraud status: {e}", "REPOSITORY_ERROR")

    def _model_to_entity(self, model: TransactionModel) -> Transaction:
        """Convert database model to domain entity.

        Args:
            model: SQLAlchemy model instance

        Returns:
            Domain entity
        """
        from decimal import Decimal

        return Transaction(
            transaction_id=model.id,
            customer_id=model.customer_id,
            merchant_id=model.merchant_id,
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
            updated_at=model.updated_at
        )
