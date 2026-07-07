"""Alert Data Transfer Objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateAlertRequest(BaseModel):
    """Request DTO for creating an alert."""

    transaction_id: UUID = Field(..., description="Transaction UUID")
    prediction_id: UUID = Field(..., description="Prediction UUID")
    alert_type: str = Field(
        ...,
        description="Alert type (high_fraud_probability, velocity_alert, amount_alert, etc.)",
    )
    severity: str = Field(
        ...,
        description="Alert severity (low, medium, high, critical)",
    )
    sla_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="SLA resolution time in hours (1-168)",
    )

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate alert severity."""
        allowed_severities = ["low", "medium", "high", "critical"]
        if v not in allowed_severities:
            raise ValueError(f"Severity must be one of: {allowed_severities}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "prediction_id": "987fcdeb-51d3-12a4-b456-426614174000",
                "alert_type": "high_fraud_probability",
                "severity": "high",
                "sla_hours": 4,
            }
        }
    }


class UpdateAlertRequest(BaseModel):
    """Request DTO for updating an alert."""

    status: str | None = Field(
        default=None,
        description="Alert status (open, in_progress, resolved, closed, escalated)",
    )
    assigned_analyst_id: UUID | None = Field(
        default=None,
        description="Analyst assigned to this alert",
    )
    resolution: str | None = Field(
        default=None,
        max_length=500,
        description="Resolution description",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate alert status."""
        if v is not None:
            allowed_statuses = ["open", "in_progress", "resolved", "closed", "escalated"]
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {allowed_statuses}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "in_progress",
                "assigned_analyst_id": "456789ab-cdef-12d3-a456-426614174000",
                "resolution": "Transaction verified as legitimate after customer contact",
            }
        }
    }


class AssignAlertRequest(BaseModel):
    """Request DTO for assigning an alert to an analyst."""

    analyst_id: UUID = Field(..., description="Analyst UUID to assign")
    priority: str | None = Field(
        default=None,
        description="Alert priority (low, normal, high, urgent)",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Assignment notes",
    )

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        """Validate alert priority."""
        if v is not None:
            allowed_priorities = ["low", "normal", "high", "urgent"]
            if v not in allowed_priorities:
                raise ValueError(f"Priority must be one of: {allowed_priorities}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "analyst_id": "456789ab-cdef-12d3-a456-426614174000",
                "priority": "high",
                "notes": "High-value customer transaction requires immediate attention",
            }
        }
    }


class ResolveAlertRequest(BaseModel):
    """Request DTO for resolving an alert."""

    resolution: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Resolution description",
    )
    is_fraud: bool = Field(..., description="Whether transaction was confirmed as fraud")
    confidence: str = Field(
        ...,
        description="Analyst confidence in decision (low, medium, high)",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Additional resolution notes",
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: str) -> str:
        """Validate confidence level."""
        allowed_confidence = ["low", "medium", "high"]
        if v not in allowed_confidence:
            raise ValueError(f"Confidence must be one of: {allowed_confidence}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "resolution": "Transaction confirmed legitimate after customer verification",
                "is_fraud": False,
                "confidence": "high",
                "notes": "Customer confirmed the transaction via phone call",
            }
        }
    }


class AlertResponse(BaseModel):
    """Response DTO for alert data."""

    alert_id: UUID = Field(..., description="Alert unique identifier")
    transaction_id: UUID = Field(..., description="Transaction UUID")
    prediction_id: UUID = Field(..., description="Prediction UUID")
    alert_type: str = Field(..., description="Alert type")
    severity: str = Field(..., description="Alert severity")
    status: str = Field(..., description="Alert status")
    assigned_analyst_id: UUID | None = Field(..., description="Assigned analyst UUID")
    assigned_at: datetime | None = Field(..., description="Assignment timestamp")
    resolution: str | None = Field(..., description="Resolution description")
    resolved_at: datetime | None = Field(..., description="Resolution timestamp")
    resolved_by_id: UUID | None = Field(..., description="Resolver UUID")
    sla_deadline: datetime = Field(..., description="SLA deadline")
    is_sla_breached: bool = Field(..., description="Whether SLA was breached")
    time_to_resolution_hours: float | None = Field(..., description="Resolution time in hours")
    created_at: datetime = Field(..., description="Alert creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "alert_id": "789abcde-f012-34d5-a678-901234567890",
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "prediction_id": "987fcdeb-51d3-12a4-b456-426614174000",
                "alert_type": "high_fraud_probability",
                "severity": "high",
                "status": "resolved",
                "assigned_analyst_id": "456789ab-cdef-12d3-a456-426614174000",
                "assigned_at": "2024-01-15T10:30:00Z",
                "resolution": "Transaction confirmed legitimate",
                "resolved_at": "2024-01-15T12:45:00Z",
                "resolved_by_id": "456789ab-cdef-12d3-a456-426614174000",
                "sla_deadline": "2024-01-15T14:30:00Z",
                "is_sla_breached": False,
                "time_to_resolution_hours": 2.25,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T12:45:00Z",
            }
        },
    }


class AlertListRequest(BaseModel):
    """Request DTO for listing alerts."""

    status: str | None = Field(
        default=None,
        description="Filter by status",
    )
    severity: str | None = Field(
        default=None,
        description="Filter by severity",
    )
    alert_type: str | None = Field(
        default=None,
        description="Filter by alert type",
    )
    assigned_analyst_id: UUID | None = Field(
        default=None,
        description="Filter by assigned analyst",
    )
    is_sla_breached: bool | None = Field(
        default=None,
        description="Filter by SLA breach status",
    )
    start_date: datetime | None = Field(
        default=None,
        description="Filter alerts created after this date",
    )
    end_date: datetime | None = Field(
        default=None,
        description="Filter alerts created before this date",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate alert status."""
        if v is not None:
            allowed_statuses = ["open", "in_progress", "resolved", "closed", "escalated"]
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {allowed_statuses}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str | None) -> str | None:
        """Validate alert severity."""
        if v is not None:
            allowed_severities = ["low", "medium", "high", "critical"]
            if v not in allowed_severities:
                raise ValueError(f"Severity must be one of: {allowed_severities}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "open",
                "severity": "high",
                "assigned_analyst_id": "456789ab-cdef-12d3-a456-426614174000",
                "is_sla_breached": False,
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
            }
        }
    }


class AlertStatisticsResponse(BaseModel):
    """Response DTO for alert statistics."""

    total_alerts: int = Field(..., description="Total number of alerts")
    alerts_by_status: dict[str, int] = Field(..., description="Count by status")
    alerts_by_severity: dict[str, int] = Field(..., description="Count by severity")
    alerts_by_type: dict[str, int] = Field(..., description="Count by alert type")
    sla_breach_rate: float = Field(..., description="SLA breach rate (0.0-1.0)")
    avg_resolution_time_hours: float | None = Field(..., description="Average resolution time")
    open_alerts: int = Field(..., description="Currently open alerts")
    overdue_alerts: int = Field(..., description="Overdue alerts")
    analysis_period_start: datetime = Field(..., description="Analysis period start")
    analysis_period_end: datetime = Field(..., description="Analysis period end")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_alerts": 1250,
                "alerts_by_status": {
                    "open": 85,
                    "in_progress": 32,
                    "resolved": 1020,
                    "closed": 110,
                    "escalated": 3,
                },
                "alerts_by_severity": {
                    "low": 450,
                    "medium": 520,
                    "high": 240,
                    "critical": 40,
                },
                "alerts_by_type": {
                    "high_fraud_probability": 400,
                    "velocity_alert": 300,
                    "amount_alert": 250,
                    "location_alert": 200,
                    "device_alert": 100,
                },
                "sla_breach_rate": 0.12,
                "avg_resolution_time_hours": 3.5,
                "open_alerts": 85,
                "overdue_alerts": 15,
                "analysis_period_start": "2024-01-01T00:00:00Z",
                "analysis_period_end": "2024-01-31T23:59:59Z",
            }
        }
    }


class AlertWorkflowResponse(BaseModel):
    """Response DTO for alert workflow status."""

    alert_id: UUID = Field(..., description="Alert UUID")
    workflow_stage: str = Field(..., description="Current workflow stage")
    next_actions: list[str] = Field(..., description="Available next actions")
    escalation_path: list[str] = Field(..., description="Escalation path")
    required_approvals: list[str] = Field(..., description="Required approvals")
    time_in_current_stage_hours: float = Field(..., description="Time in current stage")

    model_config = {
        "json_schema_extra": {
            "example": {
                "alert_id": "789abcde-f012-34d5-a678-901234567890",
                "workflow_stage": "analyst_review",
                "next_actions": ["resolve", "escalate", "request_more_info"],
                "escalation_path": ["senior_analyst", "team_lead", "manager"],
                "required_approvals": ["senior_analyst"],
                "time_in_current_stage_hours": 1.5,
            }
        }
    }
