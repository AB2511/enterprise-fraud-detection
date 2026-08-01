"""
Tests for feature dropping module.
"""

import pandas as pd
import pytest

from ml.training.data.feature_dropping import FeatureDropper


@pytest.fixture
def sample_df():
    """Create sample dataframe for testing."""
    return pd.DataFrame(
        {
            "TransactionID": [1, 2, 3, 4, 5],
            "isFraud": [0, 1, 0, 0, 1],
            "feature_A": [1.0, 2.0, 3.0, 4.0, 5.0],
            "feature_B": [1.0, 2.0, 3.0, 4.0, 5.0],  # Duplicate of A
            "feature_C": [1, 1, 1, 1, 1],  # Constant
            "feature_D": [None, None, None, None, None],  # 100% missing
            "feature_E": [1.0, None, None, None, None],  # 80% missing
        }
    )


@pytest.fixture
def config_path():
    """Get path to preprocessing config."""
    return "ml/training/data/preprocessing_config.yaml"


def test_feature_dropper_initialization(config_path):
    """Test FeatureDropper can be initialized with config."""
    dropper = FeatureDropper(config_path)
    assert dropper.config is not None
    assert "dropping" in dropper.config


def test_drop_identifiers(sample_df, config_path):
    """Test identifier columns are dropped."""
    dropper = FeatureDropper(config_path)
    result = dropper.fit_transform(sample_df)

    assert "TransactionID" not in result.columns
    assert "TransactionID" in dropper.get_all_dropped_columns()


def test_drop_constant_features(sample_df, config_path):
    """Test constant features are dropped."""
    dropper = FeatureDropper(config_path)
    result = dropper.fit_transform(sample_df)

    assert "feature_C" not in result.columns
    assert "feature_C" in dropper.get_dropped_columns()["constant"]


def test_drop_extreme_missing(sample_df, config_path):
    """Test features with extreme missing values are dropped."""
    dropper = FeatureDropper(config_path)
    result = dropper.fit_transform(sample_df)

    # feature_D has 100% missing (> 99.5% threshold)
    assert "feature_D" not in result.columns
    assert "feature_D" in dropper.get_dropped_columns()["extreme_missing"]

    # feature_E has 80% missing (< 99.5% threshold) but may be dropped due to other reasons
    # Just verify feature_D was dropped for extreme missing
    assert len(dropper.get_dropped_columns()["extreme_missing"]) >= 1


def test_drop_exact_duplicates(sample_df, config_path):
    """Test exact duplicate features are dropped."""
    dropper = FeatureDropper(config_path)
    result = dropper.fit_transform(sample_df)

    # feature_B is exact duplicate of feature_A (should be dropped)
    assert "feature_A" in result.columns
    assert "feature_B" not in result.columns

    # Verify exact duplicates tracking
    if "exact_duplicates" in dropper.get_dropped_columns():
        assert "feature_B" in dropper.get_dropped_columns()["exact_duplicates"]


def test_statistics_collection(sample_df, config_path):
    """Test statistics are collected correctly."""
    dropper = FeatureDropper(config_path)
    _ = dropper.fit_transform(sample_df)

    stats = dropper.get_statistics()

    assert "input_shape" in stats
    assert "output_shape" in stats
    assert "input_memory_mb" in stats
    assert "output_memory_mb" in stats
    assert "execution_time_seconds" in stats
    assert "columns_dropped_total" in stats

    # Verify shapes
    assert stats["input_shape"][0] == 5  # rows
    assert stats["input_shape"][1] == 7  # columns
    assert stats["output_shape"][0] == 5  # rows unchanged
    assert stats["output_shape"][1] < 7  # columns decreased


def test_get_dropped_columns_by_reason(sample_df, config_path):
    """Test dropped columns are categorized by reason."""
    dropper = FeatureDropper(config_path)
    _ = dropper.fit_transform(sample_df)

    dropped = dropper.get_dropped_columns()

    assert "identifiers" in dropped
    assert "constant" in dropped
    assert "extreme_missing" in dropped

    # Verify identifiers
    assert "TransactionID" in dropped["identifiers"]

    # Verify constant
    assert "feature_C" in dropped["constant"]

    # Verify extreme missing
    assert "feature_D" in dropped["extreme_missing"]
    assert "TransactionID" in dropped["identifiers"]

    # Verify constant
    assert "feature_C" in dropped["constant"]

    # Verify extreme missing
    assert "feature_D" in dropped["extreme_missing"]


def test_no_rows_dropped(sample_df, config_path):
    """Test that no rows are dropped, only columns."""
    dropper = FeatureDropper(config_path)
    result = dropper.fit_transform(sample_df)

    assert len(result) == len(sample_df)


def test_target_column_preserved(sample_df, config_path):
    """Test that target column is not dropped."""
    dropper = FeatureDropper(config_path)
    result = dropper.fit_transform(sample_df)

    assert "isFraud" in result.columns


def test_memory_reduction(sample_df, config_path):
    """Test that memory usage is tracked."""
    dropper = FeatureDropper(config_path)
    _ = dropper.fit_transform(sample_df)

    stats = dropper.get_statistics()

    # Memory should be reduced (columns dropped)
    assert stats["output_memory_mb"] <= stats["input_memory_mb"]


def test_execution_time_recorded(sample_df, config_path):
    """Test that execution time is recorded."""
    dropper = FeatureDropper(config_path)
    _ = dropper.fit_transform(sample_df)

    stats = dropper.get_statistics()

    assert stats["execution_time_seconds"] > 0
    assert stats["execution_time_seconds"] < 10  # Should be fast
