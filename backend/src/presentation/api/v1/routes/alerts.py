"""Alert API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.application.dtos.alert_dtos import (
    AlertListRequest,
    AlertResponse,
    AssignAlertRequest,
    CreateAlertRequest,
    ResolveAlertRequest,
    UpdateAlertRequest,
)
from src.application.dtos.common import PageRequest
from src.application.use_cases.alert_use_cases import (
    AssignAlertUseCase,
    CreateAlertUseCase,
    GetAlertUseCase,
    ListAlertsUseCase,
    ResolveAlertUseCase,
    UpdateAlertUseCase,
)
from src.config.logging_config import get_logger
from src.domain.entities.user import User
from src.infrastructure.security.authorization import require_analyst
from src.presentation.api.dependencies import (
    get_assign_alert_use_case,
    get_create_alert_use_case,
    get_get_alert_use_case,
    get_list_alerts_use_case,
    get_resolve_alert_use_case,
    get_update_alert_use_case,
)
from src.presentation.api.response import APIResponse, success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post(
    "",
    response_model=APIResponse[AlertResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create an alert",
)
async def create_alert(
    request: CreateAlertRequest,
    current_user: Annotated[User, Depends(require_analyst)],
    use_case: CreateAlertUseCase = Depends(get_create_alert_use_case),
) -> APIResponse[AlertResponse]:
    """Create an alert."""
    alert = await use_case.execute(request)
    return success_response(data=alert, message="Alert created successfully")


@router.get(
    "/{alert_id}",
    response_model=APIResponse[AlertResponse],
    status_code=status.HTTP_200_OK,
    summary="Get alert by ID",
)
async def get_alert(
    alert_id: UUID,
    current_user: Annotated[User, Depends(require_analyst)],
    use_case: GetAlertUseCase = Depends(get_get_alert_use_case),
) -> APIResponse[AlertResponse]:
    """Retrieve an alert by identifier."""
    alert = await use_case.execute(alert_id)
    return success_response(data=alert, message="Alert retrieved successfully")


@router.get(
    "",
    response_model=APIResponse[list[AlertResponse]],
    status_code=status.HTTP_200_OK,
    summary="List alerts",
)
async def list_alerts(
    current_user: Annotated[User, Depends(require_analyst)],
    status_filter: str | None = Query(default=None, alias="status"),
    severity: str | None = Query(default=None),
    alert_type: str | None = Query(default=None),
    assigned_analyst_id: UUID | None = Query(default=None),
    is_sla_breached: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=1000),
    use_case: ListAlertsUseCase = Depends(get_list_alerts_use_case),
) -> APIResponse[list[AlertResponse]]:
    """List alerts with optional filters."""
    request = AlertListRequest(
        status=status_filter,
        severity=severity,
        alert_type=alert_type,
        assigned_analyst_id=assigned_analyst_id,
        is_sla_breached=is_sla_breached,
    )
    page_request = PageRequest(page=page, page_size=page_size)
    result = await use_case.execute(request, page_request)
    return success_response(data=result.items, message="Alerts retrieved successfully")


@router.put(
    "/{alert_id}",
    response_model=APIResponse[AlertResponse],
    status_code=status.HTTP_200_OK,
    summary="Update alert",
)
async def update_alert(
    alert_id: UUID,
    request: UpdateAlertRequest,
    current_user: Annotated[User, Depends(require_analyst)],
    use_case: UpdateAlertUseCase = Depends(get_update_alert_use_case),
) -> APIResponse[AlertResponse]:
    """Update an alert."""
    alert = await use_case.execute(alert_id, request)
    return success_response(data=alert, message="Alert updated successfully")


@router.post(
    "/{alert_id}/assign",
    response_model=APIResponse[AlertResponse],
    status_code=status.HTTP_200_OK,
    summary="Assign alert",
)
async def assign_alert(
    alert_id: UUID,
    request: AssignAlertRequest,
    current_user: Annotated[User, Depends(require_analyst)],
    use_case: AssignAlertUseCase = Depends(get_assign_alert_use_case),
) -> APIResponse[AlertResponse]:
    """Assign an alert to an analyst."""
    alert = await use_case.execute(alert_id, request)
    return success_response(data=alert, message="Alert assigned successfully")


@router.post(
    "/{alert_id}/resolve",
    response_model=APIResponse[AlertResponse],
    status_code=status.HTTP_200_OK,
    summary="Resolve alert",
)
async def resolve_alert(
    alert_id: UUID,
    request: ResolveAlertRequest,
    current_user: Annotated[User, Depends(require_analyst)],
    use_case: ResolveAlertUseCase = Depends(get_resolve_alert_use_case),
) -> APIResponse[AlertResponse]:
    """Resolve an alert."""
    alert = await use_case.execute(alert_id, request)
    return success_response(data=alert, message="Alert resolved successfully")
