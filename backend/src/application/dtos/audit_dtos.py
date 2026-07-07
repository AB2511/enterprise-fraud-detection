"""Audit Data Transfer Objects."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateAuditLogRequest(BaseModel):
    """Request DTO for creating an audit log entry."""

    entity_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type of entity (customer, transaction, alert, etc.)",
    )
    entity_id: UUID = Field(..., description="Entity UUID")
    action: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Action performed (create, update, delete, etc.)",
    )
    user_id: UUID | None = Field(
        default=None,
        description="User who performed the action",
    )
    username: str | None = Field(
        default=None,
        max_length=255,
        description="Username who performed the action",
    )
    old_value: dict[str, Any] | None = Field(
        default=None,
        description="Previous entity state (for updates)",
    )
    new_value: dict[str, Any] | None = Field(
        default=None,
        description="New entity state",
    )
    ip_address: str | None = Field(
        default=None,
        max_length=45,
        description="IP address of the user",
    )
    user_agent: str | None = Field(
        default=None,
        max_length=255,
        description="User agent string",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Human-readable description of the action",
    )

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Validate entity type."""
        allowed_types = [
            "customer",
            "merchant",
            "transaction",
            "prediction",
            "alert",
            "user",
            "model",
            "audit_log",
        ]
        if v not in allowed_types:
            raise ValueError(f"Entity type must be one of: {allowed_types}")
        return v

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action type."""
        allowed_actions = [
            "create",
            "update",
            "delete",
            "activate",
            "deactivate",
            "assign",
            "resolve",
            "escalate",
            "approve",
            "reject",
            "login",
            "logout",
            "view",
            "export",
        ]
        if v not in allowed_actions:
            raise ValueError(f"Action must be one of: {allowed_actions}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "entity_type": "alert",
                "entity_id": "123e4567-e89b-12d3-a456-426614174000",
                "action": "resolve",
                "user_id": "987fcdeb-51d3-12a4-b456-426614174000",
                "username": "analyst@company.com",
                "old_value": {"status": "in_progress"},
                "new_value": {"status": "resolved", "resolution": "Confirmed legitimate"},
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "description": "Alert resolved as legitimate transaction",
            }
        }
    }


class AuditLogResponse(BaseModel):
    """Response DTO for audit log data."""

    audit_id: UUID = Field(..., description="Audit log unique identifier")
    entity_type: str = Field(..., description="Type of entity")
    entity_id: UUID = Field(..., description="Entity UUID")
    action: str = Field(..., description="Action performed")
    user_id: UUID | None = Field(..., description="User UUID")
    username: str | None = Field(..., description="Username")
    old_value: dict[str, Any] | None = Field(..., description="Previous state")
    new_value: dict[str, Any] | None = Field(..., description="New state")
    ip_address: str | None = Field(..., description="IP address")
    user_agent: str | None = Field(..., description="User agent")
    description: str | None = Field(..., description="Action description")
    created_at: datetime = Field(..., description="Audit entry timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "audit_id": "456789ab-cdef-12d3-a456-426614174000",
                "entity_type": "alert",
                "entity_id": "123e4567-e89b-12d3-a456-426614174000",
                "action": "resolve",
                "user_id": "987fcdeb-51d3-12a4-b456-426614174000",
                "username": "analyst@company.com",
                "old_value": {"status": "in_progress"},
                "new_value": {"status": "resolved"},
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
                "description": "Alert resolved",
                "created_at": "2024-01-15T10:30:00Z",
            }
        },
    }


class AuditLogListRequest(BaseModel):
    """Request DTO for listing audit logs."""

    entity_type: str | None = Field(
        default=None,
        description="Filter by entity type",
    )
    entity_id: UUID | None = Field(
        default=None,
        description="Filter by entity ID",
    )
    action: str | None = Field(
        default=None,
        description="Filter by action",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Filter by user ID",
    )
    username: str | None = Field(
        default=None,
        description="Filter by username",
    )
    start_date: datetime | None = Field(
        default=None,
        description="Filter entries after this date",
    )
    end_date: datetime | None = Field(
        default=None,
        description="Filter entries before this date",
    )

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str | None) -> str | None:
        """Validate entity type."""
        if v is not None:
            allowed_types = [
                "customer",
                "merchant",
                "transaction",
                "prediction",
                "alert",
                "user",
                "model",
                "audit_log",
            ]
            if v not in allowed_types:
                raise ValueError(f"Entity type must be one of: {allowed_types}")
        return v

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str | None) -> str | None:
        """Validate action type."""
        if v is not None:
            allowed_actions = [
                "create",
                "update",
                "delete",
                "activate",
                "deactivate",
                "assign",
                "resolve",
                "escalate",
                "approve",
                "reject",
                "login",
                "logout",
                "view",
                "export",
            ]
            if v not in allowed_actions:
                raise ValueError(f"Action must be one of: {allowed_actions}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "entity_type": "alert",
                "action": "resolve",
                "user_id": "987fcdeb-51d3-12a4-b456-426614174000",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
            }
        }
    }


class AuditTrailResponse(BaseModel):
    """Response DTO for entity audit trail."""

    entity_type: str = Field(..., description="Entity type")
    entity_id: UUID = Field(..., description="Entity UUID")
    audit_entries: list[AuditLogResponse] = Field(..., description="Chronological audit entries")
    total_entries: int = Field(..., description="Total number of audit entries")
    first_entry_date: datetime | None = Field(..., description="First audit entry date")
    last_entry_date: datetime | None = Field(..., description="Last audit entry date")
    unique_users: list[str] = Field(..., description="Users who modified this entity")

    model_config = {
        "json_schema_extra": {
            "example": {
                "entity_type": "alert",
                "entity_id": "123e4567-e89b-12d3-a456-426614174000",
                "audit_entries": [
                    {
                        "audit_id": "456789ab-cdef-12d3-a456-426614174000",
                        "action": "create",
                        "username": "system",
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "total_entries": 3,
                "first_entry_date": "2024-01-15T10:30:00Z",
                "last_entry_date": "2024-01-15T12:45:00Z",
                "unique_users": ["system", "analyst@company.com"],
            }
        }
    }


class AuditStatisticsResponse(BaseModel):
    """Response DTO for audit statistics."""

    total_entries: int = Field(..., description="Total audit entries")
    entries_by_entity_type: dict[str, int] = Field(..., description="Count by entity type")
    entries_by_action: dict[str, int] = Field(..., description="Count by action")
    entries_by_user: dict[str, int] = Field(..., description="Count by user")
    daily_activity: dict[str, int] = Field(..., description="Daily activity count")
    most_active_users: list[dict[str, Any]] = Field(..., description="Most active users")
    most_modified_entities: list[dict[str, Any]] = Field(..., description="Most modified entities")
    analysis_period_start: datetime = Field(..., description="Analysis period start")
    analysis_period_end: datetime = Field(..., description="Analysis period end")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_entries": 15000,
                "entries_by_entity_type": {
                    "transaction": 8000,
                    "alert": 4000,
                    "customer": 2000,
                    "user": 1000,
                },
                "entries_by_action": {
                    "create": 6000,
                    "update": 5000,
                    "resolve": 2500,
                    "view": 1500,
                },
                "entries_by_user": {
                    "system": 5000,
                    "analyst@company.com": 3000,
                    "admin@company.com": 2000,
                },
                "daily_activity": {
                    "2024-01-15": 150,
                    "2024-01-16": 180,
                },
                "most_active_users": [
                    {"username": "system", "count": 5000},
                    {"username": "analyst@company.com", "count": 3000},
                ],
                "most_modified_entities": [
                    {"entity_type": "transaction", "entity_id": "123...", "count": 25},
                ],
                "analysis_period_start": "2024-01-01T00:00:00Z",
                "analysis_period_end": "2024-01-31T23:59:59Z",
            }
        }
    }


class ComplianceReportRequest(BaseModel):
    """Request DTO for compliance reporting."""

    report_type: str = Field(
        ...,
        description="Type of compliance report (access, modifications, data_export)",
    )
    entity_types: list[str] | None = Field(
        default=None,
        description="Filter by entity types",
    )
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    user_filter: str | None = Field(
        default=None,
        description="Filter by specific user",
    )
    include_system_actions: bool = Field(
        default=False,
        description="Include system-generated actions",
    )

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        """Validate report type."""
        allowed_types = ["access", "modifications", "data_export", "user_activity"]
        if v not in allowed_types:
            raise ValueError(f"Report type must be one of: {allowed_types}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "report_type": "modifications",
                "entity_types": ["customer", "transaction"],
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
                "user_filter": "analyst@company.com",
                "include_system_actions": False,
            }
        }
    }
