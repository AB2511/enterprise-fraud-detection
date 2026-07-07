"""Audit Service - Business workflows for audit log management."""

from datetime import datetime
from uuid import UUID

from src.application.interfaces.audit_repository import AuditRepository
from src.domain.entities.audit_log import AuditLog


class AuditService:
    """Service for audit log management and compliance.

    This service provides searching, filtering, and export capabilities
    for the immutable audit trail.
    """

    def __init__(
        self,
        audit_repository: AuditRepository,
    ) -> None:
        """Initialize audit service.

        Args:
            audit_repository: Repository for audit log queries
        """
        self._audit_repo = audit_repository

    async def search_audit_logs(
        self,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        action: str | None = None,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Search audit logs with multiple filters.

        Args:
            entity_type: Filter by entity type (customer, transaction, etc.)
            entity_id: Filter by specific entity
            action: Filter by action (created, updated, deleted)
            user_id: Filter by user who performed action
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of matching audit logs
        """
        return await self._audit_repo.search(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: UUID,
        limit: int = 100,
    ) -> list[dict]:
        """Get complete audit history for an entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID
            limit: Maximum records

        Returns:
            List of audit records with formatted data
        """
        logs = await self._audit_repo.list_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
        )

        return [
            {
                "log_id": str(log.log_id),
                "action": log.action,
                "timestamp": log.created_at.isoformat(),
                "user_id": str(log.user_id) if log.user_id else None,
                "username": log.username,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "ip_address": log.ip_address,
                "description": log.description,
            }
            for log in logs
        ]

    async def get_user_activity(
        self,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get activity log for a user.

        Args:
            user_id: User UUID
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum records

        Returns:
            List of user actions
        """
        # Get all logs by user
        all_logs = await self._audit_repo.list_by_user(
            user_id=user_id,
            limit=1000,  # Get more for filtering
        )

        # Filter by date if provided
        filtered_logs = all_logs
        if start_date:
            filtered_logs = [log for log in filtered_logs if log.created_at >= start_date]
        if end_date:
            filtered_logs = [log for log in filtered_logs if log.created_at <= end_date]

        # Limit results
        filtered_logs = filtered_logs[:limit]

        return [
            {
                "log_id": str(log.log_id),
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id),
                "action": log.action,
                "timestamp": log.created_at.isoformat(),
                "description": log.description,
            }
            for log in filtered_logs
        ]

    async def export_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        entity_types: list[str] | None = None,
    ) -> dict:
        """Export audit logs for compliance purposes.

        Args:
            start_date: Report start date
            end_date: Report end date
            entity_types: Filter by entity types (optional)

        Returns:
            Compliance report with logs and statistics
        """
        # Get logs in date range
        logs = await self._audit_repo.list_by_date_range(
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # Large limit for compliance
        )

        # Filter by entity types if provided
        if entity_types:
            logs = [log for log in logs if log.entity_type in entity_types]

        # Calculate statistics
        stats = {
            "total_events": len(logs),
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "by_entity_type": {},
            "by_action": {},
            "by_user": {},
        }

        # Count by entity type
        for log in logs:
            stats["by_entity_type"][log.entity_type] = (
                stats["by_entity_type"].get(log.entity_type, 0) + 1
            )
            stats["by_action"][log.action] = (
                stats["by_action"].get(log.action, 0) + 1
            )
            if log.user_id:
                user_key = str(log.user_id)
                stats["by_user"][user_key] = (
                    stats["by_user"].get(user_key, 0) + 1
                )

        # Format logs
        formatted_logs = [
            {
                "log_id": str(log.log_id),
                "timestamp": log.created_at.isoformat(),
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id),
                "action": log.action,
                "user_id": str(log.user_id) if log.user_id else None,
                "username": log.username,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "ip_address": log.ip_address,
            }
            for log in logs
        ]

        return {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "report_type": "compliance_audit",
            },
            "statistics": stats,
            "audit_logs": formatted_logs,
        }

    async def get_audit_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Get audit log statistics.

        Args:
            start_date: Start date for statistics
            end_date: End date for statistics

        Returns:
            Statistics dictionary
        """
        # Get logs in range
        if start_date and end_date:
            logs = await self._audit_repo.list_by_date_range(
                start_date=start_date,
                end_date=end_date,
                limit=10000,
            )
        else:
            # Get recent logs
            logs = await self._audit_repo.list_by_date_range(
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow(),
                limit=10000,
            )

        # Calculate statistics
        total = len(logs)
        by_action = {}
        by_entity = {}

        for log in logs:
            by_action[log.action] = by_action.get(log.action, 0) + 1
            by_entity[log.entity_type] = by_entity.get(log.entity_type, 0) + 1

        return {
            "total_events": total,
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "by_action": by_action,
            "by_entity_type": by_entity,
        }

    async def verify_audit_integrity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> dict:
        """Verify audit trail integrity for an entity.

        Args:
            entity_type: Entity type
            entity_id: Entity UUID

        Returns:
            Integrity verification result
        """
        # Get all logs for entity
        logs = await self._audit_repo.list_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=1000,
        )

        # Verify chronological order
        is_chronological = all(
            logs[i].created_at <= logs[i + 1].created_at
            for i in range(len(logs) - 1)
        )

        # Check for gaps
        has_creation = any(log.action == "created" for log in logs)

        return {
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "total_events": len(logs),
            "is_chronological": is_chronological,
            "has_creation_event": has_creation,
            "first_event": logs[0].created_at.isoformat() if logs else None,
            "last_event": logs[-1].created_at.isoformat() if logs else None,
        }


from datetime import timedelta  # Add missing import
