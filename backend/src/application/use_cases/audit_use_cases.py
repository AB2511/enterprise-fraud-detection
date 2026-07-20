"""Audit Use Cases (CQRS Pattern)."""

from datetime import datetime
from uuid import UUID

from src.application.dtos.audit_dtos import (
    AuditLogListRequest,
    AuditLogResponse,
    AuditStatisticsResponse,
    AuditTrailResponse,
    ComplianceReportRequest,
    CreateAuditLogRequest,
)
from src.application.dtos.common import PageRequest, PageResponse
from src.application.services.audit_service import AuditService
from src.domain.entities.audit_log import AuditLog


class CreateAuditLogUseCase:
    """Use case for creating a new audit log entry."""

    def __init__(self, audit_service: AuditService) -> None:
        """Initialize use case.

        Args:
            audit_service: Audit service instance
        """
        self._service = audit_service

    async def execute(
        self,
        request: CreateAuditLogRequest,
        created_by: UUID | None = None,
    ) -> AuditLogResponse:
        """Execute create audit log use case.

        Args:
            request: Create audit log request DTO
            created_by: User creating the audit log (usually system)

        Returns:
            Audit log response DTO

        Raises:
            ValidationException: If validation fails
        """
        audit_log = await self._service.create_audit_log(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            action=request.action,
            user_id=request.user_id,
            username=request.username,
            old_value=request.old_value,
            new_value=request.new_value,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            description=request.description,
            created_by=created_by,
        )

        return self._to_response(audit_log)

    @staticmethod
    def _to_response(audit_log: AuditLog) -> AuditLogResponse:
        """Convert domain entity to response DTO."""
        return AuditLogResponse(
            audit_id=audit_log.audit_id,
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
            created_at=audit_log.created_at,
        )


class GetAuditLogUseCase:
    """Use case for retrieving an audit log entry."""

    def __init__(self, audit_service: AuditService) -> None:
        """Initialize use case.

        Args:
            audit_service: Audit service instance
        """
        self._service = audit_service

    async def execute(self, audit_id: UUID) -> AuditLogResponse:
        """Execute get audit log use case.

        Args:
            audit_id: Audit log UUID

        Returns:
            Audit log response DTO

        Raises:
            EntityNotFoundException: If audit log not found
        """
        audit_log = await self._service.get_audit_log_by_id(audit_id)
        return CreateAuditLogUseCase._to_response(audit_log)


class ListAuditLogsUseCase:
    """Use case for listing audit logs."""

    def __init__(self, audit_service: AuditService) -> None:
        """Initialize use case.

        Args:
            audit_service: Audit service instance
        """
        self._service = audit_service

    async def execute(
        self,
        request: AuditLogListRequest,
        page_request: PageRequest,
    ) -> PageResponse[AuditLogResponse]:
        """Execute list audit logs use case.

        Args:
            request: Audit log list request with filters
            page_request: Pagination parameters

        Returns:
            Paginated audit log responses
        """
        # Build search criteria
        criteria = {}
        if request.entity_type:
            criteria["entity_type"] = request.entity_type
        if request.entity_id:
            criteria["entity_id"] = request.entity_id
        if request.action:
            criteria["action"] = request.action
        if request.user_id:
            criteria["user_id"] = request.user_id
        if request.username:
            criteria["username"] = request.username
        if request.start_date:
            criteria["start_date"] = request.start_date
        if request.end_date:
            criteria["end_date"] = request.end_date

        audit_logs, total = await self._service.search_audit_logs(
            criteria=criteria,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        audit_log_responses = [CreateAuditLogUseCase._to_response(log) for log in audit_logs]

        return PageResponse.create(
            items=audit_log_responses,
            total=total,
            page_request=page_request,
        )


class GetEntityAuditTrailUseCase:
    """Use case for getting complete audit trail for an entity."""

    def __init__(self, audit_service: AuditService) -> None:
        """Initialize use case.

        Args:
            audit_service: Audit service instance
        """
        self._service = audit_service

    async def execute(
        self,
        entity_type: str,
        entity_id: UUID,
        page_request: PageRequest | None = None,
    ) -> AuditTrailResponse:
        """Execute get entity audit trail use case.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID
            page_request: Optional pagination parameters

        Returns:
            Complete audit trail for the entity
        """
        if page_request is None:
            page_request = PageRequest(page=1, page_size=1000)

        audit_trail = await self._service.get_entity_audit_trail(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        audit_entry_responses = [
            CreateAuditLogUseCase._to_response(log) for log in audit_trail["audit_entries"]
        ]

        return AuditTrailResponse(
            entity_type=entity_type,
            entity_id=entity_id,
            audit_entries=audit_entry_responses,
            total_entries=audit_trail["total_entries"],
            first_entry_date=audit_trail["first_entry_date"],
            last_entry_date=audit_trail["last_entry_date"],
            unique_users=audit_trail["unique_users"],
        )


class GetUserActivityUseCase:
    """Use case for getting user activity audit logs."""

    def __init__(self, audit_service: AuditService) -> None:
        """Initialize use case.

        Args:
            audit_service: Audit service instance
        """
        self._service = audit_service

    async def execute(
        self,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page_request: PageRequest | None = None,
    ) -> PageResponse[AuditLogResponse]:
        """Execute get user activity use case.

        Args:
            user_id: User UUID
            start_date: Optional activity start date
            end_date: Optional activity end date
            page_request: Pagination parameters

        Returns:
            Paginated user audit log responses
        """
        if page_request is None:
            page_request = PageRequest(page=1, page_size=100)

        audit_logs, total = await self._service.get_user_activity(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        audit_log_responses = [CreateAuditLogUseCase._to_response(log) for log in audit_logs]

        return PageResponse.create(
            items=audit_log_responses,
            total=total,
            page_request=page_request,
        )


class GetAuditStatisticsUseCase:
    """Use case for getting audit statistics."""

    def __init__(self, audit_service: AuditService) -> None:
        """Initialize use case.

        Args:
            audit_service: Audit service instance
        """
        self._service = audit_service

    async def execute(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AuditStatisticsResponse:
        """Execute get audit statistics use case.

        Args:
            start_date: Optional analysis start date
            end_date: Optional analysis end date

        Returns:
            Audit statistics response DTO
        """
        stats = await self._service.get_audit_statistics(
            start_date=start_date,
            end_date=end_date,
        )

        return AuditStatisticsResponse(
            total_entries=stats["total_entries"],
            entries_by_entity_type=stats["entries_by_entity_type"],
            entries_by_action=stats["entries_by_action"],
            entries_by_user=stats["entries_by_user"],
            daily_activity=stats["daily_activity"],
            most_active_users=stats["most_active_users"],
            most_modified_entities=stats["most_modified_entities"],
            analysis_period_start=stats["analysis_period_start"],
            analysis_period_end=stats["analysis_period_end"],
        )


class ExportAuditLogsUseCase:
    """Use case for exporting audit logs."""

    def __init__(self, audit_service: AuditService) -> None:
        """Initialize use case.

        Args:
            audit_service: Audit service instance
        """
        self._service = audit_service

    async def execute(
        self,
        request: AuditLogListRequest,
        export_format: str = "csv",
        exported_by: UUID | None = None,
    ) -> dict[str, any]:
        """Execute export audit logs use case.

        Args:
            request: Audit log list request with filters
            export_format: Export format (csv, json, xlsx)
            exported_by: User performing the export

        Returns:
            Export result with file path or data

        Raises:
            ValidationException: If export format not supported
        """
        # Build search criteria
        criteria = {}
        if request.entity_type:
            criteria["entity_type"] = request.entity_type
        if request.entity_id:
            criteria["entity_id"] = request.entity_id
        if request.action:
            criteria["action"] = request.action
        if request.user_id:
            criteria["user_id"] = request.user_id
        if request.username:
            criteria["username"] = request.username
        if request.start_date:
            criteria["start_date"] = request.start_date
        if request.end_date:
            criteria["end_date"] = request.end_date

        export_result = await self._service.export_audit_logs(
            criteria=criteria,
            export_format=export_format,
            exported_by=exported_by,
        )

        return export_result


class GenerateComplianceReportUseCase:
    """Use case for generating compliance reports."""

    def __init__(self, audit_service: AuditService) -> None:
        """Initialize use case.

        Args:
            audit_service: Audit service instance
        """
        self._service = audit_service

    async def execute(
        self,
        request: ComplianceReportRequest,
        generated_by: UUID | None = None,
    ) -> dict[str, any]:
        """Execute generate compliance report use case.

        Args:
            request: Compliance report request with parameters
            generated_by: User generating the report

        Returns:
            Compliance report data

        Raises:
            ValidationException: If report parameters invalid
        """
        report_data = await self._service.generate_compliance_report(
            report_type=request.report_type,
            entity_types=request.entity_types,
            start_date=request.start_date,
            end_date=request.end_date,
            user_filter=request.user_filter,
            include_system_actions=request.include_system_actions,
            generated_by=generated_by,
        )

        return report_data


class SearchAuditByActionUseCase:
    """Use case for searching audit logs by specific action."""

    def __init__(self, audit_service: AuditService) -> None:
        """Initialize use case.

        Args:
            audit_service: Audit service instance
        """
        self._service = audit_service

    async def execute(
        self,
        action: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page_request: PageRequest | None = None,
    ) -> PageResponse[AuditLogResponse]:
        """Execute search audit by action use case.

        Args:
            action: Action to search for
            start_date: Optional search start date
            end_date: Optional search end date
            page_request: Pagination parameters

        Returns:
            Paginated audit log responses matching the action
        """
        if page_request is None:
            page_request = PageRequest(page=1, page_size=100)

        audit_logs, total = await self._service.search_by_action(
            action=action,
            start_date=start_date,
            end_date=end_date,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        audit_log_responses = [CreateAuditLogUseCase._to_response(log) for log in audit_logs]

        return PageResponse.create(
            items=audit_log_responses,
            total=total,
            page_request=page_request,
        )


class GetRecentUserActivityUseCase:
    """Use case for getting recent user activity across all entities."""

    def __init__(self, audit_service: AuditService) -> None:
        """Initialize use case.

        Args:
            audit_service: Audit service instance
        """
        self._service = audit_service

    async def execute(
        self,
        hours: int = 24,
        page_request: PageRequest | None = None,
    ) -> PageResponse[AuditLogResponse]:
        """Execute get recent user activity use case.

        Args:
            hours: Number of hours to look back
            page_request: Pagination parameters

        Returns:
            Paginated recent audit log responses
        """
        if page_request is None:
            page_request = PageRequest(page=1, page_size=100)

        audit_logs, total = await self._service.get_recent_activity(
            hours=hours,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        audit_log_responses = [CreateAuditLogUseCase._to_response(log) for log in audit_logs]

        return PageResponse.create(
            items=audit_log_responses,
            total=total,
            page_request=page_request,
        )


class ValidateAuditIntegrityUseCase:
    """Use case for validating audit log integrity."""

    def __init__(self, audit_service: AuditService) -> None:
        """Initialize use case.

        Args:
            audit_service: Audit service instance
        """
        self._service = audit_service

    async def execute(
        self,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, any]:
        """Execute validate audit integrity use case.

        Args:
            entity_type: Optional entity type filter
            entity_id: Optional entity ID filter
            start_date: Optional validation start date
            end_date: Optional validation end date

        Returns:
            Audit integrity validation results
        """
        validation_results = await self._service.validate_audit_integrity(
            entity_type=entity_type,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
        )

        return validation_results
