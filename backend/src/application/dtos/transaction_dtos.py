"""Transaction Data Transfer Objects."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateTransactionRequest(BaseModel):
    """Request DTO for creating a transaction."""

    customer_id: UUID = Field(..., description="Customer UUID")
    merchant_id: UUID = Field(..., description="Merchant UUID")
    amount: Decimal = Field(..., gt=0, description="Transaction amount (must be positive)")
    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Currency code (ISO 4217)",
    )
    transaction_type: str = Field(
        default="purchase",
        description="Transaction type (purchase, refund, withdrawal, transfer)",
    )
    payment_channel: str = Field(
        default="online",
        description="Payment channel (online, pos, atm, mobile, phone, branch)",
    )
    payment_method: str = Field(
        default="credit_card",
        description="Payment method (credit_card, debit_card, bank_transfer, wallet, cash, crypto)",
    )
    device_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Device identifier",
    )
    ip_address: Optional[str] = Field(
        default=None,
        max_length=45,
        description="IP address",
    )
    latitude: Optional[float] = Field(
        default=None,
        ge=-90,
        le=90,
        description="Latitude (-90 to 90)",
    )
    longitude: Optional[float] = Field(
        default=None,
        ge=-180,
        le=180,
        description="Longitude (-180 to 180)",
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate and uppercase currency code."""
        return v.upper()

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, v: str) -> str:
        """Validate transaction type."""
        allowed_types = ["purchase", "refund", "withdrawal", "transfer"]
        if v not in allowed_types:
            raise ValueError(f"Transaction type must be one of: {allowed_types}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": "123e4567-e89b-12d3-a456-426614174000",
                "merchant_id": "223e4567-e89b-12d3-a456-426614174000",
                "amount": 250.00,
                "currency": "USD",
                "transaction_type": "purchase",
                "payment_channel": "online",
                "payment_method": "credit_card",
                "device_id": "device_12345",
                "ip_address": "192.168.1.1",
                "latitude": 37.7749,
                "longitude": -122.4194,
            }
        }
    }


class UpdateTransactionRequest(BaseModel):
    """Request DTO for updating a transaction."""

    status: Optional[str] = Field(
        default=None,
        description="Transaction status (pending, approved, declined, failed, reversed)",
    )
    is_fraud: Optional[bool] = Field(
        default=None,
        description="Mark transaction as fraud",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate transaction status."""
        if v is None:
            return v
        allowed_statuses = ["pending", "approved", "declined", "failed", "reversed"]
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {allowed_statuses}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "approved",
                "is_fraud": False,
            }
        }
    }


class SearchTransactionRequest(BaseModel):
    """Request DTO for searching transactions."""

    customer_id: Optional[UUID] = Field(default=None, description="Filter by customer")
    merchant_id: Optional[UUID] = Field(default=None, description="Filter by merchant")
    min_amount: Optional[Decimal] = Field(default=None, description="Minimum amount")
    max_amount: Optional[Decimal] = Field(default=None, description="Maximum amount")
    currency: Optional[str] = Field(default=None, description="Filter by currency")
    transaction_type: Optional[str] = Field(default=None, description="Filter by type")
    payment_channel: Optional[str] = Field(default=None, description="Filter by channel")
    is_fraud: Optional[bool] = Field(default=None, description="Filter by fraud status")
    start_date: Optional[datetime] = Field(default=None, description="Start date")
    end_date: Optional[datetime] = Field(default=None, description="End date")

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": "123e4567-e89b-12d3-a456-426614174000",
                "min_amount": 100.00,
                "max_amount": 1000.00,
                "currency": "USD",
                "is_fraud": False,
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z",
            }
        }
    }


class TransactionResponse(BaseModel):
    """Response DTO for transaction data."""

    transaction_id: UUID = Field(..., description="Transaction unique identifier")
    customer_id: UUID = Field(..., description="Customer UUID")
    merchant_id: UUID = Field(..., description="Merchant UUID")
    amount: float = Field(..., description="Transaction amount")
    currency: str = Field(..., description="Currency code")
    transaction_type: str = Field(..., description="Transaction type")
    status: str = Field(..., description="Transaction status")
    payment_channel: str = Field(..., description="Payment channel")
    payment_method: str = Field(..., description="Payment method")
    device_id: Optional[str] = Field(None, description="Device identifier")
    ip_address: Optional[str] = Field(None, description="IP address")
    latitude: Optional[float] = Field(None, description="Latitude")
    longitude: Optional[float] = Field(None, description="Longitude")
    velocity_1h: Optional[float] = Field(None, description="Transactions in last hour")
    velocity_24h: Optional[float] = Field(None, description="Transactions in last 24 hours")
    velocity_7d: Optional[float] = Field(None, description="Transactions in last 7 days")
    is_fraud: bool = Field(..., description="Whether transaction is fraud")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    created_at: datetime = Field(..., description="Record creation timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "transaction_id": "323e4567-e89b-12d3-a456-426614174000",
                "customer_id": "123e4567-e89b-12d3-a456-426614174000",
                "merchant_id": "223e4567-e89b-12d3-a456-426614174000",
                "amount": 250.00,
                "currency": "USD",
                "transaction_type": "purchase",
                "status": "approved",
                "payment_channel": "online",
                "payment_method": "credit_card",
                "device_id": "device_12345",
                "ip_address": "192.168.1.1",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "velocity_1h": 2.0,
                "velocity_24h": 5.0,
                "velocity_7d": 12.0,
                "is_fraud": False,
                "timestamp": "2024-07-07T14:30:00Z",
                "created_at": "2024-07-07T14:30:00Z",
            }
        },
    }
