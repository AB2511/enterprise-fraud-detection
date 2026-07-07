"""Alert Service - Business workflows for fraud alert management."""

from datetime import datetime
from uuid import UUID

from src.application.interfaces.alert_repository import AlertRepository
from src.application.interfaces.audit_repository import AuditRepository
from src.application.interfaces.user_repository import UserRepository
from src.domain.entities.alert import Alert
from src.domain.entities.audit_log import AuditLog


class AlertService:
    """Service for alert management business workflows.

    This service handles alert creation, assignment, escalation,
    resolution, and SLA tracking.
    """

    def __init__(
        self,
        alert_repository: AlertRepository,
        audit_repository: AuditRepository,
        user_repository: UserRepository,
    ) -> None:
        """Initialize alert service.

        Args:
            alert_repository: Repository for alert persistence
            audit_repository: Repository for audit logging
            user_repository: Repository for user data
        """
        self._alert_repo = alert_repository
        self._audit_repo = audit_repository
        self._user_repo = user_repository

    async def create_alert(
        self,
        transaction_id: UUID,
        prediction_id: UUID,
        alert_type: str,
        severity: str,
        user_id: UUID | None = None,
    ) -> Alert:
        """Create a new fraud alert.

        Args:
            transaction_id: Transaction UUID
            prediction_id: Prediction UUID
            alert_type: Type of alert
            severity: Alert severity (low, medium, high, critical)
            user_id: User creating alert

        Returns:
            Created alert

        Raises:
            ValueError: If validation fails
        """
        # Create alert entity
        alert = Alert(
            transaction_id=transaction_id,
            prediction_id=prediction_id,
            alert_type=alert_type,
            severity=severity,
        )

        # Persist
        created_alert = await self._alert_repo.create(alert)

        # Audit
        audit = AuditLog.for_creation(
            entity_type="alert",
            entity_id=created_alert.alert_id,
            user_id=user_id,
            username="system",
            new_value={
                "transaction_id": str(transaction_id),
                "prediction_id": str(prediction_id),
                "type": alert_type,
                "severity": severity,
                "status": "open",
            },
        )
        await self._audit_repo.create(audit)

        return created_alert

    async def assign_alert(
        self,
        alert_id: UUID,
        analyst_id: UUID,
        user_id: UUID | None = None,
    ) -> Alert:
        """Assign alert to analyst.

        Args:
            alert_id: Alert UUID
            analyst_id: Analyst user UUID
            user_id: User performing assignment

        Returns:
            Updated alert

        Raises:
            NotFoundError: If alert or analyst not found
            ValueError: If analyst role invalid
        """
        alert = await self._alert_repo.get_by_id(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Verify analyst exists and has correct role
        analyst = await self._user_repo.get_by_id(analyst_id)
        if not analyst:
            raise ValueError(f"Analyst {analyst_id} not found")

        if not analyst.can_review_alerts():
            raise ValueError(f"User {analyst_id} does not have analyst role")

        # Assign
        alert.assign_to_analyst(analyst_id)

        # Persist
        updated_alert = await self._alert_repo.update(alert)

        # Audit
        audit = AuditLog.for_update(
            entity_type="alert",
            entity_id=alert_id,
            user_id=user_id,
            username="system",
            old_value={"status": "open", "assigned_to": None},
            new_value={"status": "in_review", "assigned_to": str(analyst_id)},
        )
        await self._audit_repo.create(audit)

        return updated_alert

    async def close_alert(
        self,
        alert_id: UUID,
        resolution: str,
        resolved_by_id: UUID,
        user_id: UUID | None = None,
    ) -> Alert:
        """Close/resolve an alert.

        Args:
            alert_id: Alert UUID
            resolution: Resolution status (resolved, false_positive, confirmed_fraud)
            resolved_by_id: User resolving the alert
            user_id: User performing action

        Returns:
            Updated alert

        Raises:
            NotFoundError: If alert not found
        """
        alert = await self._alert_repo.get_by_id(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Resolve
        alert.resolve(resolution=resolution, resolved_by_id=resolved_by_id)

        # Persist
        updated_alert = await self._alert_repo.update(alert)

        # Audit
        audit = AuditLog.for_update(
            entity_type="alert",
            entity_id=alert_id,
            user_id=user_id,
            username="system",
            old_value={"status": alert.status},
            new_value={
                "status": resolution,
                "resolved_by": str(resolved_by_id),
                "resolved_at": datetime.utcnow().isoformat(),
            },
        )
        await self._audit_repo.create(audit)

        return updated_alert

    async def escalate_alert(
        self,
        alert_id: UUID,
        user_id: UUID | None = None,
    ) -> Alert:
        """Escalate alert to higher severity.

        Args:
            alert_id: Alert UUID
            user_id: User performing escalation

        Returns:
            Updated alert

        Raises:
            NotFoundError: If alert not found
        """
        alert = await self._alert_repo.get_by_id(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        old_severity = alert.severity

        # Escalate
        alert.escalate()

        # Persist
        updated_alert = await self._alert_repo.update(alert)

        # Audit
        audit = AuditLog.for_update(
            entity_type="alert",
            entity_id=alert_id,
            user_id=user_id,
            username="system",
            old_value={"severity": old_severity},
            new_value={"severity": alert.severity, "status": "escalated"},
        )
        await self._audit_repo.create(audit)

        return updated_alert

    async def track_sla(
        self,
        alert_id: UUID,
    ) -> dict:
        """Track SLA status for alert.

        Args:
            alert_id: Alert UUID

        Returns:
            SLA tracking information

        Raises:
            NotFoundError: If alert not found
        """
        alert = await self._alert_repo.get_by_id(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Calculate SLA info
        time_to_breach = alert.time_to_sla_breach()
        is_breached = alert.check_sla_breach()

        return {
            "alert_id": str(alert.alert_id),
            "severity": alert.severity,
            "sla_hours": alert.calculate_sla_hours(),
            "sla_deadline": alert.sla_deadline.isoformat(),
            "time_to_breach_minutes": time_to_breach,
            "is_breached": is_breached,
            "status": alert.status,
            "requires_action": alert.requires_action(),
        }

    async def get_priority_queue(
        self,
        limit: int = 50,
    ) -> list[dict]:
        """Get prioritized alert queue.

        Args:
            limit: Maximum alerts to return

        Returns:
            List of alerts sorted by priority

        Raises:
            None
        """
        # Get open and in-review alerts
        open_alerts = await self._alert_repo.list_by_status(
            status="open",
            limit=limit,
        )
        review_alerts = await self._alert_repo.list_by_status(
            status="in_review",
            limit=limit,
        )

        all_alerts = open_alerts + review_alerts

        # Calculate priority for each
        prioritized = []
        for alert in all_alerts:
            sla_info = await self.track_sla(alert.alert_id)
            prioritized.append({
                **sla_info,
                "alert_type": alert.alert_type,
                "transaction_id": str(alert.transaction_id),
                "assigned_to": str(alert.assigned_analyst_id) if alert.assigned_analyst_id else None,
            })

        # Sort by time to breach (ascending)
        prioritized.sort(key=lambda x: x["time_to_breach_minutes"] or float("inf"))

        return prioritized[:limit]

    async def get_analyst_workload(
        self,
        analyst_id: UUID,
    ) -> dict:
        """Get workload statistics for analyst.

        Args:
            analyst_id: Analyst UUID

        Returns:
            Workload statistics

        Raises:
            NotFoundError: If analyst not found
        """
        # Get assigned alerts
        assigned_alerts = await self._alert_repo.list_by_analyst(
            analyst_id=analyst_id,
            limit=1000,
        )

        # Count by status
        open_count = sum(1 for a in assigned_alerts if a.status == "open")
        review_count = sum(1 for a in assigned_alerts if a.status == "in_review")
        resolved_count = sum(1 for a in assigned_alerts if a.is_resolved())

        # Count by severity
        critical_count = sum(1 for a in assigned_alerts if a.severity == "critical" and not a.is_resolved())
        high_count = sum(1 for a in assigned_alerts if a.severity == "high" and not a.is_resolved())

        return {
            "analyst_id": str(analyst_id),
            "total_assigned": len(assigned_alerts),
            "open": open_count,
            "in_review": review_count,
            "resolved": resolved_count,
            "critical_pending": critical_count,
            "high_pending": high_count,
        }

    async def get_sla_breached_alerts(
        self,
        limit: int = 100,
    ) -> list[Alert]:
        """Get alerts that have breached SLA.

        Args:
            limit: Maximum alerts to return

        Returns:
            List of SLA-breached alerts
        """
        return await self._alert_repo.list_sla_breached(limit=limit)
