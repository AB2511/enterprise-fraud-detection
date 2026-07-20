"""Audit API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.application.dtos.audit_dtos import (
    AuditLogListRequest,
    AuditLogResponse,
    CreateAuditLogRequest,
)
from src.application.dtos.common import PageRequest
from src.application.use_cases.audit_use_cases import (
    CreateAuditLogUseCase,
    GetAuditLogUseCase,
    ListAuditLogsUseCase,
)
from src.config.logging_config import get_logger
from src.domain.entities.user import User
from src.infrastructure.security.authorization import require_admin
from src.presentation.api.dependencies import (
    get_create_audit_log_use_case,
    get_get_audit_log_use_case,
    get_list_audit_logs_use_case,
)
from src.presentation.api.response import APIResponse, success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post(
    "",
    response_model=APIResponse[AuditLogResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create an audit log entry",
)
async def create_audit_log(
    request: CreateAuditLogRequest,
    current_user: Annotated[User, Depends(require_admin)],
    use_case: CreateAuditLogUseCase = Depends(get_create_audit_log_use_case),
) -> APIResponse[AuditLogResponse]:
    """Create an audit log entry."""
    audit_log = await use_case.execute(request)
    return success_response(data=audit_log, message="Audit log created successfully")


@router.get(
    "/{audit_id}",
    response_model=APIResponse[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get audit log by ID",
)
async def get_audit_log(
    audit_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    use_case: GetAuditLogUseCase = Depends(get_get_audit_log_use_case),
) -> APIResponse[AuditLogResponse]:
    """Retrieve an audit log entry by identifier."""
    audit_log = await use_case.execute(audit_id)
    return success_response(data=audit_log, message="Audit log retrieved successfully")


@router.get(
    "",
    response_model=APIResponse[list[AuditLogResponse]],
    status_code=status.HTTP_200_OK,
    summary="List audit logs",
)
async def list_audit_logs(
    current_user: Annotated[User, Depends(require_admin)],
    entity_type: str | None = Query(default=None),
    entity_id: UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    user_id: UUID | None = Query(default=None),
    username: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=1000),
    use_case: ListAuditLogsUseCase = Depends(get_list_audit_logs_use_case),
) -> APIResponse[list[AuditLogResponse]]:
    """List audit logs with optional filters."""
    request = AuditLogListRequest(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        username=username,
    )
    page_request = PageRequest(page=page, page_size=page_size)
    result = await use_case.execute(request, page_request)
    return success_response(data=result.items, message="Audit logs retrieved successfully")
