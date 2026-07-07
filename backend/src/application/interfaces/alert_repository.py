"""Alert Repository Interface."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.alert import Alert


class AlertRepository(ABC):
    """Repository interface for Alert entity."""

    @abstractmethod
    async def create(self, alert: Alert) -> Alert:
        """Create a new alert.

        Args:
            alert: Alert entity to create

        Returns:
            Created alert with generated ID

        Raises:
            RepositoryError: If creation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, alert_id: UUID) -> Alert | None:
        """Retrieve alert by ID.

        Args:
            alert_id: Alert UUID

        Returns:
            Alert if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, alert: Alert) -> Alert:
        """Update existing alert.

        Args:
            alert: Alert entity with updated data

        Returns:
            Updated alert

        Raises:
            RepositoryError: If update fails
            NotFoundError: If alert doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, alert_id: UUID) -> bool:
        """Soft delete alert.

        Args:
            alert_id: Alert UUID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def list_sla_breached(self, limit: int = 100) -> list[Alert]:
        """List alerts that have breached SLA.

        Args:
            limit: Maximum number of results

        Returns:
            List of SLA-breached alerts
        """
        pass

    @abstractmethod
    async def count_by_status(self, status: str) -> int:
        """Count alerts by status.

        Args:
            status: Alert status

        Returns:
            Number of alerts
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass
