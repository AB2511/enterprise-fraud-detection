"""
Unit tests for dataset summary generation.

Tests:
- Summary generation
- JSON serialization
- Statistics calculation
"""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from ml.training.data.config import IEEECISSchema
from ml.training.data.dataset_summary import DatasetSummary, generate_dataset_summary


@pytest.fixture
def sample_dataframe():
    """Create sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "TransactionID": [1, 2, 3, 4, 5],
            "isFraud": [0, 1, 0, 0, 1],
            "TransactionAmt": [10.0, 20.0, None, 40.0, 50.0],
            "ProductCD": ["W", "W", "C", None, "H"],
            "card1": [1000, 2000, 3000, 4000, 5000],
        }
    )


class TestDatasetSummary:
    """Test DatasetSummary dataclass."""

    def test_create_summary(self):
        """Test creating a summary object."""
        summary = DatasetSummary(
            num_rows=1000,
            num_columns=50,
            memory_usage_mb=10.5,
            target_distribution={
                "total_samples": 1000,
                "fraud_cases": 35,
                "legitimate_cases": 965,
                "fraud_rate": 0.035,
            },
            missing_value_stats={
                "columns_with_missing": 10,
                "total_missing_values": 500,
                "overall_missing_rate": 0.01,
                "max_missing_rate": 0.5,
            },
            column_types={"int64": 30, "float64": 15, "object": 5},
        )

        assert summary.num_rows == 1000
        assert summary.num_columns == 50
        assert summary.memory_usage_mb == 10.5

    def test_to_dict(self):
        """Test converting summary to dictionary."""
        summary = DatasetSummary(
            num_rows=100,
            num_columns=10,
            memory_usage_mb=1.0,
            target_distribution={"fraud_rate": 0.05},
            missing_value_stats={"total_missing_values": 10},
            column_types={"int64": 5, "float64": 5},
        )

        summary_dict = summary.to_dict()

        assert isinstance(summary_dict, dict)
        assert summary_dict["num_rows"] == 100
        assert summary_dict["num_columns"] == 10
        assert "target_distribution" in summary_dict
        assert "missing_value_stats" in summary_dict

    def test_to_json(self):
        """Test saving summary to JSON file."""
        summary = DatasetSummary(
            num_rows=100,
            num_columns=10,
            memory_usage_mb=1.0,
            target_distribution={"fraud_rate": 0.05},
            missing_value_stats={"total_missing_values": 10},
            column_types={"int64": 5},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "summary.json"
            summary.to_json(output_path)

            assert output_path.exists()

            with open(output_path) as f:
                loaded_data = json.load(f)

            assert loaded_data["num_rows"] == 100
            assert loaded_data["num_columns"] == 10

    def test_str_representation(self):
        """Test string representation of summary."""
        summary = DatasetSummary(
            num_rows=1000,
            num_columns=50,
            memory_usage_mb=10.5,
            target_distribution={
                "total_samples": 1000,
                "fraud_cases": 35,
                "legitimate_cases": 965,
                "fraud_rate": 0.035,
            },
            missing_value_stats={
                "columns_with_missing": 10,
                "total_missing_values": 500,
                "overall_missing_rate": 0.01,
                "max_missing_rate": 0.5,
            },
            column_types={"int64": 30, "float64": 15},
        )

        str_summary = str(summary)

        assert "1,000" in str_summary
        assert "50" in str_summary
        assert "10.5" in str_summary
        assert "3.50%" in str_summary  # Format is .2f so 3.50% not 3.5%


class TestGenerateDatasetSummary:
    """Test dataset summary generation."""

    def test_generate_basic_summary(self, sample_dataframe):
        """Test generating summary from DataFrame."""
        summary = generate_dataset_summary(sample_dataframe)

        assert isinstance(summary, DatasetSummary)
        assert summary.num_rows == 5
        assert summary.num_columns == 5
        assert summary.memory_usage_mb > 0

    def test_generate_target_distribution(self, sample_dataframe):
        """Test target distribution calculation."""
        summary = generate_dataset_summary(sample_dataframe)

        target_dist = summary.target_distribution
        assert target_dist["total_samples"] == 5
        assert target_dist["fraud_cases"] == 2
        assert target_dist["legitimate_cases"] == 3
        assert target_dist["fraud_rate"] == 0.4

    def test_generate_missing_value_stats(self, sample_dataframe):
        """Test missing value statistics calculation."""
        summary = generate_dataset_summary(sample_dataframe)

        missing_stats = summary.missing_value_stats
        assert missing_stats["columns_with_missing"] == 2  # TransactionAmt, ProductCD
        assert missing_stats["total_missing_values"] == 2  # 1 in each column
        assert 0 < missing_stats["overall_missing_rate"] < 1
        assert 0 < missing_stats["max_missing_rate"] <= 1

    def test_generate_column_types(self, sample_dataframe):
        """Test column type counting."""
        summary = generate_dataset_summary(sample_dataframe)

        column_types = summary.column_types
        assert "int64" in column_types
        assert "float64" in column_types or "int64" in column_types
        assert "object" in column_types

    def test_generate_without_target_column(self):
        """Test generating summary without isFraud column."""
        df = pd.DataFrame(
            {
                "TransactionID": [1, 2, 3],
                "TransactionAmt": [10.0, 20.0, 30.0],
            }
        )

        summary = generate_dataset_summary(df)

        assert summary.target_distribution["fraud_cases"] == 0
        assert summary.target_distribution["fraud_rate"] == 0.0

    def test_generate_with_all_fraud(self):
        """Test generating summary with all fraud transactions."""
        df = pd.DataFrame(
            {
                "TransactionID": [1, 2, 3],
                "isFraud": [1, 1, 1],
                "TransactionAmt": [10.0, 20.0, 30.0],
            }
        )

        summary = generate_dataset_summary(df)

        assert summary.target_distribution["fraud_cases"] == 3
        assert summary.target_distribution["legitimate_cases"] == 0
        assert summary.target_distribution["fraud_rate"] == 1.0

    def test_generate_with_no_missing_values(self):
        """Test generating summary with no missing values."""
        df = pd.DataFrame(
            {
                "TransactionID": [1, 2, 3],
                "isFraud": [0, 1, 0],
                "TransactionAmt": [10.0, 20.0, 30.0],
            }
        )

        summary = generate_dataset_summary(df)

        missing_stats = summary.missing_value_stats
        assert missing_stats["columns_with_missing"] == 0
        assert missing_stats["total_missing_values"] == 0
        assert missing_stats["overall_missing_rate"] == 0.0
        assert missing_stats["max_missing_rate"] == 0.0

    def test_generate_with_custom_schema(self, sample_dataframe):
        """Test generating summary with custom schema."""
        custom_schema = IEEECISSchema()
        summary = generate_dataset_summary(sample_dataframe, schema=custom_schema)

        assert isinstance(summary, DatasetSummary)
        assert summary.num_rows == 5

    def test_generate_memory_calculation(self):
        """Test memory usage calculation."""
        # Create DataFrame with known size
        large_df = pd.DataFrame(
            {
                "col1": range(10000),
                "col2": [f"string_{i}" for i in range(10000)],
                "col3": [float(i) for i in range(10000)],
            }
        )

        summary = generate_dataset_summary(large_df)

        # Memory should be positive and reasonable
        assert summary.memory_usage_mb > 0
        assert summary.memory_usage_mb < 1000  # Shouldn't be gigabytes
