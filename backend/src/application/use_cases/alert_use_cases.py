"""Alert Use Cases (CQRS Pattern)."""

from uuid import UUID

from src.application.dtos.alert_dtos import (
    AlertListRequest,
    AlertResponse,
    AlertStatisticsResponse,
    AlertWorkflowResponse,
    AssignAlertRequest,
    CreateAlertRequest,
    ResolveAlertRequest,
    UpdateAlertRequest,
)
from src.application.dtos.common import PageRequest, PageResponse
from src.application.services.alert_service import AlertService
from src.domain.entities.alert import Alert


class CreateAlertUseCase:
    """Use case for creating a new alert."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(
        self,
        request: CreateAlertRequest,
        user_id: UUID | None = None,
    ) -> AlertResponse:
        """Execute create alert use case.

        Args:
            request: Create alert request DTO
            user_id: User performing the action

        Returns:
            Alert response DTO

        Raises:
            ValidationException: If validation fails
            EntityNotFoundException: If transaction or prediction not found
        """
        alert = await self._service.create_alert(
            transaction_id=request.transaction_id,
            prediction_id=request.prediction_id,
            alert_type=request.alert_type,
            severity=request.severity,
            sla_hours=request.sla_hours,
            user_id=user_id,
        )

        return self._to_response(alert)

    @staticmethod
    def _to_response(alert: Alert) -> AlertResponse:
        """Convert domain entity to response DTO."""
        return AlertResponse(
            alert_id=alert.alert_id,
            transaction_id=alert.transaction_id,
            prediction_id=alert.prediction_id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            status=alert.status,
            assigned_analyst_id=alert.assigned_analyst_id,
            assigned_at=alert.assigned_at,
            resolution=alert.resolution,
            resolved_at=alert.resolved_at,
            resolved_by_id=alert.resolved_by_id,
            sla_deadline=alert.sla_deadline,
            is_sla_breached=alert.is_sla_breached,
            time_to_resolution_hours=alert.time_to_resolution_hours,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
        )


class UpdateAlertUseCase:
    """Use case for updating an alert."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(
        self,
        alert_id: UUID,
        request: UpdateAlertRequest,
        user_id: UUID | None = None,
    ) -> AlertResponse:
        """Execute update alert use case.

        Args:
            alert_id: Alert UUID
            request: Update alert request DTO
            user_id: User performing the action

        Returns:
            Alert response DTO

        Raises:
            EntityNotFoundException: If alert not found
            ValidationException: If validation fails
        """
        # Build updates dictionary
        updates = {}
        if request.status is not None:
            updates["status"] = request.status
        if request.assigned_analyst_id is not None:
            updates["assigned_analyst_id"] = request.assigned_analyst_id
        if request.resolution is not None:
            updates["resolution"] = request.resolution

        alert = await self._service.update_alert(
            alert_id=alert_id,
            updates=updates,
            user_id=user_id,
        )

        return CreateAlertUseCase._to_response(alert)


class GetAlertUseCase:
    """Use case for retrieving an alert."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(self, alert_id: UUID) -> AlertResponse:
        """Execute get alert use case.

        Args:
            alert_id: Alert UUID

        Returns:
            Alert response DTO

        Raises:
            EntityNotFoundException: If alert not found
        """
        alert = await self._service.get_alert_by_id(alert_id)
        return CreateAlertUseCase._to_response(alert)


class ListAlertsUseCase:
    """Use case for listing alerts."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(
        self,
        request: AlertListRequest,
        page_request: PageRequest,
    ) -> PageResponse[AlertResponse]:
        """Execute list alerts use case.

        Args:
            request: Alert list request with filters
            page_request: Pagination parameters

        Returns:
            Paginated alert responses
        """
        # Build search criteria
        criteria = {}
        if request.status:
            criteria["status"] = request.status
        if request.severity:
            criteria["severity"] = request.severity
        if request.alert_type:
            criteria["alert_type"] = request.alert_type
        if request.assigned_analyst_id:
            criteria["assigned_analyst_id"] = request.assigned_analyst_id
        if request.is_sla_breached is not None:
            criteria["is_sla_breached"] = request.is_sla_breached
        if request.start_date:
            criteria["start_date"] = request.start_date
        if request.end_date:
            criteria["end_date"] = request.end_date

        alerts, total = await self._service.search_alerts(
            criteria=criteria,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        alert_responses = [CreateAlertUseCase._to_response(a) for a in alerts]

        return PageResponse.create(
            items=alert_responses,
            total=total,
            page_request=page_request,
        )


class AssignAlertUseCase:
    """Use case for assigning an alert to an analyst."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(
        self,
        alert_id: UUID,
        request: AssignAlertRequest,
        user_id: UUID | None = None,
    ) -> AlertResponse:
        """Execute assign alert use case.

        Args:
            alert_id: Alert UUID
            request: Assignment request with analyst and priority
            user_id: User performing the action

        Returns:
            Alert response DTO

        Raises:
            EntityNotFoundException: If alert or analyst not found
            ValidationException: If validation fails
        """
        alert = await self._service.assign_alert(
            alert_id=alert_id,
            analyst_id=request.analyst_id,
            priority=request.priority,
            notes=request.notes,
            assigned_by=user_id,
        )

        return CreateAlertUseCase._to_response(alert)


class ResolveAlertUseCase:
    """Use case for resolving an alert."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(
        self,
        alert_id: UUID,
        request: ResolveAlertRequest,
        user_id: UUID | None = None,
    ) -> AlertResponse:
        """Execute resolve alert use case.

        Args:
            alert_id: Alert UUID
            request: Resolution request with details
            user_id: User performing the action

        Returns:
            Alert response DTO

        Raises:
            EntityNotFoundException: If alert not found
            ValidationException: If validation fails
        """
        alert = await self._service.resolve_alert(
            alert_id=alert_id,
            resolution=request.resolution,
            is_fraud=request.is_fraud,
            confidence=request.confidence,
            notes=request.notes,
            resolved_by=user_id,
        )

        return CreateAlertUseCase._to_response(alert)


class EscalateAlertUseCase:
    """Use case for escalating an alert."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(
        self,
        alert_id: UUID,
        escalation_reason: str,
        escalated_by: UUID,
        escalated_to: UUID | None = None,
    ) -> AlertResponse:
        """Execute escalate alert use case.

        Args:
            alert_id: Alert UUID
            escalation_reason: Reason for escalation
            escalated_by: User escalating the alert
            escalated_to: User to escalate to (optional, system will auto-assign)

        Returns:
            Alert response DTO

        Raises:
            EntityNotFoundException: If alert not found
        """
        alert = await self._service.escalate_alert(
            alert_id=alert_id,
            escalation_reason=escalation_reason,
            escalated_by=escalated_by,
            escalated_to=escalated_to,
        )

        return CreateAlertUseCase._to_response(alert)


class CloseAlertUseCase:
    """Use case for closing an alert."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(
        self,
        alert_id: UUID,
        closure_reason: str,
        closed_by: UUID,
    ) -> AlertResponse:
        """Execute close alert use case.

        Args:
            alert_id: Alert UUID
            closure_reason: Reason for closure
            closed_by: User closing the alert

        Returns:
            Alert response DTO

        Raises:
            EntityNotFoundException: If alert not found
        """
        alert = await self._service.close_alert(
            alert_id=alert_id,
            closure_reason=closure_reason,
            closed_by=closed_by,
        )

        return CreateAlertUseCase._to_response(alert)


class GetAlertStatisticsUseCase:
    """Use case for getting alert statistics."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(
        self,
        start_date: None = None,
        end_date: None = None,
    ) -> AlertStatisticsResponse:
        """Execute get alert statistics use case.

        Args:
            start_date: Optional analysis start date
            end_date: Optional analysis end date

        Returns:
            Alert statistics response DTO
        """
        stats = await self._service.get_alert_statistics(
            start_date=start_date,
            end_date=end_date,
        )

        return AlertStatisticsResponse(
            total_alerts=stats["total_alerts"],
            alerts_by_status=stats["alerts_by_status"],
            alerts_by_severity=stats["alerts_by_severity"],
            alerts_by_type=stats["alerts_by_type"],
            sla_breach_rate=stats["sla_breach_rate"],
            avg_resolution_time_hours=stats["avg_resolution_time_hours"],
            open_alerts=stats["open_alerts"],
            overdue_alerts=stats["overdue_alerts"],
            analysis_period_start=stats["analysis_period_start"],
            analysis_period_end=stats["analysis_period_end"],
        )


class GetMyAlertsUseCase:
    """Use case for getting alerts assigned to a specific analyst."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(
        self,
        analyst_id: UUID,
        status: str | None = None,
        page_request: PageRequest | None = None,
    ) -> PageResponse[AlertResponse]:
        """Execute get my alerts use case.

        Args:
            analyst_id: Analyst UUID
            status: Optional status filter
            page_request: Pagination parameters

        Returns:
            Paginated alert responses assigned to the analyst
        """
        if page_request is None:
            page_request = PageRequest(page=1, page_size=50)

        alerts, total = await self._service.get_analyst_alerts(
            analyst_id=analyst_id,
            status=status,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        alert_responses = [CreateAlertUseCase._to_response(a) for a in alerts]

        return PageResponse.create(
            items=alert_responses,
            total=total,
            page_request=page_request,
        )


class GetOverdueAlertsUseCase:
    """Use case for getting overdue alerts."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(
        self,
        page_request: PageRequest | None = None,
    ) -> PageResponse[AlertResponse]:
        """Execute get overdue alerts use case.

        Args:
            page_request: Pagination parameters

        Returns:
            Paginated overdue alert responses
        """
        if page_request is None:
            page_request = PageRequest(page=1, page_size=100)

        alerts, total = await self._service.get_overdue_alerts(
            limit=page_request.limit,
            offset=page_request.offset,
        )

        alert_responses = [CreateAlertUseCase._to_response(a) for a in alerts]

        return PageResponse.create(
            items=alert_responses,
            total=total,
            page_request=page_request,
        )


class GetAlertWorkflowStatusUseCase:
    """Use case for getting alert workflow status."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(self, alert_id: UUID) -> AlertWorkflowResponse:
        """Execute get alert workflow status use case.

        Args:
            alert_id: Alert UUID

        Returns:
            Alert workflow response DTO

        Raises:
            EntityNotFoundException: If alert not found
        """
        workflow_status = await self._service.get_alert_workflow_status(alert_id)

        return AlertWorkflowResponse(
            alert_id=alert_id,
            workflow_stage=workflow_status["workflow_stage"],
            next_actions=workflow_status["next_actions"],
            escalation_path=workflow_status["escalation_path"],
            required_approvals=workflow_status["required_approvals"],
            time_in_current_stage_hours=workflow_status["time_in_current_stage_hours"],
        )


class BulkAssignAlertsUseCase:
    """Use case for bulk assigning alerts."""

    def __init__(self, alert_service: AlertService) -> None:
        """Initialize use case.

        Args:
            alert_service: Alert service instance
        """
        self._service = alert_service

    async def execute(
        self,
        alert_ids: list[UUID],
        analyst_id: UUID,
        priority: str | None = None,
        assigned_by: UUID | None = None,
    ) -> list[AlertResponse]:
        """Execute bulk assign alerts use case.

        Args:
            alert_ids: List of alert UUIDs to assign
            analyst_id: Analyst UUID to assign to
            priority: Optional priority level
            assigned_by: User performing the bulk assignment

        Returns:
            List of updated alert responses

        Raises:
            ValidationException: If any alert assignment fails
        """
        alerts = await self._service.bulk_assign_alerts(
            alert_ids=alert_ids,
            analyst_id=analyst_id,
            priority=priority,
            assigned_by=assigned_by,
        )

        return [CreateAlertUseCase._to_response(a) for a in alerts]
