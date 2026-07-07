"""
Testing Assertions

Helper assertions for ML pipeline testing.
"""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.utils.metadata import DatasetMetadata, FeatureMetadata, PipelineRunMetadata
from ml.validation.validators import ValidationCheck


def assert_dataframe_equal(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    check_dtype: bool = True,
    check_index_type: bool = True,
    check_column_type: bool = True,
    check_names: bool = True,
    rtol: float = 1e-5,
    atol: float = 1e-8,
) -> None:
    """
    Assert that two DataFrames are equal with detailed error messages.

    Args:
        df1: First DataFrame
        df2: Second DataFrame
        check_dtype: Whether to check data types
        check_index_type: Whether to check index types
        check_column_type: Whether to check column types
        check_names: Whether to check names
        rtol: Relative tolerance for numeric comparison
        atol: Absolute tolerance for numeric comparison

    Raises:
        AssertionError: If DataFrames are not equal
    """
    # Check shapes
    assert df1.shape == df2.shape, f"DataFrame shapes differ: {df1.shape} != {df2.shape}"

    # Check columns
    if not df1.columns.equals(df2.columns):
        missing_in_df2 = set(df1.columns) - set(df2.columns)
        missing_in_df1 = set(df2.columns) - set(df1.columns)

        error_msg = "Column names differ:"
        if missing_in_df2:
            error_msg += f"\n  Missing in df2: {list(missing_in_df2)}"
        if missing_in_df1:
            error_msg += f"\n  Missing in df1: {list(missing_in_df1)}"

        raise AssertionError(error_msg)

    # Check each column
    for col in df1.columns:
        col1 = df1[col]
        col2 = df2[col]

        # Check data types
        if check_dtype and col1.dtype != col2.dtype:
            raise AssertionError(f"Column '{col}' dtypes differ: {col1.dtype} != {col2.dtype}")

        # Check values
        if pd.api.types.is_numeric_dtype(col1):
            # Numeric comparison with tolerance
            if not np.allclose(col1, col2, rtol=rtol, atol=atol, equal_nan=True):
                raise AssertionError(f"Column '{col}' numeric values differ beyond tolerance")
        else:
            # Exact comparison for non-numeric
            if not col1.equals(col2):
                # Find differing rows
                diff_mask = col1 != col2
                if diff_mask.any():
                    diff_indices = diff_mask[diff_mask].index[:5]  # Show first 5
                    diff_values = [
                        f"  Row {i}: '{col1.iloc[i]}' != '{col2.iloc[i]}'" for i in diff_indices
                    ]

                    raise AssertionError(
                        f"Column '{col}' values differ:\n" + "\n".join(diff_values)
                    )

    # Check index
    if check_index_type and not df1.index.equals(df2.index):
        raise AssertionError("DataFrame indices differ")


def assert_dataframe_schema(
    df: pd.DataFrame,
    expected_columns: list[str],
    expected_dtypes: dict[str, str] | None = None,
    allow_extra_columns: bool = False,
) -> None:
    """
    Assert DataFrame schema matches expectations.

    Args:
        df: DataFrame to check
        expected_columns: List of expected column names
        expected_dtypes: Dict of expected data types
        allow_extra_columns: Whether to allow extra columns

    Raises:
        AssertionError: If schema doesn't match
    """
    # Check required columns
    missing_cols = set(expected_columns) - set(df.columns)
    if missing_cols:
        raise AssertionError(f"Missing required columns: {list(missing_cols)}")

    # Check for extra columns
    if not allow_extra_columns:
        extra_cols = set(df.columns) - set(expected_columns)
        if extra_cols:
            raise AssertionError(f"Unexpected columns: {list(extra_cols)}")

    # Check data types
    if expected_dtypes:
        for col, expected_dtype in expected_dtypes.items():
            if col in df.columns:
                actual_dtype = str(df[col].dtype)
                if actual_dtype != expected_dtype:
                    raise AssertionError(
                        f"Column '{col}' dtype mismatch: "
                        f"expected {expected_dtype}, got {actual_dtype}"
                    )


def assert_dataframe_not_empty(df: pd.DataFrame) -> None:
    """Assert DataFrame is not empty"""
    assert not df.empty, "DataFrame is empty"


def assert_dataframe_no_nulls(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> None:
    """
    Assert DataFrame has no null values.

    Args:
        df: DataFrame to check
        columns: Specific columns to check (default: all)

    Raises:
        AssertionError: If null values found
    """
    check_cols = columns or df.columns

    for col in check_cols:
        if col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                raise AssertionError(f"Column '{col}' has {null_count} null values")


def assert_dataframe_no_duplicates(
    df: pd.DataFrame,
    subset: list[str] | None = None,
) -> None:
    """
    Assert DataFrame has no duplicate rows.

    Args:
        df: DataFrame to check
        subset: Columns to check for duplicates

    Raises:
        AssertionError: If duplicates found
    """
    duplicate_count = df.duplicated(subset=subset).sum()
    if duplicate_count > 0:
        raise AssertionError(f"Found {duplicate_count} duplicate rows")


def assert_dataframe_range(
    df: pd.DataFrame,
    column: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> None:
    """
    Assert DataFrame column values are within range.

    Args:
        df: DataFrame to check
        column: Column name
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Raises:
        AssertionError: If values are out of range
    """
    if column not in df.columns:
        raise AssertionError(f"Column '{column}' not found")

    col_values = df[column].dropna()

    if min_value is not None:
        below_min = (col_values < min_value).sum()
        if below_min > 0:
            raise AssertionError(f"Column '{column}' has {below_min} values below {min_value}")

    if max_value is not None:
        above_max = (col_values > max_value).sum()
        if above_max > 0:
            raise AssertionError(f"Column '{column}' has {above_max} values above {max_value}")


def assert_metadata_valid(
    metadata: DatasetMetadata | FeatureMetadata | PipelineRunMetadata,
    required_fields: list[str] | None = None,
) -> None:
    """
    Assert metadata object is valid.

    Args:
        metadata: Metadata object to check
        required_fields: Required field names

    Raises:
        AssertionError: If metadata is invalid
    """
    # Check required fields
    if required_fields:
        for field in required_fields:
            if not hasattr(metadata, field):
                raise AssertionError(f"Missing required field: '{field}'")

            value = getattr(metadata, field)
            if value is None:
                raise AssertionError(f"Required field '{field}' is None")

    # Type-specific validation
    if isinstance(metadata, DatasetMetadata):
        assert metadata.row_count >= 0, "Row count must be non-negative"
        assert metadata.column_count >= 0, "Column count must be non-negative"
        assert 0 <= metadata.quality_score <= 1, "Quality score must be in [0, 1]"

    elif isinstance(metadata, FeatureMetadata):
        assert metadata.feature_name, "Feature name cannot be empty"
        if metadata.importance_score is not None:
            assert 0 <= metadata.importance_score <= 1, "Importance score must be in [0, 1]"

    elif isinstance(metadata, PipelineRunMetadata):
        assert metadata.pipeline_name, "Pipeline name cannot be empty"
        assert metadata.run_id, "Run ID cannot be empty"


def assert_validation_passed(
    validation_results: list[ValidationCheck],
    min_passed_rate: float = 1.0,
) -> None:
    """
    Assert validation checks passed at required rate.

    Args:
        validation_results: List of validation checks
        min_passed_rate: Minimum pass rate (0.0 to 1.0)

    Raises:
        AssertionError: If pass rate is below threshold
    """
    if not validation_results:
        raise AssertionError("No validation results provided")

    total_checks = len(validation_results)
    passed_checks = sum(1 for check in validation_results if check.passed)
    pass_rate = passed_checks / total_checks

    if pass_rate < min_passed_rate:
        failed_checks = [
            f"  - {check.validator_name}.{check.check_name}: {check.message}"
            for check in validation_results
            if not check.passed
        ]

        raise AssertionError(
            f"Validation pass rate {pass_rate:.2%} below threshold {min_passed_rate:.2%}\n"
            f"Failed checks:\n" + "\n".join(failed_checks[:5])  # Show first 5
        )


def assert_validation_all_passed(validation_results: list[ValidationCheck]) -> None:
    """Assert all validation checks passed"""
    assert_validation_passed(validation_results, min_passed_rate=1.0)


def assert_file_exists(file_path: Path, message: str | None = None) -> None:
    """
    Assert file exists.

    Args:
        file_path: Path to file
        message: Custom error message

    Raises:
        AssertionError: If file doesn't exist
    """
    if not file_path.exists():
        error_msg = message or f"File does not exist: {file_path}"
        raise AssertionError(error_msg)


def assert_file_not_empty(file_path: Path) -> None:
    """
    Assert file exists and is not empty.

    Args:
        file_path: Path to file

    Raises:
        AssertionError: If file doesn't exist or is empty
    """
    assert_file_exists(file_path)

    if file_path.stat().st_size == 0:
        raise AssertionError(f"File is empty: {file_path}")


def assert_directory_exists(dir_path: Path, message: str | None = None) -> None:
    """
    Assert directory exists.

    Args:
        dir_path: Path to directory
        message: Custom error message

    Raises:
        AssertionError: If directory doesn't exist
    """
    if not dir_path.exists():
        error_msg = message or f"Directory does not exist: {dir_path}"
        raise AssertionError(error_msg)

    if not dir_path.is_dir():
        raise AssertionError(f"Path exists but is not a directory: {dir_path}")


def assert_json_valid(
    json_path: Path,
    required_keys: list[str] | None = None,
) -> dict[str, Any]:
    """
    Assert JSON file is valid and optionally has required keys.

    Args:
        json_path: Path to JSON file
        required_keys: Required keys in JSON

    Returns:
        Loaded JSON data

    Raises:
        AssertionError: If JSON is invalid or missing keys
    """
    assert_file_exists(json_path)

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON in {json_path}: {e}")

    if required_keys:
        missing_keys = set(required_keys) - set(data.keys())
        if missing_keys:
            raise AssertionError(f"Missing required keys in {json_path}: {list(missing_keys)}")

    return data


def assert_checksum_valid(
    file_path: Path,
    expected_checksum: str,
    algorithm: str = "sha256",
) -> None:
    """
    Assert file checksum matches expected value.

    Args:
        file_path: Path to file
        expected_checksum: Expected checksum
        algorithm: Hash algorithm

    Raises:
        AssertionError: If checksum doesn't match
    """
    from ml.utils.file_manager import compute_file_hash

    assert_file_exists(file_path)

    actual_checksum = compute_file_hash(file_path, algorithm=algorithm)

    if actual_checksum != expected_checksum:
        raise AssertionError(
            f"Checksum mismatch for {file_path}:\n"
            f"  Expected: {expected_checksum}\n"
            f"  Actual:   {actual_checksum}"
        )


def assert_config_valid(config: dict[str, Any], schema: dict[str, type]) -> None:
    """
    Assert configuration matches schema.

    Args:
        config: Configuration dictionary
        schema: Schema dictionary (key -> type)

    Raises:
        AssertionError: If config doesn't match schema
    """
    # Check required keys
    missing_keys = set(schema.keys()) - set(config.keys())
    if missing_keys:
        raise AssertionError(f"Missing required config keys: {list(missing_keys)}")

    # Check types
    for key, expected_type in schema.items():
        if key in config:
            actual_value = config[key]
            if not isinstance(actual_value, expected_type):
                raise AssertionError(
                    f"Config key '{key}' has wrong type: "
                    f"expected {expected_type.__name__}, got {type(actual_value).__name__}"
                )


def assert_pipeline_completed(
    pipeline_metadata: PipelineRunMetadata,
    expected_status: str = "success",
) -> None:
    """
    Assert pipeline completed with expected status.

    Args:
        pipeline_metadata: Pipeline run metadata
        expected_status: Expected completion status

    Raises:
        AssertionError: If pipeline status doesn't match
    """
    if pipeline_metadata.status != expected_status:
        raise AssertionError(
            f"Pipeline status mismatch: "
            f"expected '{expected_status}', got '{pipeline_metadata.status}'"
        )

    if pipeline_metadata.completed_at is None:
        raise AssertionError("Pipeline completed_at timestamp is None")

    if pipeline_metadata.started_at >= pipeline_metadata.completed_at:
        raise AssertionError("Pipeline started_at >= completed_at")


def assert_feature_importance_valid(
    importance_scores: dict[str, float],
    min_score: float = 0.0,
    max_score: float = 1.0,
) -> None:
    """
    Assert feature importance scores are valid.

    Args:
        importance_scores: Feature importance dictionary
        min_score: Minimum valid score
        max_score: Maximum valid score

    Raises:
        AssertionError: If scores are invalid
    """
    if not importance_scores:
        raise AssertionError("No feature importance scores provided")

    for feature, score in importance_scores.items():
        if not isinstance(score, (int, float)):
            raise AssertionError(f"Feature '{feature}' importance is not numeric: {type(score)}")

        if not (min_score <= score <= max_score):
            raise AssertionError(
                f"Feature '{feature}' importance {score} not in range [{min_score}, {max_score}]"
            )


def assert_data_split_valid(
    train_size: int,
    val_size: int,
    test_size: int,
    total_size: int,
    tolerance: float = 0.01,
) -> None:
    """
    Assert data split sizes are valid.

    Args:
        train_size: Training set size
        val_size: Validation set size
        test_size: Test set size
        total_size: Total dataset size
        tolerance: Allowed difference tolerance

    Raises:
        AssertionError: If split is invalid
    """
    split_total = train_size + val_size + test_size
    diff = abs(split_total - total_size)

    if diff > (total_size * tolerance):
        raise AssertionError(
            f"Split sizes don't match total: "
            f"{train_size} + {val_size} + {test_size} = {split_total} != {total_size}"
        )

    # Check minimum sizes
    if train_size <= 0:
        raise AssertionError(f"Training set size must be positive: {train_size}")

    if val_size < 0:
        raise AssertionError(f"Validation set size must be non-negative: {val_size}")

    if test_size < 0:
        raise AssertionError(f"Test set size must be non-negative: {test_size}")
