"""
Testing Fixtures

Reusable fixtures for ML pipeline testing.
"""

import json
import shutil
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.utils.config import DatasetConfig, PipelineConfig, ValidationConfig
from ml.utils.metadata import DatasetMetadata, FeatureMetadata, PipelineRunMetadata
from ml.validation.validators import ValidationCheck


class MockDatasetGenerator:
    """Generate mock datasets for testing"""

    def __init__(self, seed: int = 42):
        """Initialize with random seed"""
        self.rng = np.random.RandomState(seed)

    def generate_transaction_data(
        self,
        n_rows: int = 1000,
        fraud_rate: float = 0.02,
        include_missing: bool = True,
        missing_rate: float = 0.05,
    ) -> pd.DataFrame:
        """
        Generate mock transaction dataset.

        Args:
            n_rows: Number of rows
            fraud_rate: Fraction of fraudulent transactions
            include_missing: Whether to include missing values
            missing_rate: Fraction of missing values per column

        Returns:
            Mock transaction DataFrame
        """
        # Base transaction features
        data = {
            "transaction_id": [f"txn_{uuid.uuid4().hex[:8]}" for _ in range(n_rows)],
            "user_id": self.rng.randint(1000, 9999, n_rows),
            "merchant_id": self.rng.randint(100, 999, n_rows),
            "amount": self.rng.lognormal(3, 1, n_rows).round(2),
            "timestamp": pd.date_range(start="2024-01-01", periods=n_rows, freq="5min"),
        }

        # Derived features
        timestamp_series = pd.to_datetime(data["timestamp"])
        data["hour"] = timestamp_series.hour.tolist()  # Convert to list for mutability
        data["day_of_week"] = timestamp_series.dayofweek.tolist()  # Convert to list
        data["amount_log"] = np.log1p(data["amount"]).tolist()

        # Categorical features
        data["payment_method"] = self.rng.choice(
            ["credit_card", "debit_card", "paypal", "bank_transfer"], n_rows, p=[0.4, 0.3, 0.2, 0.1]
        )

        data["merchant_category"] = self.rng.choice(
            ["grocery", "gas", "restaurant", "retail", "online"],
            n_rows,
            p=[0.25, 0.15, 0.2, 0.25, 0.15],
        )

        data["country"] = self.rng.choice(
            ["US", "CA", "UK", "FR", "DE"], n_rows, p=[0.5, 0.15, 0.15, 0.1, 0.1]
        )

        # Boolean features (convert to lists for mutability)
        data["is_weekend"] = (timestamp_series.dayofweek >= 5).tolist()
        data["is_night"] = ((timestamp_series.hour >= 22) | (timestamp_series.hour <= 6)).tolist()

        # Target variable (fraud)
        n_fraud = int(n_rows * fraud_rate)
        fraud_indices = self.rng.choice(n_rows, n_fraud, replace=False)
        data["is_fraud"] = [False] * n_rows  # Create list instead of scalar
        for idx in fraud_indices:
            data["is_fraud"][idx] = True

        # Make fraud transactions look suspicious
        for idx in fraud_indices:
            # Higher amounts
            if self.rng.random() < 0.6:
                data["amount"][idx] *= self.rng.uniform(2, 10)
            # More likely at night
            if self.rng.random() < 0.4:
                new_hour = self.rng.choice([23, 0, 1, 2, 3])
                data["hour"][idx] = new_hour
                data["is_night"][idx] = True
            # Different countries
            if self.rng.random() < 0.3:
                data["country"][idx] = self.rng.choice(["RU", "CN", "BR"])

        df = pd.DataFrame(data)

        # Add missing values
        if include_missing:
            for col in ["merchant_category", "country", "payment_method"]:
                if col in df.columns:
                    n_missing = int(len(df) * missing_rate)
                    missing_indices = self.rng.choice(len(df), n_missing, replace=False)
                    df.loc[missing_indices, col] = None

        return df

    def generate_user_data(self, n_users: int = 500) -> pd.DataFrame:
        """Generate mock user dataset"""
        data = {
            "user_id": range(1000, 1000 + n_users),
            "age": self.rng.randint(18, 80, n_users),
            "income": self.rng.lognormal(10, 0.5, n_users).round(0),
            "credit_score": self.rng.randint(300, 850, n_users),
            "account_age_days": self.rng.randint(1, 3650, n_users),
            "num_transactions_30d": self.rng.poisson(15, n_users),
            "avg_transaction_amount": self.rng.lognormal(3, 0.8, n_users).round(2),
        }

        return pd.DataFrame(data)

    def generate_merchant_data(self, n_merchants: int = 200) -> pd.DataFrame:
        """Generate mock merchant dataset"""
        data = {
            "merchant_id": range(100, 100 + n_merchants),
            "merchant_name": [f"Merchant {i}" for i in range(n_merchants)],
            "category": self.rng.choice(
                ["grocery", "gas", "restaurant", "retail", "online"], n_merchants
            ),
            "risk_score": self.rng.uniform(0, 1, n_merchants).round(3),
            "transactions_per_day": self.rng.poisson(50, n_merchants),
            "avg_transaction_amount": self.rng.lognormal(3, 0.6, n_merchants).round(2),
        }

        return pd.DataFrame(data)


@pytest.fixture
def mock_dataset_generator():
    """Fixture for MockDatasetGenerator"""
    return MockDatasetGenerator(seed=42)


@pytest.fixture
def sample_transaction_data(mock_dataset_generator):
    """Fixture for sample transaction data"""
    return mock_dataset_generator.generate_transaction_data(n_rows=100)


@pytest.fixture
def sample_user_data(mock_dataset_generator):
    """Fixture for sample user data"""
    return mock_dataset_generator.generate_user_data(n_users=50)


@pytest.fixture
def sample_merchant_data(mock_dataset_generator):
    """Fixture for sample merchant data"""
    return mock_dataset_generator.generate_merchant_data(n_merchants=20)


@pytest.fixture
def temp_directory():
    """Fixture for temporary directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_data_directory(temp_directory):
    """Fixture for temporary data directory structure"""
    data_dir = temp_directory / "data"

    # Create standard directory structure
    directories = [
        "raw/creditcard",
        "raw/ieee-cis",
        "interim/cleaned",
        "interim/validated",
        "processed/train",
        "processed/val",
        "processed/test",
        "external",
        "feature_store",
        "validation",
        "reports",
        "metadata/datasets",
        "metadata/features",
        "metadata/pipelines",
        "metadata/validations",
        "metadata/splits",
        "metadata/lineage",
        "metadata/statistics",
        "metadata/history",
    ]

    for directory in directories:
        (data_dir / directory).mkdir(parents=True, exist_ok=True)

    return data_dir


def create_mock_dataframe(
    n_rows: int = 100,
    n_cols: int = 5,
    include_nulls: bool = True,
    include_duplicates: bool = False,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Create mock DataFrame for testing.

    Args:
        n_rows: Number of rows
        n_cols: Number of columns
        include_nulls: Whether to include null values
        include_duplicates: Whether to include duplicate rows
        seed: Random seed

    Returns:
        Mock DataFrame
    """
    rng = np.random.RandomState(seed)

    # Generate base data
    data = {}
    for i in range(n_cols):
        if i == 0:
            # ID column
            data[f"col_{i}"] = [f"id_{j:04d}" for j in range(n_rows)]
        elif i % 3 == 1:
            # Numeric column
            data[f"col_{i}"] = rng.randn(n_rows) * 100
        elif i % 3 == 2:
            # Integer column
            data[f"col_{i}"] = rng.randint(0, 100, n_rows)
        else:
            # Categorical column
            categories = [f"cat_{k}" for k in range(5)]
            data[f"col_{i}"] = rng.choice(categories, n_rows)

    df = pd.DataFrame(data)

    # Add nulls
    if include_nulls and n_cols > 1:
        null_col = f"col_{1}"
        n_nulls = max(1, n_rows // 10)
        null_indices = rng.choice(n_rows, n_nulls, replace=False)
        df.loc[null_indices, null_col] = None

    # Add duplicates
    if include_duplicates and n_rows > 5:
        n_dups = max(1, n_rows // 20)
        dup_indices = rng.choice(n_rows - n_dups, n_dups, replace=False)
        for i, idx in enumerate(dup_indices):
            df.iloc[idx + i + 1] = df.iloc[idx]

    return df


def create_mock_metadata(
    dataset_name: str = "test_dataset",
    version_id: str = "20240707_120000_test",
) -> DatasetMetadata:
    """
    Create mock dataset metadata.

    Args:
        dataset_name: Dataset name
        version_id: Version ID

    Returns:
        Mock DatasetMetadata
    """
    return DatasetMetadata(
        dataset_name=dataset_name,
        version_id=version_id,
        created_at=datetime.utcnow(),
        source="mock_source",
        file_path=f"data/processed/{dataset_name}/{version_id}.parquet",
        file_size_bytes=1024 * 1024,
        checksum="abc123def456",
        schema_version="v1.0.0",
        preprocessing_version="v1.0.0",
        row_count=1000,
        column_count=10,
        null_count=50,
        duplicate_count=5,
        quality_score=0.95,
        column_info={
            "transaction_id": {"dtype": "object", "null_count": 0, "unique_count": 1000},
            "amount": {"dtype": "float64", "null_count": 0, "min": 0.01, "max": 9999.99},
            "is_fraud": {"dtype": "bool", "null_count": 0, "true_count": 20},
        },
        statistics={
            "mean_amount": 156.78,
            "fraud_rate": 0.02,
            "missing_rate": 0.05,
        },
        tags=["mock", "test", "fraud_detection"],
        parent_version_id=None,
    )


def create_mock_feature_metadata(
    feature_name: str = "test_feature",
) -> FeatureMetadata:
    """Create mock feature metadata"""
    return FeatureMetadata(
        feature_name=feature_name,
        data_type="float64",
        description=f"Mock feature: {feature_name}",
        source_columns=["raw_col_1", "raw_col_2"],
        transformation="log_transform",
        importance_score=0.75,
        null_percentage=0.02,
        unique_values=None,
        min_value=0.0,
        max_value=100.0,
        mean_value=45.6,
        std_value=12.3,
        created_at=datetime.utcnow(),
        tags=["mock", "test"],
    )


def create_mock_pipeline_metadata(
    pipeline_name: str = "test_pipeline",
    run_id: str = None,
) -> PipelineRunMetadata:
    """Create mock pipeline run metadata"""
    if run_id is None:
        run_id = f"run_{uuid.uuid4().hex[:8]}"

    return PipelineRunMetadata(
        pipeline_name=pipeline_name,
        run_id=run_id,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow() + timedelta(minutes=5),
        status="success",
        config_hash="config_hash_123",
        input_datasets=["dataset_v1"],
        output_datasets=["dataset_v2"],
        metrics={
            "processing_time_seconds": 300,
            "rows_processed": 10000,
            "validation_passed": True,
        },
        git_commit="abc123def456",
        environment_snapshot={
            "python_version": "3.9.0",
            "pandas_version": "1.3.0",
            "numpy_version": "1.21.0",
        },
    )


def create_mock_validation_results(
    n_checks: int = 5,
    n_passed: int = 4,
) -> list[ValidationCheck]:
    """
    Create mock validation results.

    Args:
        n_checks: Total number of checks
        n_passed: Number of passed checks

    Returns:
        List of ValidationCheck objects
    """
    checks = []

    for i in range(n_checks):
        passed = i < n_passed
        severity = "info" if passed else "error"

        check = ValidationCheck(
            validator_name="MockValidator",
            check_name=f"check_{i}",
            passed=passed,
            severity=severity,
            message=f"Mock check {i} {'passed' if passed else 'failed'}",
            expected_value="expected",
            actual_value="actual" if passed else "different",
            column="test_column" if i % 2 == 0 else None,
        )
        checks.append(check)

    return checks


def create_mock_config(
    dataset_name: str = "test_dataset",
    dataset_type: str = "creditcard",
) -> PipelineConfig:
    """Create mock pipeline configuration"""
    return PipelineConfig(
        pipeline_name="test_pipeline",
        random_seed=42,
        dataset=DatasetConfig(
            dataset_name=dataset_name,
            dataset_type=dataset_type,
            source_path=Path(f"data/raw/{dataset_type}/{dataset_name}.csv"),
            target_column="is_fraud",
            datetime_column="timestamp",
            id_column="transaction_id",
            categorical_columns=["payment_method", "merchant_category"],
            numerical_columns=["amount", "user_age"],
            drop_columns=["internal_id"],
        ),
        validation=ValidationConfig(
            missing_threshold=0.1,
            duplicate_threshold=0.05,
            outlier_threshold=3.0,
            schema_strict=True,
            enable_data_drift=False,
        ),
    )


@pytest.fixture
def mock_dataframe():
    """Fixture for mock DataFrame"""
    return create_mock_dataframe()


@pytest.fixture
def mock_metadata():
    """Fixture for mock metadata"""
    return create_mock_metadata()


@pytest.fixture
def mock_feature_metadata():
    """Fixture for mock feature metadata"""
    return create_mock_feature_metadata()


@pytest.fixture
def mock_pipeline_metadata():
    """Fixture for mock pipeline metadata"""
    return create_mock_pipeline_metadata()


@pytest.fixture
def mock_validation_results():
    """Fixture for mock validation results"""
    return create_mock_validation_results()


@pytest.fixture
def mock_config():
    """Fixture for mock configuration"""
    return create_mock_config()


@pytest.fixture
def sample_csv_data(temp_directory):
    """Fixture for sample CSV file"""
    df = create_mock_dataframe(n_rows=50)
    csv_path = temp_directory / "sample.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_parquet_data(temp_directory):
    """Fixture for sample Parquet file"""
    df = create_mock_dataframe(n_rows=50)
    parquet_path = temp_directory / "sample.parquet"
    df.to_parquet(parquet_path, index=False)
    return parquet_path


@pytest.fixture
def sample_json_data(temp_directory):
    """Fixture for sample JSON file"""
    data = {"key": "value", "number": 42, "list": [1, 2, 3]}
    json_path = temp_directory / "sample.json"
    with open(json_path, "w") as f:
        json.dump(data, f)
    return json_path
