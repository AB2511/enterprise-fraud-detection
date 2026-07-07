"""
Data Contracts - Pydantic Schemas

Defines explicit schemas for all data structures in the ML pipeline.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DatasetType(str, Enum):
    """Supported dataset types"""

    CREDITCARD = "creditcard"
    IEEE_CIS = "ieee-cis"
    CUSTOM = "custom"


class ProcessingStage(str, Enum):
    """Data processing stages"""

    RAW = "raw"
    CLEANED = "cleaned"
    VALIDATED = "validated"
    FEATURED = "featured"
    SPLIT = "split"


# ============================================================================
# Raw Transaction Schema
# ============================================================================


class RawTransaction(BaseModel):
    """Raw transaction data before processing"""

    transaction_id: str
    timestamp: datetime
    amount: float = Field(gt=0, description="Transaction amount (must be positive)")
    customer_id: str | None = None
    merchant_id: str | None = None
    is_fraud: bool | None = None  # Target variable (may be None for unlabeled)

    # Optional fields
    transaction_type: str | None = None
    payment_method: str | None = None
    device_id: str | None = None
    ip_address: str | None = None
    country_code: str | None = None

    # Metadata
    source_dataset: DatasetType
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Original raw fields")

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "txn_123456",
                "timestamp": "2026-07-07T10:30:00Z",
                "amount": 125.50,
                "customer_id": "cust_789",
                "merchant_id": "merch_456",
                "is_fraud": False,
                "source_dataset": "creditcard",
            }
        }


# ============================================================================
# Processed Transaction Schema
# ============================================================================


class ProcessedTransaction(BaseModel):
    """Processed transaction after cleaning and validation"""

    transaction_id: str
    timestamp: datetime
    amount: float
    customer_id: str
    merchant_id: str
    is_fraud: bool  # Must be labeled after processing

    # Required processed fields
    transaction_type: str
    payment_method: str
    hour_of_day: int = Field(ge=0, le=23)
    day_of_week: int = Field(ge=0, le=6)
    is_weekend: bool

    # Optional enriched fields
    device_id: str | None = None
    ip_address: str | None = None
    country_code: str | None = None

    # Processing metadata
    processing_version: str
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "txn_123456",
                "timestamp": "2026-07-07T10:30:00Z",
                "amount": 125.50,
                "customer_id": "cust_789",
                "merchant_id": "merch_456",
                "is_fraud": False,
                "transaction_type": "purchase",
                "payment_method": "credit_card",
                "hour_of_day": 10,
                "day_of_week": 1,
                "is_weekend": False,
                "processing_version": "v1.0.0",
            }
        }


# ============================================================================
# Feature Vector Schema
# ============================================================================


class FeatureVector(BaseModel):
    """Feature vector ready for model training/inference"""

    transaction_id: str
    features: dict[str, float] = Field(description="Feature name -> value mapping")
    target: bool = Field(description="Fraud label (target variable)")

    # Feature metadata
    feature_version: str
    feature_names: list[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("features")
    @classmethod
    def validate_features(cls, v: dict[str, float]) -> dict[str, float]:
        """Ensure all feature values are numeric"""
        for name, value in v.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Feature '{name}' must be numeric, got {type(value)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "txn_123456",
                "features": {
                    "amount_log": 4.832,
                    "hour_sin": 0.866,
                    "velocity_1h": 3.0,
                    "merchant_fraud_rate": 0.005,
                },
                "target": False,
                "feature_version": "v1.0.0",
                "feature_names": ["amount_log", "hour_sin", "velocity_1h", "merchant_fraud_rate"],
            }
        }


# ============================================================================
# Dataset Metadata Schema
# ============================================================================


class DatasetMetadata(BaseModel):
    """Metadata for a dataset version"""

    dataset_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dataset_name: str
    dataset_type: DatasetType
    version: str
    stage: ProcessingStage

    # Dataset statistics
    num_records: int = Field(ge=0)
    num_features: int | None = None
    num_fraud: int = Field(ge=0)
    num_legitimate: int = Field(ge=0)
    fraud_rate: float = Field(ge=0.0, le=1.0)

    # Temporal coverage
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None

    # Processing information
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "ml_pipeline"
    processing_config: dict[str, Any] = Field(default_factory=dict)

    # Data quality
    validation_passed: bool = False
    validation_report_path: str | None = None
    quality_report_path: str | None = None

    # Versioning
    parent_dataset_id: str | None = None
    data_hash: str | None = None  # SHA256 hash for integrity

    class Config:
        json_schema_extra = {
            "example": {
                "dataset_name": "creditcard_processed",
                "dataset_type": "creditcard",
                "version": "v1.0.0",
                "stage": "processed",
                "num_records": 284807,
                "num_fraud": 492,
                "num_legitimate": 284315,
                "fraud_rate": 0.00173,
                "created_by": "ml_pipeline",
                "validation_passed": True,
            }
        }


# ============================================================================
# Feature Metadata Schema
# ============================================================================


class FeatureMetadata(BaseModel):
    """Metadata for a single feature"""

    feature_name: str
    feature_type: str  # "numerical", "categorical", "binary"
    description: str
    importance: str  # "critical", "high", "medium", "low"

    # Statistical properties
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    std_value: float | None = None
    missing_rate: float = Field(ge=0.0, le=1.0)

    # Business context
    business_justification: str
    transformer_class: str

    class Config:
        json_schema_extra = {
            "example": {
                "feature_name": "amount_log",
                "feature_type": "numerical",
                "description": "Log-transformed transaction amount",
                "importance": "high",
                "min_value": 0.0,
                "max_value": 10.8,
                "mean_value": 4.5,
                "std_value": 1.2,
                "missing_rate": 0.0,
                "business_justification": "Large amounts attract fraud; log transform handles skewness",
                "transformer_class": "AmountTransformer",
            }
        }


# ============================================================================
# Pipeline Run Metadata
# ============================================================================


class PipelineRunMetadata(BaseModel):
    """Metadata for a pipeline execution"""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_name: str
    pipeline_version: str

    # Execution details
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    status: str  # "running", "success", "failed"

    # Configuration
    config: dict[str, Any] = Field(default_factory=dict)
    random_seed: int = Field(default=42)

    # Input/Output
    input_dataset_id: str | None = None
    output_dataset_id: str | None = None

    # Execution statistics
    records_processed: int = 0
    records_failed: int = 0
    processing_time_seconds: float | None = None

    # Error tracking
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "pipeline_name": "feature_engineering",
                "pipeline_version": "v1.0.0",
                "status": "success",
                "random_seed": 42,
                "records_processed": 284807,
                "records_failed": 0,
                "processing_time_seconds": 125.3,
            }
        }


# ============================================================================
# Validation Result Schema
# ============================================================================


class ValidationResult(BaseModel):
    """Result of data validation"""

    validation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dataset_id: str
    validated_at: datetime = Field(default_factory=datetime.utcnow)

    # Overall status
    passed: bool
    total_checks: int = Field(ge=0)
    passed_checks: int = Field(ge=0)
    failed_checks: int = Field(ge=0)
    warning_checks: int = Field(ge=0)

    # Check results
    check_results: list[dict[str, Any]] = Field(default_factory=list)

    # Summary
    critical_failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # Report paths
    html_report_path: str | None = None
    json_report_path: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "dataset_id": "dataset_123",
                "passed": True,
                "total_checks": 25,
                "passed_checks": 23,
                "failed_checks": 0,
                "warning_checks": 2,
                "warnings": ["Missing rate for feature X is 5%"],
            }
        }


# ============================================================================
# Train/Val/Test Split Metadata
# ============================================================================


class SplitMetadata(BaseModel):
    """Metadata for train/validation/test split"""

    split_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_dataset_id: str
    split_strategy: str  # "stratified", "time_aware", "random"
    split_date: datetime = Field(default_factory=datetime.utcnow)

    # Split ratios
    train_ratio: float = Field(gt=0.0, lt=1.0)
    val_ratio: float = Field(gt=0.0, lt=1.0)
    test_ratio: float = Field(gt=0.0, lt=1.0)

    # Split statistics
    train_size: int = Field(ge=0)
    val_size: int = Field(ge=0)
    test_size: int = Field(ge=0)

    train_fraud_rate: float = Field(ge=0.0, le=1.0)
    val_fraud_rate: float = Field(ge=0.0, le=1.0)
    test_fraud_rate: float = Field(ge=0.0, le=1.0)

    # Temporal splits
    train_date_range: tuple[datetime, datetime] | None = None
    val_date_range: tuple[datetime, datetime] | None = None
    test_date_range: tuple[datetime, datetime] | None = None

    # Random seed for reproducibility
    random_seed: int = Field(default=42)

    # Leakage prevention flags
    leakage_checks_passed: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "source_dataset_id": "dataset_123",
                "split_strategy": "time_aware",
                "train_ratio": 0.75,
                "val_ratio": 0.125,
                "test_ratio": 0.125,
                "train_size": 213605,
                "val_size": 35601,
                "test_size": 35601,
                "train_fraud_rate": 0.00172,
                "val_fraud_rate": 0.00174,
                "test_fraud_rate": 0.00175,
                "random_seed": 42,
                "leakage_checks_passed": True,
            }
        }

    @field_validator("train_ratio", "val_ratio", "test_ratio")
    @classmethod
    def validate_ratios(cls, v: float) -> float:
        """Ensure ratios are between 0 and 1"""
        if not 0 < v < 1:
            raise ValueError("Split ratios must be between 0 and 1")
        return v
