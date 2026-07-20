"""Standard API Response Wrapper.

Provides consistent response structure across all API endpoints.
"""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIMetadata(BaseModel):
    """Metadata included in every API response."""

    request_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique request identifier for tracing",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp",
    )
    api_version: str = Field(
        default="v1",
        description="API version",
    )


class APIResponse(BaseModel, Generic[T]):
    """Standard API response envelope.

    All API endpoints should return this structure for consistency.

    Attributes:
        success: Whether the operation succeeded
        message: Human-readable message
        data: Response payload (type varies by endpoint)
        metadata: Request metadata for tracing
    """

    success: bool = Field(
        ...,
        description="Whether the operation succeeded",
    )
    message: str = Field(
        ...,
        description="Human-readable status message",
    )
    data: T | None = Field(
        default=None,
        description="Response payload",
    )
    metadata: APIMetadata = Field(
        default_factory=APIMetadata,
        description="Request metadata",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": "123", "name": "Example"},
                "metadata": {
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "api_version": "v1",
                },
            }
        }
    }


def success_response(
    data: T,
    message: str = "Operation completed successfully",
    request_id: str | None = None,
) -> APIResponse[T]:
    """Create a success response.

    Args:
        data: Response data payload
        message: Success message
        request_id: Optional request ID for tracing

    Returns:
        Standard API response
    """
    metadata = APIMetadata()
    if request_id:
        metadata.request_id = request_id

    return APIResponse(
        success=True,
        message=message,
        data=data,
        metadata=metadata,
    )


def error_response(
    message: str,
    request_id: str | None = None,
) -> APIResponse[None]:
    """Create an error response.

    Args:
        message: Error message
        request_id: Optional request ID for tracing

    Returns:
        Standard API response with error
    """
    metadata = APIMetadata()
    if request_id:
        metadata.request_id = request_id

    return APIResponse(
        success=False,
        message=message,
        data=None,
        metadata=metadata,
    )
