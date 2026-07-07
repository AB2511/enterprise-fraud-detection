"""Audit Repository Implementation using SQLAlchemy Async."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, desc, select, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.audit_repository import AuditRepository
from src.domain.entities.audit_log import AuditLog
from src.domain.exceptions.base import DomainException, NotFoundError, RepositoryError
from src.infrastructure.database.models import AuditLogModel


class AuditRepositoryImpl(AuditRepository):
    """SQLAlchemy implementation of AuditRepository.

    Provides append-only audit log operations with comprehensive
    search and filtering capabilities for compliance and forensics.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, audit_log: AuditLog) -> AuditLog:
        """Create a new audit log entry.

        Args:
            audit_log: AuditLog entity to create

        Returns:
            Created audit log with generated ID

        Raises:
            RepositoryError: If creation fails
        """
        try:
            # Convert domain entity to database model
            audit_model = AuditLogModel(
                id=audit_log.audit_id,
                entity_type=audit_log.entity_type,
                entity_id=audit_log.entity_id,
                action=audit_log.action,
                user_id=audit_log.user_id,
                username=audit_log.username,
                old_value=audit_log.old_value,
                new_value=audit_log.new_value,
                ip_address=audit_log.ip_address,
                user_agent=audit_log.user_agent,
                description=audit_log.description,
                created_at=audit_log.created_at
            )

            self._session.add(audit_model)
            await self._session.flush()
            await self._session.refresh(audit_model)

            return self._model_to_entity(audit_model)

        except IntegrityError as e:
            await self._session.rollback()
            raise DomainException(f"Database constraint violation: {e}", "DB_CONSTRAINT_ERROR")

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to create audit log: {e}", "REPOSITORY_ERROR")

    async def get_by_id(self, log_id: UUID) -> Optional[AuditLog]:
        """Retrieve audit log by ID.

        Args:
            log_id: Audit log UUID

        Returns:
            AuditLog if found, None otherwise
        """
        try:
            result = await self._session.execute(
                select(AuditLogModel).where(AuditLogModel.id == log_id)
            )
            audit_model = result.scalar_one_or_none()
            
            if audit_model:
                return self._model_to_entity(audit_model)
            return None

        except Exception as e:
            raise DomainException(f"Failed to get audit log by ID: {e}", "REPOSITORY_ERROR")

    async def list_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """List audit logs for specific entity.

        Args:
            entity_type: Type of entity (e.g., "transaction", "customer")
            entity_id: Entity UUID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of audit logs
        """
        try:
            result = await self._session.execute(
                select(AuditLogModel)
                .where(
                    and_(
                        AuditLogModel.entity_type == entity_type,
                        AuditLogModel.entity_id == entity_id
                    )
                )
                .order_by(desc(AuditLogModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            audit_logs = result.scalars().all()
            return [self._model_to_entity(log) for log in audit_logs]

        except Exception as e:
            raise DomainException(f"Failed to list audit logs by entity: {e}", "REPOSITORY_ERROR")

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """List audit logs by user.

        Args:
            user_id: User UUID who performed action
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of audit logs
        """
        try:
            result = await self._session.execute(
                select(AuditLogModel)
                .where(AuditLogModel.user_id == user_id)
                .order_by(desc(AuditLogModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            audit_logs = result.scalars().all()
            return [self._model_to_entity(log) for log in audit_logs]

        except Exception as e:
            raise DomainException(f"Failed to list audit logs by user: {e}", "REPOSITORY_ERROR")

    async def list_by_action(
        self,
        action: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """List audit logs by action type.

        Args:
            action: Action type (e.g., "CREATE", "UPDATE", "DELETE")
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of audit logs
        """
        try:
            result = await self._session.execute(
                select(AuditLogModel)
                .where(AuditLogModel.action == action)
                .order_by(desc(AuditLogModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            audit_logs = result.scalars().all()
            return [self._model_to_entity(log) for log in audit_logs]

        except Exception as e:
            raise DomainException(f"Failed to list audit logs by action: {e}", "REPOSITORY_ERROR")

    async def list_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[AuditLog]:
        """List audit logs within date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of audit logs
        """
        try:
            result = await self._session.execute(
                select(AuditLogModel)
                .where(
                    and_(
                        AuditLogModel.created_at >= start_date,
                        AuditLogModel.created_at <= end_date
                    )
                )
                .order_by(desc(AuditLogModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            audit_logs = result.scalars().all()
            return [self._model_to_entity(log) for log in audit_logs]

        except Exception as e:
            raise DomainException(f"Failed to list audit logs by date range: {e}", "REPOSITORY_ERROR")

    async def search(
        self,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        user_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Search audit logs with multiple filters.

        Args:
            entity_type: Optional entity type filter
            action: Optional action filter
            user_id: Optional user filter
            start_date: Optional start date
            end_date: Optional end date
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of audit logs matching filters
        """
        try:
            query = select(AuditLogModel)
            conditions = []

            # Add filters dynamically
            if entity_type:
                conditions.append(AuditLogModel.entity_type == entity_type)
            if action:
                conditions.append(AuditLogModel.action == action)
            if user_id:
                conditions.append(AuditLogModel.user_id == user_id)
            if start_date:
                conditions.append(AuditLogModel.created_at >= start_date)
            if end_date:
                conditions.append(AuditLogModel.created_at <= end_date)

            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(desc(AuditLogModel.created_at)).limit(limit).offset(offset)

            result = await self._session.execute(query)
            audit_logs = result.scalars().all()
            
            return [self._model_to_entity(log) for log in audit_logs]

        except Exception as e:
            raise DomainException(f"Failed to search audit logs: {e}", "REPOSITORY_ERROR")

    async def count_by_entity(self, entity_type: str, entity_id: UUID) -> int:
        """Count audit logs for entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID

        Returns:
            Number of audit logs
        """
        try:
            from sqlalchemy import func
            result = await self._session.execute(
                select(func.count(AuditLogModel.id))
                .where(
                    and_(
                        AuditLogModel.entity_type == entity_type,
                        AuditLogModel.entity_id == entity_id
                    )
                )
            )

            return result.scalar() or 0

        except Exception as e:
            raise DomainException(f"Failed to count audit logs by entity: {e}", "REPOSITORY_ERROR")

    async def get_audit_trail_summary(
        self,
        entity_type: str,
        entity_id: UUID
    ) -> dict[str, any]:
        """Get audit trail summary for an entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID

        Returns:
            Summary statistics for the audit trail
        """
        try:
            # Simplified approach using COUNT with WHERE conditions
            result = await self._session.execute(
                select(
                    func.count(AuditLogModel.id).label("total_events"),
                    func.count(func.distinct(AuditLogModel.user_id)).label("unique_users"),
                    func.min(AuditLogModel.created_at).label("first_event"),
                    func.max(AuditLogModel.created_at).label("last_event"),
                )
                .where(
                    and_(
                        AuditLogModel.entity_type == entity_type,
                        AuditLogModel.entity_id == entity_id
                    )
                )
            )

            row = result.first()

            if not row or row.total_events == 0:
                return {
                    "total_events": 0,
                    "unique_users": 0,
                    "first_event": None,
                    "last_event": None,
                    "create_count": 0,
                    "update_count": 0,
                    "delete_count": 0,
                    "read_count": 0
                }

            # Get action counts separately
            create_count_result = await self._session.execute(
                select(func.count(AuditLogModel.id))
                .where(
                    and_(
                        AuditLogModel.entity_type == entity_type,
                        AuditLogModel.entity_id == entity_id,
                        AuditLogModel.action == "CREATE"
                    )
                )
            )
            create_count = create_count_result.scalar() or 0

            update_count_result = await self._session.execute(
                select(func.count(AuditLogModel.id))
                .where(
                    and_(
                        AuditLogModel.entity_type == entity_type,
                        AuditLogModel.entity_id == entity_id,
                        AuditLogModel.action == "UPDATE"
                    )
                )
            )
            update_count = update_count_result.scalar() or 0

            delete_count_result = await self._session.execute(
                select(func.count(AuditLogModel.id))
                .where(
                    and_(
                        AuditLogModel.entity_type == entity_type,
                        AuditLogModel.entity_id == entity_id,
                        AuditLogModel.action == "DELETE"
                    )
                )
            )
            delete_count = delete_count_result.scalar() or 0

            read_count_result = await self._session.execute(
                select(func.count(AuditLogModel.id))
                .where(
                    and_(
                        AuditLogModel.entity_type == entity_type,
                        AuditLogModel.entity_id == entity_id,
                        AuditLogModel.action == "READ"
                    )
                )
            )
            read_count = read_count_result.scalar() or 0

            return {
                "total_events": row.total_events,
                "unique_users": row.unique_users,
                "first_event": row.first_event,
                "last_event": row.last_event,
                "create_count": create_count,
                "update_count": update_count,
                "delete_count": delete_count,
                "read_count": read_count
            }

        except Exception as e:
            raise DomainException(f"Failed to get audit trail summary: {e}", "REPOSITORY_ERROR")

    async def get_user_activity_summary(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict[str, any]:
        """Get user activity summary.

        Args:
            user_id: User UUID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            User activity statistics
        """
        try:
            # Simplified approach using separate queries
            base_query = select(func.count(AuditLogModel.id)).where(AuditLogModel.user_id == user_id)
            
            if start_date:
                base_query = base_query.where(AuditLogModel.created_at >= start_date)
            if end_date:
                base_query = base_query.where(AuditLogModel.created_at <= end_date)

            # Get total count
            total_result = await self._session.execute(base_query)
            total_actions = total_result.scalar() or 0

            if total_actions == 0:
                return {
                    "total_actions": 0,
                    "entity_types": 0,
                    "create_count": 0,
                    "update_count": 0,
                    "delete_count": 0,
                    "read_count": 0
                }

            # Get entity types count
            entity_types_query = select(func.count(func.distinct(AuditLogModel.entity_type))).where(AuditLogModel.user_id == user_id)
            if start_date:
                entity_types_query = entity_types_query.where(AuditLogModel.created_at >= start_date)
            if end_date:
                entity_types_query = entity_types_query.where(AuditLogModel.created_at <= end_date)

            entity_types_result = await self._session.execute(entity_types_query)
            entity_types_count = entity_types_result.scalar() or 0

            # Get action counts
            create_query = base_query.where(AuditLogModel.action == "CREATE")
            create_result = await self._session.execute(create_query)
            create_count = create_result.scalar() or 0

            update_query = base_query.where(AuditLogModel.action == "UPDATE")
            update_result = await self._session.execute(update_query)
            update_count = update_result.scalar() or 0

            delete_query = base_query.where(AuditLogModel.action == "DELETE")
            delete_result = await self._session.execute(delete_query)
            delete_count = delete_result.scalar() or 0

            read_query = base_query.where(AuditLogModel.action == "READ")
            read_result = await self._session.execute(read_query)
            read_count = read_result.scalar() or 0

            return {
                "total_actions": total_actions,
                "entity_types": entity_types_count,
                "create_count": create_count,
                "update_count": update_count,
                "delete_count": delete_count,
                "read_count": read_count
            }

        except Exception as e:
            raise DomainException(f"Failed to get user activity summary: {e}", "REPOSITORY_ERROR")

    def _model_to_entity(self, model: AuditLogModel) -> AuditLog:
        """Convert database model to domain entity.

        Args:
            model: SQLAlchemy model instance

        Returns:
            Domain entity
        """
        return AuditLog(
            audit_id=model.id,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            action=model.action,
            user_id=model.user_id,
            username=model.username,
            old_value=model.old_value,
            new_value=model.new_value,
            ip_address=model.ip_address,
            user_agent=model.user_agent,
            description=model.description,
            created_at=model.created_at
        )