"""Health Check Endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import Settings, get_settings
from src.infrastructure.database import get_async_session
from src.presentation.api.v1.schemas.health_schema import HealthResponse

router = APIRouter()


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the API is operational",
)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        Health status response
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.utcnow(),
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Check if the API is ready to accept requests (includes DB check)",
)
async def readiness_check(
    session: AsyncSession = Depends(get_async_session),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Readiness check with database connectivity validation.

    Args:
        session: Database session
        settings: Application settings

    Returns:
        Health status with readiness confirmation
    """
    # Test database connection
    try:
        await session.execute("SELECT 1")
        database_healthy = True
    except Exception:
        database_healthy = False

    return HealthResponse(
        status="ready" if database_healthy else "not_ready",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.utcnow(),
        checks={"database": "healthy" if database_healthy else "unhealthy"},
    )


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Simple liveness probe for Kubernetes/ECS",
)
async def liveness_check() -> dict[str, str]:
    """Liveness check for container orchestration.

    Returns:
        Simple alive status
    """
    return {"status": "alive"}
