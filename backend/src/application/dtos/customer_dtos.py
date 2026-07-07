"""Customer Data Transfer Objects."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class CreateCustomerRequest(BaseModel):
    """Request DTO for creating a customer."""

    customer_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Customer full name",
    )
    email: EmailStr = Field(..., description="Customer email address")
    country: str = Field(
        ...,
        min_length=2,
        max_length=3,
        description="Country code (ISO 3166-1 alpha-2 or alpha-3)",
    )
    date_of_birth: date | None = Field(
        default=None,
        description="Customer date of birth",
    )

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        """Validate and uppercase country code."""
        return v.upper()

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: date | None) -> date | None:
        """Validate date of birth is in the past."""
        if v and v >= date.today():
            raise ValueError("Date of birth must be in the past")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_name": "John Doe",
                "email": "john.doe@example.com",
                "country": "USA",
                "date_of_birth": "1990-01-15",
            }
        }
    }


class UpdateCustomerRequest(BaseModel):
    """Request DTO for updating a customer."""

    customer_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Customer full name",
    )
    credit_score: int | None = Field(
        default=None,
        ge=300,
        le=850,
        description="Credit score (300-850)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_name": "John Smith",
                "credit_score": 720,
            }
        }
    }


class CustomerResponse(BaseModel):
    """Response DTO for customer data."""

    customer_id: UUID = Field(..., description="Customer unique identifier")
    customer_name: str = Field(..., description="Customer full name")
    email: str = Field(..., description="Customer email address")
    country: str = Field(..., description="Country code")
    kyc_status: str = Field(..., description="KYC verification status")
    customer_risk_category: str = Field(..., description="Risk category")
    credit_score: int = Field(..., description="Credit score")
    historical_fraud_count: int = Field(..., description="Number of fraud incidents")
    lifetime_transaction_volume: float = Field(..., description="Total transaction volume")
    account_age_days: int = Field(..., description="Account age in days")
    is_active: bool = Field(..., description="Whether account is active")
    is_verified: bool = Field(..., description="Whether KYC is verified")
    can_transact: bool = Field(..., description="Whether customer can make transactions")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "customer_id": "123e4567-e89b-12d3-a456-426614174000",
                "customer_name": "John Doe",
                "email": "john.doe@example.com",
                "country": "USA",
                "kyc_status": "verified",
                "customer_risk_category": "low",
                "credit_score": 720,
                "historical_fraud_count": 0,
                "lifetime_transaction_volume": 15000.50,
                "account_age_days": 365,
                "is_active": True,
                "is_verified": True,
                "can_transact": True,
                "created_at": "2023-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    }
