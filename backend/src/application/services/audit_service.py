"""Audit Service - Business workflows for audit log management."""

from collections.abc import Mapping
from datetime import datetime, timedelta
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

    async def create_audit_log(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        action: str,
        user_id: UUID | None = None,
        username: str | None = None,
        old_value: dict[str, object] | None = None,
        new_value: dict[str, object] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        description: str | None = None,
        created_by: UUID | None = None,
    ) -> AuditLog:
        """Create a new audit log entry."""
        normalized_action = action.strip().upper()
        audit_log = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=normalized_action,
            user_id=user_id if user_id is not None else created_by,
            username=username,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
        )
        return await self._audit_repo.create(audit_log)

    async def search_audit_logs(
        self,
        criteria: Mapping[str, object] | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        action: str | None = None,
        user_id: UUID | None = None,
        username: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Search audit logs with multiple filters."""
        criteria_map: Mapping[str, object] = criteria if criteria is not None else {}

        if entity_type is None and "entity_type" in criteria_map:
            entity_type = (
                criteria_map["entity_type"]
                if isinstance(criteria_map["entity_type"], str)
                else None
            )
        if entity_id is None and "entity_id" in criteria_map:
            entity_id = (
                criteria_map["entity_id"] if isinstance(criteria_map["entity_id"], UUID) else None
            )
        if action is None and "action" in criteria_map:
            action = criteria_map["action"] if isinstance(criteria_map["action"], str) else None
        if user_id is None and "user_id" in criteria_map:
            user_id = criteria_map["user_id"] if isinstance(criteria_map["user_id"], UUID) else None
        if username is None and "username" in criteria_map:
            username = (
                criteria_map["username"] if isinstance(criteria_map["username"], str) else None
            )
        if start_date is None and "start_date" in criteria_map:
            start_date = (
                criteria_map["start_date"]
                if isinstance(criteria_map["start_date"], datetime)
                else None
            )
        if end_date is None and "end_date" in criteria_map:
            end_date = (
                criteria_map["end_date"] if isinstance(criteria_map["end_date"], datetime) else None
            )

        normalized_action = (
            action.strip().upper() if isinstance(action, str) and action.strip() else None
        )

        logs = await self._audit_repo.search(
            entity_type=entity_type,
            entity_id=entity_id,
            action=normalized_action,
            user_id=user_id,
            username=username,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        return logs, len(logs)

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
                "log_id": str(log.audit_id),
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
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
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

        total = len(filtered_logs)
        paged_logs = filtered_logs[offset : offset + limit]

        return paged_logs, total

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
        by_entity_type: dict[str, int] = {}
        by_action: dict[str, int] = {}
        by_user: dict[str, int] = {}

        for log in logs:
            by_entity_type[log.entity_type] = by_entity_type.get(log.entity_type, 0) + 1
            by_action[log.action] = by_action.get(log.action, 0) + 1
            if log.user_id:
                user_key = str(log.user_id)
                by_user[user_key] = by_user.get(user_key, 0) + 1

        stats: dict[str, object] = {
            "total_events": len(logs),
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "by_entity_type": by_entity_type,
            "by_action": by_action,
            "by_user": by_user,
        }

        # Format logs
        formatted_logs = [
            {
                "log_id": str(log.audit_id),
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
    ) -> dict[str, object]:
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
        by_action: dict[str, int] = {}
        by_entity: dict[str, int] = {}
        by_user: dict[str, int] = {}
        daily_activity: dict[str, int] = {}
        most_modified_entities: dict[tuple[str, UUID], int] = {}

        for log in logs:
            by_action[log.action] = by_action.get(log.action, 0) + 1
            by_entity[log.entity_type] = by_entity.get(log.entity_type, 0) + 1
            if log.user_id:
                user_key = str(log.user_id)
                by_user[user_key] = by_user.get(user_key, 0) + 1

            day_key = log.created_at.date().isoformat()
            daily_activity[day_key] = daily_activity.get(day_key, 0) + 1

            entity_key = (log.entity_type, log.entity_id)
            most_modified_entities[entity_key] = most_modified_entities.get(entity_key, 0) + 1

        most_active_users = [
            {"username": username, "count": count}
            for username, count in sorted(by_user.items(), key=lambda item: item[1], reverse=True)[
                :10
            ]
        ]
        most_modified_entity_list = [
            {
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "count": count,
            }
            for (entity_type, entity_id), count in sorted(
                most_modified_entities.items(), key=lambda item: item[1], reverse=True
            )[:10]
        ]

        return {
            "total_entries": total,
            "entries_by_entity_type": by_entity,
            "entries_by_action": by_action,
            "entries_by_user": by_user,
            "daily_activity": daily_activity,
            "most_active_users": most_active_users,
            "most_modified_entities": most_modified_entity_list,
            "analysis_period_start": start_date or datetime.utcnow() - timedelta(days=30),
            "analysis_period_end": end_date or datetime.utcnow(),
        }

    async def validate_audit_integrity(
        self,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, object]:
        """Validate audit trail integrity for an entity."""
        logs = await self._audit_repo.search(
            entity_type=entity_type,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
            limit=1000,
        )

        is_chronological = all(
            logs[i].created_at <= logs[i + 1].created_at for i in range(len(logs) - 1)
        )
        has_creation = any(log.action == "CREATE" for log in logs)

        return {
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id else None,
            "total_events": len(logs),
            "is_chronological": is_chronological,
            "has_creation_event": has_creation,
            "first_event": logs[0].created_at.isoformat() if logs else None,
            "last_event": logs[-1].created_at.isoformat() if logs else None,
        }

    async def get_audit_log_by_id(
        self,
        audit_id: UUID,
    ) -> AuditLog | None:
        """Get audit log by ID.

        Args:
            audit_id: Audit log UUID

        Returns:
            Audit log if found, None otherwise
        """
        return await self._audit_repo.get_by_id(audit_id)

    async def get_entity_audit_trail(
        self,
        entity_type: str,
        entity_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """Get complete audit trail for an entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID
            limit: Maximum records
            offset: Pagination offset

        Returns:
            Complete audit trail with metadata
        """
        # Get audit logs
        logs = await self._audit_repo.list_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
            offset=offset,
        )

        # Get total count
        total_count = await self._audit_repo.count_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
        )

        # Get unique users
        unique_users = set()
        for log in logs:
            if log.user_id:
                unique_users.add(str(log.user_id))

        return {
            "audit_entries": logs,
            "total_entries": total_count,
            "first_entry_date": logs[0].created_at.isoformat() if logs else None,
            "last_entry_date": logs[-1].created_at.isoformat() if logs else None,
            "unique_users": list(unique_users),
        }

    async def export_audit_logs(
        self,
        criteria: Mapping[str, object],
        export_format: str = "json",
        exported_by: UUID | None = None,
    ) -> dict:
        """Export audit logs in specified format.

        Args:
            criteria: Search criteria
            export_format: Export format (json, csv, xlsx)
            exported_by: User performing export

        Returns:
            Export result with data

        Raises:
            ValueError: If export format not supported
        """
        if export_format not in ["json", "csv", "xlsx"]:
            raise ValueError(f"Unsupported export format: {export_format}")

        # Search logs
        logs, _ = await self.search_audit_logs(
            criteria=criteria,
            limit=10000,  # Large limit for export
            offset=0,
        )

        # Format logs
        formatted_logs = [
            {
                "log_id": str(log.audit_id),
                "timestamp": log.created_at.isoformat(),
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id),
                "action": log.action,
                "user_id": str(log.user_id) if log.user_id else None,
                "username": log.username,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "ip_address": log.ip_address,
                "description": log.description,
            }
            for log in logs
        ]

        return {
            "export_format": export_format,
            "total_records": len(formatted_logs),
            "exported_at": datetime.utcnow().isoformat(),
            "exported_by": str(exported_by) if exported_by else None,
            "data": formatted_logs,
        }

    async def generate_compliance_report(
        self,
        report_type: str,
        entity_types: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_filter: str | None = None,
        include_system_actions: bool = True,
        generated_by: UUID | None = None,
    ) -> dict:
        """Generate compliance report.

        Args:
            report_type: Type of compliance report
            entity_types: Filter by entity types
            start_date: Report start date
            end_date: Report end date
            user_filter: Filter by specific user
            include_system_actions: Include system-generated actions
            generated_by: User generating report

        Returns:
            Compliance report data
        """
        # Use export_compliance_report as base
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        report = await self.export_compliance_report(
            start_date=start_date,
            end_date=end_date,
            entity_types=entity_types,
        )

        # Add report metadata
        report["report_type"] = report_type
        report["generated_by"] = str(generated_by) if generated_by else None
        report["include_system_actions"] = include_system_actions

        # Filter by user if specified
        if user_filter:
            report["audit_logs"] = [
                log for log in report["audit_logs"] if log["username"] == user_filter
            ]

        # Filter out system actions if requested
        if not include_system_actions:
            report["audit_logs"] = [
                log for log in report["audit_logs"] if log["username"] != "system"
            ]

        return report

    async def search_by_action(
        self,
        action: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Search audit logs by action.

        Args:
            action: Action type to search for
            start_date: Optional start date
            end_date: Optional end date
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (list of audit logs, total count)
        """
        # Use repository list_by_action
        logs = await self._audit_repo.list_by_action(
            action=action,
            limit=limit,
            offset=offset,
        )

        # Filter by date if provided
        if start_date or end_date:
            filtered_logs = []
            for log in logs:
                if start_date and log.created_at < start_date:
                    continue
                if end_date and log.created_at > end_date:
                    continue
                filtered_logs.append(log)
            logs = filtered_logs

        total = len(logs)

        return logs, total

    async def get_recent_activity(
        self,
        hours: int = 24,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Get recent audit activity.

        Args:
            hours: Number of hours to look back
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (list of audit logs, total count)
        """
        from datetime import timedelta

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=hours)

        logs = await self._audit_repo.list_by_date_range(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        total = len(logs)

        return logs, total
