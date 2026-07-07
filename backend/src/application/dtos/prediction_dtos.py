"""Prediction Data Transfer Objects."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreatePredictionRequest(BaseModel):
    """Request DTO for creating a prediction."""

    transaction_id: UUID = Field(..., description="Transaction UUID")
    model_id: UUID = Field(..., description="Model UUID")
    model_version: str = Field(..., description="Model version used")
    prediction_class: str = Field(
        ...,
        description="Prediction class (fraud, legitimate, suspicious)",
    )
    fraud_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraud probability (0.0-1.0)",
    )
    anomaly_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Anomaly score (higher = more anomalous)",
    )
    risk_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Risk score (0-100)",
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Prediction confidence (0.0-1.0)",
    )
    decision: str = Field(
        ...,
        description="Automated decision (approve, decline, review)",
    )
    latency_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Prediction latency in milliseconds",
    )
    explanation_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Feature importance and explanation data",
    )

    @field_validator("prediction_class")
    @classmethod
    def validate_prediction_class(cls, v: str) -> str:
        """Validate prediction class."""
        allowed_classes = ["fraud", "legitimate", "suspicious"]
        if v not in allowed_classes:
            raise ValueError(f"Prediction class must be one of: {allowed_classes}")
        return v

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        """Validate automated decision."""
        allowed_decisions = ["approve", "decline", "review"]
        if v not in allowed_decisions:
            raise ValueError(f"Decision must be one of: {allowed_decisions}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "model_id": "987fcdeb-51d3-12a4-b456-426614174000",
                "model_version": "1.2.3",
                "prediction_class": "fraud",
                "fraud_probability": 0.85,
                "anomaly_score": 7.2,
                "risk_score": 85.0,
                "confidence": 0.92,
                "decision": "decline",
                "latency_ms": 12.5,
                "explanation_data": {
                    "top_features": ["amount", "velocity_1h", "unusual_time"],
                    "feature_importance": {"amount": 0.4, "velocity_1h": 0.3},
                },
            }
        }
    }


class UpdatePredictionRequest(BaseModel):
    """Request DTO for updating a prediction."""

    decision: Optional[str] = Field(
        default=None,
        description="Updated automated decision",
    )
    explanation_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Updated explanation data",
    )

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: Optional[str]) -> Optional[str]:
        """Validate automated decision."""
        if v is not None:
            allowed_decisions = ["approve", "decline", "review"]
            if v not in allowed_decisions:
                raise ValueError(f"Decision must be one of: {allowed_decisions}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "decision": "review",
                "explanation_data": {
                    "analyst_notes": "Requires manual review due to high value",
                },
            }
        }
    }


class PredictionResponse(BaseModel):
    """Response DTO for prediction data."""

    prediction_id: UUID = Field(..., description="Prediction unique identifier")
    transaction_id: UUID = Field(..., description="Transaction UUID")
    model_id: UUID = Field(..., description="Model UUID")
    model_version: str = Field(..., description="Model version")
    prediction_class: str = Field(..., description="Prediction class")
    fraud_probability: float = Field(..., description="Fraud probability")
    anomaly_score: Optional[float] = Field(..., description="Anomaly score")
    risk_score: Optional[float] = Field(..., description="Risk score")
    confidence: Optional[float] = Field(..., description="Prediction confidence")
    decision: str = Field(..., description="Automated decision")
    latency_ms: Optional[float] = Field(..., description="Prediction latency")
    explanation_data: Optional[dict[str, Any]] = Field(..., description="Explanation data")
    created_at: datetime = Field(..., description="Prediction timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "prediction_id": "456789ab-cdef-12d3-a456-426614174000",
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "model_id": "987fcdeb-51d3-12a4-b456-426614174000",
                "model_version": "1.2.3",
                "prediction_class": "fraud",
                "fraud_probability": 0.85,
                "anomaly_score": 7.2,
                "risk_score": 85.0,
                "confidence": 0.92,
                "decision": "decline",
                "latency_ms": 12.5,
                "explanation_data": {
                    "top_features": ["amount", "velocity_1h"],
                },
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    }


class PredictionListRequest(BaseModel):
    """Request DTO for listing predictions."""

    transaction_id: Optional[UUID] = Field(
        default=None,
        description="Filter by transaction ID",
    )
    model_id: Optional[UUID] = Field(
        default=None,
        description="Filter by model ID",
    )
    prediction_class: Optional[str] = Field(
        default=None,
        description="Filter by prediction class",
    )
    decision: Optional[str] = Field(
        default=None,
        description="Filter by decision",
    )
    min_fraud_probability: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum fraud probability",
    )
    max_fraud_probability: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Maximum fraud probability",
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Filter predictions after this date",
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Filter predictions before this date",
    )

    @field_validator("prediction_class")
    @classmethod
    def validate_prediction_class(cls, v: Optional[str]) -> Optional[str]:
        """Validate prediction class."""
        if v is not None:
            allowed_classes = ["fraud", "legitimate", "suspicious"]
            if v not in allowed_classes:
                raise ValueError(f"Prediction class must be one of: {allowed_classes}")
        return v

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: Optional[str]) -> Optional[str]:
        """Validate decision."""
        if v is not None:
            allowed_decisions = ["approve", "decline", "review"]
            if v not in allowed_decisions:
                raise ValueError(f"Decision must be one of: {allowed_decisions}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "prediction_class": "fraud",
                "decision": "decline",
                "min_fraud_probability": 0.8,
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
            }
        }
    }


class ModelPerformanceResponse(BaseModel):
    """Response DTO for model performance metrics."""

    model_id: UUID = Field(..., description="Model UUID")
    model_version: str = Field(..., description="Model version")
    total_predictions: int = Field(..., description="Total number of predictions")
    accuracy: Optional[float] = Field(..., description="Model accuracy")
    precision: Optional[float] = Field(..., description="Model precision")
    recall: Optional[float] = Field(..., description="Model recall")
    f1_score: Optional[float] = Field(..., description="Model F1 score")
    avg_latency_ms: Optional[float] = Field(..., description="Average prediction latency")
    fraud_detection_rate: Optional[float] = Field(..., description="Fraud detection rate")
    false_positive_rate: Optional[float] = Field(..., description="False positive rate")
    analysis_period_start: datetime = Field(..., description="Analysis period start")
    analysis_period_end: datetime = Field(..., description="Analysis period end")

    model_config = {
        "json_schema_extra": {
            "example": {
                "model_id": "987fcdeb-51d3-12a4-b456-426614174000",
                "model_version": "1.2.3",
                "total_predictions": 10000,
                "accuracy": 0.95,
                "precision": 0.92,
                "recall": 0.88,
                "f1_score": 0.90,
                "avg_latency_ms": 15.2,
                "fraud_detection_rate": 0.94,
                "false_positive_rate": 0.03,
                "analysis_period_start": "2024-01-01T00:00:00Z",
                "analysis_period_end": "2024-01-31T23:59:59Z",
            }
        }
    }


class PredictionExplanationResponse(BaseModel):
    """Response DTO for detailed prediction explanation."""

    prediction_id: UUID = Field(..., description="Prediction UUID")
    feature_importance: dict[str, float] = Field(..., description="Feature importance scores")
    top_contributing_features: list[str] = Field(..., description="Top contributing features")
    rule_explanations: list[str] = Field(..., description="Business rule explanations")
    confidence_intervals: Optional[dict[str, float]] = Field(..., description="Confidence intervals")
    similar_cases: Optional[list[UUID]] = Field(..., description="Similar historical cases")
    recommendation: str = Field(..., description="Analyst recommendation")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prediction_id": "456789ab-cdef-12d3-a456-426614174000",
                "feature_importance": {
                    "transaction_amount": 0.35,
                    "velocity_1h": 0.25,
                    "unusual_time": 0.15,
                    "new_merchant": 0.12,
                    "location_risk": 0.13,
                },
                "top_contributing_features": [
                    "transaction_amount",
                    "velocity_1h",
                    "unusual_time",
                ],
                "rule_explanations": [
                    "Transaction amount is 5x higher than customer average",
                    "Customer has made 3 transactions in the last hour",
                    "Transaction occurred at 3 AM (unusual time)",
                ],
                "recommendation": "Decline transaction and alert customer",
            }
        }
    }