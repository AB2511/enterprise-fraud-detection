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
            prioritized.append(
                {
                    **sla_info,
                    "alert_type": alert.alert_type,
                    "transaction_id": str(alert.transaction_id),
                    "assigned_to": (
                        str(alert.assigned_analyst_id) if alert.assigned_analyst_id else None
                    ),
                }
            )

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
        critical_count = sum(
            1 for a in assigned_alerts if a.severity == "critical" and not a.is_resolved()
        )
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

    async def get_alert_by_id(
        self,
        alert_id: UUID,
    ) -> Alert | None:
        """Get alert by ID.

        Args:
            alert_id: Alert UUID

        Returns:
            Alert if found, None otherwise
        """
        return await self._alert_repo.get_by_id(alert_id)

    async def update_alert(
        self,
        alert_id: UUID,
        updates: dict,
        user_id: UUID | None = None,
    ) -> Alert:
        """Update alert information.

        Args:
            alert_id: Alert UUID
            updates: Dictionary of fields to update
            user_id: User performing update

        Returns:
            Updated alert

        Raises:
            ValueError: If alert not found
        """
        alert = await self._alert_repo.get_by_id(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Store old values
        old_values = {
            "status": alert.status,
            "severity": alert.severity,
        }

        # Apply updates (limited to safe fields)
        if "status" in updates:
            # Status changes should use specific methods (assign, close, escalate)
            # But we allow direct update for flexibility
            alert.status = updates["status"]

        if "severity" in updates:
            alert.severity = updates["severity"]

        # Persist
        updated_alert = await self._alert_repo.update(alert)

        # Audit
        new_values = {
            "status": alert.status,
            "severity": alert.severity,
        }

        audit = AuditLog.for_update(
            entity_type="alert",
            entity_id=alert_id,
            user_id=user_id,
            username="system",
            old_value=old_values,
            new_value=new_values,
        )
        await self._audit_repo.create(audit)

        return updated_alert

    async def search_alerts(
        self,
        criteria: dict,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Alert], int]:
        """Search alerts with multiple criteria.

        Args:
            criteria: Search criteria (status, severity, assigned_analyst_id, etc.)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (list of alerts, total count)
        """
        alerts = []

        # Filter by status
        if "status" in criteria:
            alerts = await self._alert_repo.list_by_status(
                status=criteria["status"],
                limit=limit,
                offset=offset,
            )
        # Filter by severity
        elif "severity" in criteria:
            alerts = await self._alert_repo.list_by_severity(
                severity=criteria["severity"],
                limit=limit,
                offset=offset,
            )
        # Filter by analyst
        elif "assigned_analyst_id" in criteria:
            alerts = await self._alert_repo.list_by_analyst(
                analyst_id=criteria["assigned_analyst_id"],
                limit=limit,
                offset=offset,
            )
        # Get unassigned
        elif criteria.get("unassigned"):
            alerts = await self._alert_repo.list_unassigned(
                limit=limit,
                offset=offset,
            )
        # Get SLA breached
        elif criteria.get("is_sla_breached"):
            alerts = await self._alert_repo.list_sla_breached(limit=limit)
        else:
            # Default to open alerts
            alerts = await self._alert_repo.list_by_status(
                status="open",
                limit=limit,
                offset=offset,
            )

        # TODO: Implement actual count - for now return len(alerts)
        total = len(alerts)

        return alerts, total

    async def resolve_alert(
        self,
        alert_id: UUID,
        resolution: str,
        is_fraud: bool,
        confidence: float,
        notes: str | None = None,
        resolved_by: UUID | None = None,
    ) -> Alert:
        """Resolve an alert with decision.

        Args:
            alert_id: Alert UUID
            resolution: Resolution type (confirmed_fraud, false_positive, etc.)
            is_fraud: Whether transaction is fraudulent
            confidence: Confidence in decision (0.0-1.0)
            notes: Optional resolution notes
            resolved_by: User resolving the alert

        Returns:
            Resolved alert

        Raises:
            ValueError: If alert not found
        """
        alert = await self._alert_repo.get_by_id(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Resolve using domain method
        alert.resolve(
            resolution=resolution, resolved_by_id=resolved_by or alert.assigned_analyst_id
        )

        # Persist
        updated_alert = await self._alert_repo.update(alert)

        # Audit
        audit = AuditLog.for_update(
            entity_type="alert",
            entity_id=alert_id,
            user_id=resolved_by,
            username="analyst",
            old_value={"status": "in_review"},
            new_value={
                "status": resolution,
                "is_fraud": is_fraud,
                "confidence": confidence,
                "notes": notes,
            },
        )
        await self._audit_repo.create(audit)

        return updated_alert

    async def get_alert_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Get alert statistics.

        Args:
            start_date: Optional analysis start date
            end_date: Optional analysis end date

        Returns:
            Dictionary with alert statistics
        """
        from datetime import datetime, timedelta

        # Get alerts in range
        if start_date and end_date:
            alerts = await self._alert_repo.get_open_alerts_in_range(
                start_date=start_date,
                end_date=end_date,
            )
        else:
            # Get recent alerts (last 30 days as default)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            alerts = await self._alert_repo.get_open_alerts_in_range(
                start_date=start_date,
                end_date=end_date,
            )

        # Calculate statistics
        total_alerts = len(alerts)
        by_status = {}
        by_severity = {}
        by_type = {}
        sla_breached_count = 0
        total_resolution_time = 0.0
        resolved_count = 0

        for alert in alerts:
            # Count by status
            by_status[alert.status] = by_status.get(alert.status, 0) + 1

            # Count by severity
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1

            # Count by type
            by_type[alert.alert_type] = by_type.get(alert.alert_type, 0) + 1

            # Count SLA breaches
            if alert.check_sla_breach():
                sla_breached_count += 1

            # Calculate resolution time
            if alert.is_resolved() and alert.time_to_resolution_hours:
                total_resolution_time += alert.time_to_resolution_hours
                resolved_count += 1

        avg_resolution_time = total_resolution_time / resolved_count if resolved_count > 0 else 0.0
        sla_breach_rate = sla_breached_count / total_alerts if total_alerts > 0 else 0.0

        open_alerts = by_status.get("open", 0)
        overdue_alerts = sla_breached_count

        return {
            "total_alerts": total_alerts,
            "alerts_by_status": by_status,
            "alerts_by_severity": by_severity,
            "alerts_by_type": by_type,
            "sla_breach_rate": sla_breach_rate,
            "avg_resolution_time_hours": avg_resolution_time,
            "open_alerts": open_alerts,
            "overdue_alerts": overdue_alerts,
            "analysis_period_start": start_date.isoformat() if start_date else None,
            "analysis_period_end": end_date.isoformat() if end_date else None,
        }

    async def get_analyst_alerts(
        self,
        analyst_id: UUID,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Alert], int]:
        """Get alerts assigned to analyst.

        Args:
            analyst_id: Analyst UUID
            status: Optional status filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (list of alerts, total count)
        """
        # Get alerts for analyst
        alerts = await self._alert_repo.list_by_analyst(
            analyst_id=analyst_id,
            limit=limit,
            offset=offset,
        )

        # Filter by status if provided
        if status:
            alerts = [a for a in alerts if a.status == status]

        total = len(alerts)

        return alerts, total

    async def get_overdue_alerts(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Alert], int]:
        """Get overdue (SLA breached) alerts.

        Args:
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (list of alerts, total count)
        """
        alerts = await self._alert_repo.list_sla_breached(limit=limit)

        # Apply offset (since repo doesn't support it)
        alerts = alerts[offset : offset + limit]

        total = len(alerts)

        return alerts, total

    async def get_alert_workflow_status(
        self,
        alert_id: UUID,
    ) -> dict:
        """Get alert workflow status.

        Args:
            alert_id: Alert UUID

        Returns:
            Dictionary with workflow status information

        Raises:
            ValueError: If alert not found
        """
        alert = await self._alert_repo.get_by_id(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Determine workflow stage
        workflow_stage = "created"
        if alert.assigned_analyst_id:
            workflow_stage = "assigned"
        if alert.status == "in_review":
            workflow_stage = "under_review"
        if alert.is_resolved():
            workflow_stage = "resolved"
        if alert.status == "escalated":
            workflow_stage = "escalated"

        # Determine next actions
        next_actions = []
        if alert.status == "open":
            next_actions = ["assign", "escalate"]
        elif alert.status == "in_review":
            next_actions = ["resolve", "escalate"]
        elif alert.status == "escalated":
            next_actions = ["assign", "resolve"]

        # Calculate time in current stage
        from datetime import datetime

        time_in_stage = (datetime.utcnow() - alert.updated_at).total_seconds() / 3600

        return {
            "workflow_stage": workflow_stage,
            "next_actions": next_actions,
            "escalation_path": ["analyst", "senior_analyst", "manager"],
            "required_approvals": [],
            "time_in_current_stage_hours": time_in_stage,
        }

    async def bulk_assign_alerts(
        self,
        alert_ids: list[UUID],
        analyst_id: UUID,
        priority: str | None = None,
        assigned_by: UUID | None = None,
    ) -> list[Alert]:
        """Bulk assign alerts to analyst.

        Args:
            alert_ids: List of alert UUIDs
            analyst_id: Analyst to assign to
            priority: Optional priority level
            assigned_by: User performing bulk assignment

        Returns:
            List of assigned alerts

        Raises:
            ValueError: If analyst invalid or alerts not found
        """
        # Verify analyst exists and has correct role
        analyst = await self._user_repo.get_by_id(analyst_id)
        if not analyst:
            raise ValueError(f"Analyst {analyst_id} not found")

        if not analyst.can_review_alerts():
            raise ValueError(f"User {analyst_id} does not have analyst role")

        # Assign each alert
        assigned_alerts = []
        for alert_id in alert_ids:
            try:
                alert = await self.assign_alert(
                    alert_id=alert_id,
                    analyst_id=analyst_id,
                    user_id=assigned_by,
                )
                assigned_alerts.append(alert)
            except ValueError:
                # Skip alerts that don't exist
                continue

        return assigned_alerts
