"""Alert Repository Implementation using SQLAlchemy Async."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, desc, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.alert_repository import AlertRepository
from src.domain.entities.alert import Alert
from src.domain.exceptions.base import DomainException
from src.infrastructure.database.models import AlertModel


class AlertNotFoundError(DomainException):
    """Raised when alert is not found."""

    def __init__(self, alert_id: UUID) -> None:
        super().__init__(f"Alert with ID {alert_id} not found", "ALERT_NOT_FOUND")


class AlertRepositoryImpl(AlertRepository):
    """SQLAlchemy implementation of AlertRepository.

    Provides async database operations for Alert entities with
    comprehensive querying and SLA tracking capabilities.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, alert: Alert) -> Alert:
        """Create a new alert.

        Args:
            alert: Alert entity to create

        Returns:
            Created alert with generated ID

        Raises:
            RepositoryError: If creation fails
        """
        try:
            # Calculate SLA deadline (24 hours from creation for most alerts)
            sla_hours = 24
            if alert.severity == "critical":
                sla_hours = 2
            elif alert.severity == "high":
                sla_hours = 8

            sla_deadline = alert.created_at.replace(
                hour=(alert.created_at.hour + sla_hours) % 24
            )

            # Convert domain entity to database model
            alert_model = AlertModel(
                id=alert.alert_id,
                transaction_id=alert.transaction_id,
                prediction_id=alert.prediction_id,
                alert_type=alert.alert_type,
                severity=alert.severity,
                status=alert.status,
                assigned_analyst_id=alert.assigned_analyst_id,
                assigned_at=alert.assigned_at,
                resolution=alert.resolution,
                resolved_at=alert.resolved_at,
                resolved_by_id=None,  # Would need to track resolver
                sla_deadline=sla_deadline,
                is_sla_breached=False,
                created_at=alert.created_at,
                updated_at=alert.updated_at
            )

            self._session.add(alert_model)
            await self._session.flush()
            await self._session.refresh(alert_model)

            return self._model_to_entity(alert_model)

        except IntegrityError as e:
            await self._session.rollback()
            raise DomainException(f"Database constraint violation: {e}", "DB_CONSTRAINT_ERROR")

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to create alert: {e}", "REPOSITORY_ERROR")

    async def get_by_id(self, alert_id: UUID) -> Alert | None:
        """Retrieve alert by ID.

        Args:
            alert_id: Alert UUID

        Returns:
            Alert if found, None otherwise
        """
        try:
            result = await self._session.execute(
                select(AlertModel).where(
                    and_(
                        AlertModel.id == alert_id,
                        AlertModel.deleted_at.is_(None)
                    )
                )
            )
            alert_model = result.scalar_one_or_none()

            if alert_model:
                return self._model_to_entity(alert_model)
            return None

        except Exception as e:
            raise DomainException(f"Failed to get alert by ID: {e}", "REPOSITORY_ERROR")

    async def update(self, alert: Alert) -> Alert:
        """Update existing alert.

        Args:
            alert: Alert entity with updated data

        Returns:
            Updated alert

        Raises:
            AlertNotFoundError: If alert doesn't exist
            RepositoryError: If update fails
        """
        try:
            # Check if alert exists
            existing = await self._session.execute(
                select(AlertModel).where(
                    and_(
                        AlertModel.id == alert.alert_id,
                        AlertModel.deleted_at.is_(None)
                    )
                )
            )
            if not existing.scalar_one_or_none():
                raise AlertNotFoundError(alert.alert_id)

            # Update fields
            await self._session.execute(
                update(AlertModel)
                .where(AlertModel.id == alert.alert_id)
                .values(
                    status=alert.status,
                    assigned_analyst_id=alert.assigned_analyst_id,
                    assigned_at=alert.assigned_at,
                    resolution=alert.resolution,
                    resolved_at=alert.resolved_at,
                    severity=alert.severity,
                    updated_at=datetime.utcnow()
                )
            )

            # Fetch updated record
            result = await self._session.execute(
                select(AlertModel).where(AlertModel.id == alert.alert_id)
            )
            updated_model = result.scalar_one()

            return self._model_to_entity(updated_model)

        except AlertNotFoundError:
            raise
        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to update alert: {e}", "REPOSITORY_ERROR")

    async def delete(self, alert_id: UUID) -> bool:
        """Soft delete alert.

        Args:
            alert_id: Alert UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self._session.execute(
                update(AlertModel)
                .where(
                    and_(
                        AlertModel.id == alert_id,
                        AlertModel.deleted_at.is_(None)
                    )
                )
                .values(deleted_at=datetime.utcnow())
            )

            return result.rowcount > 0

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to delete alert: {e}", "REPOSITORY_ERROR")

    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        """List alerts by status.

        Args:
            status: Alert status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of alerts
        """
        try:
            result = await self._session.execute(
                select(AlertModel)
                .where(
                    and_(
                        AlertModel.status == status,
                        AlertModel.deleted_at.is_(None)
                    )
                )
                .order_by(desc(AlertModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            alerts = result.scalars().all()
            return [self._model_to_entity(alert) for alert in alerts]

        except Exception as e:
            raise DomainException(f"Failed to list alerts by status: {e}", "REPOSITORY_ERROR")

    async def list_by_severity(
        self,
        severity: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        """List alerts by severity.

        Args:
            severity: Alert severity level
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of alerts
        """
        try:
            result = await self._session.execute(
                select(AlertModel)
                .where(
                    and_(
                        AlertModel.severity == severity,
                        AlertModel.deleted_at.is_(None)
                    )
                )
                .order_by(desc(AlertModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            alerts = result.scalars().all()
            return [self._model_to_entity(alert) for alert in alerts]

        except Exception as e:
            raise DomainException(f"Failed to list alerts by severity: {e}", "REPOSITORY_ERROR")

    async def list_by_analyst(
        self,
        analyst_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        """List alerts assigned to analyst.

        Args:
            analyst_id: Analyst user ID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of alerts
        """
        try:
            result = await self._session.execute(
                select(AlertModel)
                .where(
                    and_(
                        AlertModel.assigned_analyst_id == analyst_id,
                        AlertModel.deleted_at.is_(None)
                    )
                )
                .order_by(desc(AlertModel.severity), desc(AlertModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            alerts = result.scalars().all()
            return [self._model_to_entity(alert) for alert in alerts]

        except Exception as e:
            raise DomainException(f"Failed to list alerts by analyst: {e}", "REPOSITORY_ERROR")

    async def list_unassigned(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        """List unassigned alerts.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of unassigned alerts
        """
        try:
            result = await self._session.execute(
                select(AlertModel)
                .where(
                    and_(
                        AlertModel.assigned_analyst_id.is_(None),
                        AlertModel.status == "open",
                        AlertModel.deleted_at.is_(None)
                    )
                )
                .order_by(desc(AlertModel.severity), desc(AlertModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            alerts = result.scalars().all()
            return [self._model_to_entity(alert) for alert in alerts]

        except Exception as e:
            raise DomainException(f"Failed to list unassigned alerts: {e}", "REPOSITORY_ERROR")

    async def list_sla_breached(self, limit: int = 100) -> list[Alert]:
        """List alerts that have breached SLA.

        Args:
            limit: Maximum number of results

        Returns:
            List of SLA-breached alerts
        """
        try:
            current_time = datetime.utcnow()

            result = await self._session.execute(
                select(AlertModel)
                .where(
                    and_(
                        AlertModel.sla_deadline < current_time,
                        AlertModel.status.in_(["open", "in_review"]),
                        AlertModel.deleted_at.is_(None)
                    )
                )
                .order_by(AlertModel.sla_deadline.asc())
                .limit(limit)
            )

            alerts = result.scalars().all()
            return [self._model_to_entity(alert) for alert in alerts]

        except Exception as e:
            raise DomainException(f"Failed to list SLA-breached alerts: {e}", "REPOSITORY_ERROR")

    async def count_by_status(self, status: str) -> int:
        """Count alerts by status.

        Args:
            status: Alert status

        Returns:
            Number of alerts
        """
        try:
            from sqlalchemy import func
            result = await self._session.execute(
                select(func.count(AlertModel.id))
                .where(
                    and_(
                        AlertModel.status == status,
                        AlertModel.deleted_at.is_(None)
                    )
                )
            )

            return result.scalar() or 0

        except Exception as e:
            raise DomainException(f"Failed to count alerts by status: {e}", "REPOSITORY_ERROR")

    async def get_alerts_for_transaction(
        self,
        transaction_id: UUID,
    ) -> list[Alert]:
        """Get all alerts for a transaction.

        Args:
            transaction_id: Transaction UUID

        Returns:
            List of alerts
        """
        try:
            result = await self._session.execute(
                select(AlertModel)
                .where(
                    and_(
                        AlertModel.transaction_id == transaction_id,
                        AlertModel.deleted_at.is_(None)
                    )
                )
                .order_by(desc(AlertModel.created_at))
            )

            alerts = result.scalars().all()
            return [self._model_to_entity(alert) for alert in alerts]

        except Exception as e:
            raise DomainException(f"Failed to get alerts for transaction: {e}", "REPOSITORY_ERROR")

    async def get_open_alerts_in_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[Alert]:
        """Get open alerts within date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of alerts
        """
        try:
            result = await self._session.execute(
                select(AlertModel)
                .where(
                    and_(
                        AlertModel.status.in_(["open", "in_review"]),
                        AlertModel.created_at >= start_date,
                        AlertModel.created_at <= end_date,
                        AlertModel.deleted_at.is_(None)
                    )
                )
                .order_by(desc(AlertModel.severity), desc(AlertModel.created_at))
            )

            alerts = result.scalars().all()
            return [self._model_to_entity(alert) for alert in alerts]

        except Exception as e:
            raise DomainException(f"Failed to get open alerts in range: {e}", "REPOSITORY_ERROR")

    async def update_sla_breach_status(self) -> int:
        """Update SLA breach status for overdue alerts.

        Returns:
            Number of alerts marked as SLA breached
        """
        try:
            current_time = datetime.utcnow()

            result = await self._session.execute(
                update(AlertModel)
                .where(
                    and_(
                        AlertModel.sla_deadline < current_time,
                        AlertModel.is_sla_breached == False,
                        AlertModel.status.in_(["open", "in_review"]),
                        AlertModel.deleted_at.is_(None)
                    )
                )
                .values(
                    is_sla_breached=True,
                    updated_at=current_time
                )
            )

            return result.rowcount

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to update SLA breach status: {e}", "REPOSITORY_ERROR")

    def _model_to_entity(self, model: AlertModel) -> Alert:
        """Convert database model to domain entity.

        Args:
            model: SQLAlchemy model instance

        Returns:
            Domain entity
        """
        return Alert(
            alert_id=model.id,
            prediction_id=model.prediction_id,
            transaction_id=model.transaction_id,
            severity=model.severity,
            alert_type=model.alert_type,
            assigned_analyst_id=model.assigned_analyst_id,
            status=model.status,
            resolution=model.resolution,
            resolution_notes=None,  # Not in current model
            created_at=model.created_at,
            assigned_at=model.assigned_at,
            resolved_at=model.resolved_at,
            updated_at=model.updated_at
        )
