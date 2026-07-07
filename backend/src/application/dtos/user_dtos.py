"""User Data Transfer Objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class CreateUserRequest(BaseModel):
    """Request DTO for creating a user."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=255,
        description="User password (min 8 characters)",
    )
    role: str = Field(
        default="analyst",
        description="User role (admin, analyst, data_scientist, auditor)",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate user role."""
        allowed_roles = ["admin", "analyst", "data_scientist", "auditor"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {allowed_roles}")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "analyst@company.com",
                "password": "SecurePass123!",
                "role": "analyst",
            }
        }
    }


class UpdateUserRequest(BaseModel):
    """Request DTO for updating a user."""

    role: str | None = Field(
        default=None,
        description="User role (admin, analyst, data_scientist, auditor)",
    )
    status: str | None = Field(
        default=None,
        description="Account status (active, inactive, locked)",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        """Validate user role."""
        if v is not None:
            allowed_roles = ["admin", "analyst", "data_scientist", "auditor"]
            if v not in allowed_roles:
                raise ValueError(f"Role must be one of: {allowed_roles}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate user status."""
        if v is not None:
            allowed_statuses = ["active", "inactive", "locked"]
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {allowed_statuses}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "role": "data_scientist",
                "status": "active",
            }
        }
    }


class ChangePasswordRequest(BaseModel):
    """Request DTO for changing password."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=255,
        description="New password (min 8 characters)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "current_password": "OldPassword123!",
                "new_password": "NewSecurePass456!",
            }
        }
    }


class LoginRequest(BaseModel):
    """Request DTO for user authentication."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "analyst@company.com",
                "password": "SecurePass123!",
            }
        }
    }


class UserResponse(BaseModel):
    """Response DTO for user data."""

    user_id: UUID = Field(..., description="User unique identifier")
    email: str = Field(..., description="User email address")
    role: str = Field(..., description="User role")
    status: str = Field(..., description="Account status")
    is_active: bool = Field(..., description="Whether account is active")
    is_locked: bool = Field(..., description="Whether account is locked")
    can_review_alerts: bool = Field(..., description="Whether user can review fraud alerts")
    can_manage_models: bool = Field(..., description="Whether user can manage ML models")
    last_login: datetime | None = Field(..., description="Last login timestamp")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "analyst@company.com",
                "role": "analyst",
                "status": "active",
                "is_active": True,
                "is_locked": False,
                "can_review_alerts": True,
                "can_manage_models": False,
                "last_login": "2024-01-15T10:30:00Z",
                "created_at": "2023-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    }


class AuthenticationResponse(BaseModel):
    """Response DTO for authentication."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse = Field(..., description="Authenticated user information")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "analyst@company.com",
                    "role": "analyst",
                    "status": "active",
                },
            }
        }
    }


class UserListRequest(BaseModel):
    """Request DTO for listing users."""

    role: str | None = Field(
        default=None,
        description="Filter by role (admin, analyst, data_scientist, auditor)",
    )
    status: str | None = Field(
        default=None,
        description="Filter by status (active, inactive, locked)",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        """Validate user role."""
        if v is not None:
            allowed_roles = ["admin", "analyst", "data_scientist", "auditor"]
            if v not in allowed_roles:
                raise ValueError(f"Role must be one of: {allowed_roles}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate user status."""
        if v is not None:
            allowed_statuses = ["active", "inactive", "locked"]
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {allowed_statuses}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "role": "analyst",
                "status": "active",
            }
        }
    }
