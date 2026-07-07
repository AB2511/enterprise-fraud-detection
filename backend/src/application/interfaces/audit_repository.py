"""Audit Log Repository Interface."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.domain.entities.audit_log import AuditLog


class AuditRepository(ABC):
    """Repository interface for AuditLog entity.

    Audit logs are immutable and append-only.
    """

    @abstractmethod
    async def create(self, audit_log: AuditLog) -> AuditLog:
        """Create a new audit log entry.

        Args:
            audit_log: AuditLog entity to create

        Returns:
            Created audit log with generated ID

        Raises:
            RepositoryError: If creation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, log_id: UUID) -> Optional[AuditLog]:
        """Retrieve audit log by ID.

        Args:
            log_id: Audit log UUID

        Returns:
            AuditLog if found, None otherwise
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def list_by_action(
        self,
        action: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """List audit logs by action type.

        Args:
            action: Action type (e.g., "created", "updated", "deleted")
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of audit logs
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def count_by_entity(self, entity_type: str, entity_id: UUID) -> int:
        """Count audit logs for entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID

        Returns:
            Number of audit logs
        """
        pass
