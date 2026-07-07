"""
Configuration System

Typed configuration objects for ML pipeline with:
- Path configuration
- Dataset configuration
- Validation configuration
- Feature generation configuration
- Splitting configuration
- Export configuration
- Environment variable overrides
"""

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# Path Configuration
# ============================================================================


class PathConfig(BaseModel):
    """Path configuration for ML pipeline"""

    # Root directories
    project_root: Path = Field(default=Path("."))
    data_root: Path = Field(default=Path("data"))
    ml_root: Path = Field(default=Path("ml"))

    # Data directories
    raw_data_dir: Path = Field(default=Path("data/raw"))
    interim_data_dir: Path = Field(default=Path("data/interim"))
    processed_data_dir: Path = Field(default=Path("data/processed"))
    external_data_dir: Path = Field(default=Path("data/external"))
    feature_store_dir: Path = Field(default=Path("data/feature_store"))

    # Output directories
    validation_dir: Path = Field(default=Path("data/validation"))
    reports_dir: Path = Field(default=Path("data/reports"))
    metadata_dir: Path = Field(default=Path("data/metadata"))

    # Logs
    logs_dir: Path = Field(default=Path("logs"))

    class Config:
        frozen = True  # Immutable

    def ensure_directories(self) -> None:
        """Create all configured directories"""
        for field_name, field_value in self.model_dump().items():
            if isinstance(field_value, Path):
                field_value.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Dataset Configuration
# ============================================================================


class DatasetConfig(BaseModel):
    """Dataset configuration"""

    dataset_name: str
    dataset_type: str  # "creditcard", "ieee-cis", etc.
    source_path: Path

    # Loading options
    file_format: str = Field(default="csv")  # "csv", "parquet"
    chunksize: int | None = Field(default=None)
    nrows: int | None = Field(default=None)  # For testing on subset

    # Schema options
    schema_version: str = Field(default="v1.0.0")
    expected_columns: list[str] | None = None

    # Preprocessing options
    preprocessing_version: str = Field(default="v1.0.0")
    drop_duplicates: bool = Field(default=True)
    handle_missing: bool = Field(default=True)

    class Config:
        frozen = True


# ============================================================================
# Validation Configuration
# ============================================================================


class ValidationConfig(BaseModel):
    """Data validation configuration"""

    # Validation strictness
    fail_on_error: bool = Field(default=True)
    fail_on_warning: bool = Field(default=False)

    # Missing value thresholds
    max_missing_rate_critical: float = Field(default=0.05, ge=0.0, le=1.0)
    max_missing_rate_important: float = Field(default=0.10, ge=0.0, le=1.0)
    max_missing_rate_optional: float = Field(default=0.30, ge=0.0, le=1.0)

    # Duplicate detection
    check_duplicates: bool = Field(default=True)
    duplicate_threshold: float = Field(default=0.01, ge=0.0, le=1.0)

    # Range validation
    check_ranges: bool = Field(default=True)

    # Timestamp validation
    check_timestamp_ordering: bool = Field(default=True)
    allow_future_timestamps: bool = Field(default=False)

    # Target distribution
    min_fraud_rate: float = Field(default=0.001, ge=0.0, le=1.0)
    max_fraud_rate: float = Field(default=0.10, ge=0.0, le=1.0)

    # Report generation
    generate_html_report: bool = Field(default=True)
    generate_json_report: bool = Field(default=True)

    class Config:
        frozen = True


# ============================================================================
# Feature Generation Configuration
# ============================================================================


class FeatureConfig(BaseModel):
    """Feature generation configuration"""

    feature_version: str = Field(default="v1.0.0")

    # Feature groups to generate
    generate_amount_features: bool = Field(default=True)
    generate_velocity_features: bool = Field(default=True)
    generate_merchant_features: bool = Field(default=True)
    generate_customer_features: bool = Field(default=True)
    generate_temporal_features: bool = Field(default=True)
    generate_device_features: bool = Field(default=True)
    generate_geo_features: bool = Field(default=True)

    # Velocity windows (in hours)
    velocity_windows: list[int] = Field(default=[1, 24, 168])  # 1h, 24h, 7d

    # Aggregation windows (in days)
    aggregation_windows: list[int] = Field(default=[7, 30, 90])

    # Feature selection
    min_feature_importance: float | None = None
    max_correlation: float = Field(default=0.95, ge=0.0, le=1.0)

    # Missing value handling
    impute_missing: bool = Field(default=True)
    imputation_strategy: str = Field(default="median")  # "median", "mean", "mode"

    class Config:
        frozen = True


# ============================================================================
# Splitting Configuration
# ============================================================================


class SplitConfig(BaseModel):
    """Train/validation/test split configuration"""

    # Split strategy
    strategy: str = Field(default="stratified")  # "stratified", "time_aware", "random"

    # Split ratios
    train_ratio: float = Field(default=0.75, gt=0.0, lt=1.0)
    val_ratio: float = Field(default=0.125, gt=0.0, lt=1.0)
    test_ratio: float = Field(default=0.125, gt=0.0, lt=1.0)

    # Stratification
    stratify_by_target: bool = Field(default=True)
    stratify_by_time: bool = Field(default=False)

    # Random seed
    random_seed: int = Field(default=42)

    # Validation
    ensure_fraud_in_all_splits: bool = Field(default=True)
    min_samples_per_split: int = Field(default=1000)

    @field_validator("train_ratio", "val_ratio", "test_ratio")
    @classmethod
    def validate_ratios(cls, v: float) -> float:
        if not 0 < v < 1:
            raise ValueError("Split ratios must be between 0 and 1")
        return v

    class Config:
        frozen = True


# ============================================================================
# Export Configuration
# ============================================================================


class ExportConfig(BaseModel):
    """Data export configuration"""

    # Export formats
    export_parquet: bool = Field(default=True)
    export_csv: bool = Field(default=False)
    export_json: bool = Field(default=False)

    # Compression
    compression: str | None = Field(default="snappy")  # "snappy", "gzip", "brotli"

    # Partitioning
    partition_by: list[str] | None = None  # e.g., ["year", "month"]

    # File naming
    include_timestamp: bool = Field(default=True)
    include_version: bool = Field(default=True)

    # Metadata
    save_metadata: bool = Field(default=True)
    save_schema: bool = Field(default=True)
    save_statistics: bool = Field(default=True)

    class Config:
        frozen = True


# ============================================================================
# Master Pipeline Configuration
# ============================================================================


class PipelineConfig(BaseModel):
    """Master pipeline configuration"""

    pipeline_name: str
    pipeline_version: str = Field(default="v1.0.0")

    # Sub-configurations
    paths: PathConfig = Field(default_factory=PathConfig)
    dataset: DatasetConfig | None = None
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    features: FeatureConfig = Field(default_factory=FeatureConfig)
    splitting: SplitConfig = Field(default_factory=SplitConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)

    # Execution options
    random_seed: int = Field(default=42)
    num_workers: int = Field(default=1)
    verbose: bool = Field(default=True)

    # Reproducibility
    capture_environment: bool = Field(default=True)
    save_config_snapshot: bool = Field(default=True)

    def save(self, path: Path) -> None:
        """Save configuration to JSON file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> "PipelineConfig":
        """Load configuration from JSON file"""
        with open(path) as f:
            data = json.load(f)

        return cls(**data)

    @classmethod
    def from_env(cls, pipeline_name: str, **overrides) -> "PipelineConfig":
        """
        Create configuration with environment variable overrides.

        Environment variables:
        - ML_RANDOM_SEED: Override random seed
        - ML_DATA_ROOT: Override data root path
        - ML_NUM_WORKERS: Override number of workers
        """
        config_dict = {
            "pipeline_name": pipeline_name,
            "random_seed": int(os.getenv("ML_RANDOM_SEED", "42")),
            "num_workers": int(os.getenv("ML_NUM_WORKERS", "1")),
        }

        # Path overrides
        if data_root := os.getenv("ML_DATA_ROOT"):
            config_dict["paths"] = {"data_root": Path(data_root)}

        # Apply explicit overrides
        config_dict.update(overrides)

        return cls(**config_dict)


# ============================================================================
# Configuration Factory
# ============================================================================


def create_default_config(pipeline_name: str) -> PipelineConfig:
    """
    Create default pipeline configuration.

    Args:
        pipeline_name: Name of the pipeline

    Returns:
        PipelineConfig with default settings
    """
    return PipelineConfig(pipeline_name=pipeline_name)


def create_dataset_config(
    dataset_name: str, dataset_type: str, source_path: Path, **kwargs
) -> DatasetConfig:
    """
    Create dataset configuration.

    Args:
        dataset_name: Dataset name
        dataset_type: Dataset type
        source_path: Path to source data
        **kwargs: Additional configuration options

    Returns:
        DatasetConfig
    """
    return DatasetConfig(
        dataset_name=dataset_name, dataset_type=dataset_type, source_path=source_path, **kwargs
    )
