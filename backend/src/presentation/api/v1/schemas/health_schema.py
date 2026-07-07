"""Health Check Schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema.

    Attributes:
        status: Current health status
        version: Application version
        environment: Deployment environment
        timestamp: Response timestamp
        checks: Optional dictionary of component health checks
    """

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment name")
    timestamp: datetime = Field(..., description="Response timestamp")
    checks: dict[str, str] | None = Field(None, description="Component health checks")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "environment": "production",
                "timestamp": "2026-07-07T12:00:00Z",
                "checks": {
                    "database": "healthy",
                    "model_loaded": "healthy",
                },
            }
        }
    }
