"""Merchant Data Transfer Objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class CreateMerchantRequest(BaseModel):
    """Request DTO for creating a merchant."""

    merchant_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Merchant business name",
    )
    merchant_category: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Merchant category code (MCC)",
    )
    country: str = Field(
        ...,
        min_length=2,
        max_length=3,
        description="Country code (ISO 3166-1 alpha-2 or alpha-3)",
    )
    contact_email: EmailStr | None = Field(
        default=None,
        description="Merchant contact email",
    )
    business_registration: str | None = Field(
        default=None,
        max_length=100,
        description="Business registration number",
    )

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        """Validate and uppercase country code."""
        return v.upper()

    model_config = {
        "json_schema_extra": {
            "example": {
                "merchant_name": "ABC Electronics Store",
                "merchant_category": "5732",
                "country": "USA",
                "contact_email": "contact@abcelectronics.com",
                "business_registration": "BRN123456789",
            }
        }
    }


class UpdateMerchantRequest(BaseModel):
    """Request DTO for updating a merchant."""

    merchant_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Merchant business name",
    )
    contact_email: EmailStr | None = Field(
        default=None,
        description="Merchant contact email",
    )
    risk_rating: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Risk rating (0-100)",
    )
    is_suspended: bool | None = Field(
        default=None,
        description="Suspension status",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "merchant_name": "ABC Electronics Store Ltd",
                "contact_email": "newcontact@abcelectronics.com",
                "risk_rating": 45,
                "is_suspended": False,
            }
        }
    }


class MerchantResponse(BaseModel):
    """Response DTO for merchant data."""

    merchant_id: UUID = Field(..., description="Merchant unique identifier")
    merchant_name: str = Field(..., description="Merchant business name")
    merchant_category: str = Field(..., description="Merchant category code")
    country: str = Field(..., description="Country code")
    contact_email: str | None = Field(..., description="Contact email")
    business_registration: str | None = Field(..., description="Business registration")
    risk_rating: int = Field(..., description="Risk rating (0-100)")
    fraud_rate: float = Field(..., description="Historical fraud rate")
    transaction_count: int = Field(..., description="Total transactions processed")
    total_volume: float = Field(..., description="Total transaction volume")
    avg_transaction_amount: float = Field(..., description="Average transaction amount")
    is_suspended: bool = Field(..., description="Whether merchant is suspended")
    suspension_reason: str | None = Field(..., description="Suspension reason")
    last_transaction_date: datetime | None = Field(..., description="Last transaction date")
    created_at: datetime = Field(..., description="Merchant onboarding date")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "merchant_id": "223e4567-e89b-12d3-a456-426614174000",
                "merchant_name": "ABC Electronics Store",
                "merchant_category": "5732",
                "country": "USA",
                "contact_email": "contact@abcelectronics.com",
                "business_registration": "BRN123456789",
                "risk_rating": 45,
                "fraud_rate": 0.02,
                "transaction_count": 1250,
                "total_volume": 150000.50,
                "avg_transaction_amount": 120.00,
                "is_suspended": False,
                "suspension_reason": None,
                "last_transaction_date": "2024-07-07T14:30:00Z",
                "created_at": "2023-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    }


class MerchantListRequest(BaseModel):
    """Request DTO for listing merchants."""

    merchant_category: str | None = Field(
        default=None,
        description="Filter by merchant category",
    )
    country: str | None = Field(
        default=None,
        description="Filter by country",
    )
    min_risk_rating: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Minimum risk rating",
    )
    max_risk_rating: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Maximum risk rating",
    )
    is_suspended: bool | None = Field(
        default=None,
        description="Filter by suspension status",
    )
    min_fraud_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum fraud rate",
    )

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str | None) -> str | None:
        """Validate and uppercase country code."""
        return v.upper() if v else v

    model_config = {
        "json_schema_extra": {
            "example": {
                "merchant_category": "5732",
                "country": "USA",
                "min_risk_rating": 0,
                "max_risk_rating": 50,
                "is_suspended": False,
            }
        }
    }


class MerchantStatisticsResponse(BaseModel):
    """Response DTO for merchant statistics."""

    total_merchants: int = Field(..., description="Total number of merchants")
    active_merchants: int = Field(..., description="Active merchants")
    suspended_merchants: int = Field(..., description="Suspended merchants")
    merchants_by_category: dict[str, int] = Field(..., description="Count by category")
    merchants_by_risk_level: dict[str, int] = Field(..., description="Count by risk level")
    avg_risk_rating: float = Field(..., description="Average risk rating")
    avg_fraud_rate: float = Field(..., description="Average fraud rate")
    high_risk_merchants: int = Field(..., description="High-risk merchants (rating > 70)")
    new_merchants_this_month: int = Field(..., description="New merchants this month")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_merchants": 5000,
                "active_merchants": 4650,
                "suspended_merchants": 350,
                "merchants_by_category": {
                    "5732": 1200,
                    "5411": 800,
                    "5812": 600,
                    "5999": 2400,
                },
                "merchants_by_risk_level": {
                    "low": 3500,
                    "medium": 1200,
                    "high": 250,
                    "critical": 50,
                },
                "avg_risk_rating": 32.5,
                "avg_fraud_rate": 0.025,
                "high_risk_merchants": 300,
                "new_merchants_this_month": 45,
            }
        }
    }


class SuspendMerchantRequest(BaseModel):
    """Request DTO for suspending a merchant."""

    reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Suspension reason",
    )
    suspension_type: str = Field(
        default="temporary",
        description="Suspension type (temporary, permanent)",
    )
    review_date: datetime | None = Field(
        default=None,
        description="Date for suspension review",
    )

    @field_validator("suspension_type")
    @classmethod
    def validate_suspension_type(cls, v: str) -> str:
        """Validate suspension type."""
        allowed_types = ["temporary", "permanent"]
        if v not in allowed_types:
            raise ValueError(f"Suspension type must be one of: {allowed_types}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "reason": "High fraud rate detected (>5%)",
                "suspension_type": "temporary",
                "review_date": "2024-08-01T00:00:00Z",
            }
        }
    }
