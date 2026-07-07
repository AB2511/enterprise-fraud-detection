"""Model Data Transfer Objects."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateModelRequest(BaseModel):
    """Request DTO for creating a model."""

    version: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Model version (e.g., '1.0.0')",
    )
    model_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Model type (xgboost, isolation_forest, neural_network)",
    )
    artifact_path: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Path to model artifact (S3 URI or file path)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Model training metadata (hyperparameters, dataset info)",
    )
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Model performance metrics (accuracy, precision, recall)",
    )
    training_date: Optional[datetime] = Field(
        default=None,
        description="When model was trained (defaults to current time)",
    )
    created_by: str = Field(
        default="system",
        description="Who created this model",
    )

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version format."""
        if not v.strip():
            raise ValueError("Version cannot be empty")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "version": "1.2.3",
                "model_type": "xgboost",
                "artifact_path": "s3://ml-models/fraud-detection/v1.2.3/model.pkl",
                "metadata": {
                    "hyperparameters": {"n_estimators": 100, "max_depth": 6},
                    "dataset_version": "2024-01",
                    "features_count": 47,
                },
                "metrics": {
                    "accuracy": 0.95,
                    "precision": 0.92,
                    "recall": 0.88,
                    "f1_score": 0.90,
                    "pr_auc": 0.94,
                },
                "created_by": "data_scientist@company.com",
            }
        }
    }


class UpdateModelRequest(BaseModel):
    """Request DTO for updating a model."""

    artifact_path: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Updated path to model artifact",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Updated model metadata",
    )
    metrics: Optional[dict[str, float]] = Field(
        default=None,
        description="Updated model performance metrics",
    )
    status: Optional[str] = Field(
        default=None,
        description="Model status (training, staging, production, archived)",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate model status."""
        if v is not None:
            allowed_statuses = ["training", "staging", "production", "archived"]
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {allowed_statuses}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "metrics": {
                    "accuracy": 0.96,
                    "precision": 0.93,
                    "recall": 0.89,
                },
                "status": "staging",
            }
        }
    }


class ModelPromotionRequest(BaseModel):
    """Request DTO for promoting a model."""

    target_status: str = Field(
        ...,
        description="Target status (staging, production)",
    )
    approval_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reason for promotion",
    )

    @field_validator("target_status")
    @classmethod
    def validate_target_status(cls, v: str) -> str:
        """Validate promotion target status."""
        allowed_statuses = ["staging", "production"]
        if v not in allowed_statuses:
            raise ValueError(f"Target status must be one of: {allowed_statuses}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "target_status": "production",
                "approval_reason": "Model passed all validation tests with 96% accuracy",
            }
        }
    }


class ModelResponse(BaseModel):
    """Response DTO for model data."""

    model_id: UUID = Field(..., description="Model unique identifier")
    version: str = Field(..., description="Model version")
    model_type: str = Field(..., description="Model type")
    artifact_path: str = Field(..., description="Model artifact path")
    metadata: dict[str, Any] = Field(..., description="Model metadata")
    metrics: dict[str, float] = Field(..., description="Performance metrics")
    training_date: datetime = Field(..., description="Training date")
    status: str = Field(..., description="Deployment status")
    is_production: bool = Field(..., description="Whether model is in production")
    is_archived: bool = Field(..., description="Whether model is archived")
    created_by: str = Field(..., description="Model creator")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "model_id": "123e4567-e89b-12d3-a456-426614174000",
                "version": "1.2.3",
                "model_type": "xgboost",
                "artifact_path": "s3://ml-models/fraud-detection/v1.2.3/model.pkl",
                "metadata": {
                    "hyperparameters": {"n_estimators": 100, "max_depth": 6},
                    "dataset_version": "2024-01",
                },
                "metrics": {
                    "accuracy": 0.95,
                    "precision": 0.92,
                    "recall": 0.88,
                },
                "training_date": "2024-01-15T10:30:00Z",
                "status": "production",
                "is_production": True,
                "is_archived": False,
                "created_by": "data_scientist@company.com",
                "created_at": "2024-01-15T10:30:00Z",
            }
        },
    }


class ModelListRequest(BaseModel):
    """Request DTO for listing models."""

    model_type: Optional[str] = Field(
        default=None,
        description="Filter by model type",
    )
    status: Optional[str] = Field(
        default=None,
        description="Filter by status (training, staging, production, archived)",
    )
    created_by: Optional[str] = Field(
        default=None,
        description="Filter by creator",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate model status."""
        if v is not None:
            allowed_statuses = ["training", "staging", "production", "archived"]
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {allowed_statuses}")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "model_type": "xgboost",
                "status": "production",
            }
        }
    }


class ModelStatisticsResponse(BaseModel):
    """Response DTO for model statistics."""

    total: int = Field(..., description="Total number of models")
    by_status: dict[str, int] = Field(..., description="Count by status")
    by_type: dict[str, int] = Field(..., description="Count by model type")
    latest_training_date: Optional[str] = Field(..., description="Latest training date")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 25,
                "by_status": {
                    "training": 3,
                    "staging": 2,
                    "production": 5,
                    "archived": 15,
                },
                "by_type": {
                    "xgboost": 15,
                    "isolation_forest": 8,
                    "neural_network": 2,
                },
                "latest_training_date": "2024-01-15T10:30:00Z",
            }
        }
    }