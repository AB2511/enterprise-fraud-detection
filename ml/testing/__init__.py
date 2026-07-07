"""
Testing Infrastructure

Reusable testing utilities for ML pipeline components.
"""

from ml.testing.assertions import (
    assert_checksum_valid,
    assert_config_valid,
    assert_data_split_valid,
    assert_dataframe_equal,
    assert_dataframe_no_duplicates,
    assert_dataframe_no_nulls,
    assert_dataframe_not_empty,
    assert_dataframe_range,
    assert_dataframe_schema,
    assert_directory_exists,
    assert_feature_importance_valid,
    assert_file_exists,
    assert_file_not_empty,
    assert_json_valid,
    assert_metadata_valid,
    assert_pipeline_completed,
    assert_validation_all_passed,
    assert_validation_passed,
)
from ml.testing.fixtures import (
    MockDatasetGenerator,
    create_mock_config,
    create_mock_dataframe,
    create_mock_feature_metadata,
    create_mock_metadata,
    create_mock_pipeline_metadata,
    create_mock_validation_results,
)

__all__ = [
    # Fixtures
    "MockDatasetGenerator",
    "create_mock_dataframe",
    "create_mock_metadata",
    "create_mock_feature_metadata",
    "create_mock_pipeline_metadata",
    "create_mock_validation_results",
    "create_mock_config",
    # Assertions
    "assert_dataframe_equal",
    "assert_dataframe_schema",
    "assert_dataframe_not_empty",
    "assert_dataframe_no_nulls",
    "assert_dataframe_no_duplicates",
    "assert_dataframe_range",
    "assert_metadata_valid",
    "assert_validation_passed",
    "assert_validation_all_passed",
    "assert_file_exists",
    "assert_file_not_empty",
    "assert_directory_exists",
    "assert_json_valid",
    "assert_checksum_valid",
    "assert_config_valid",
    "assert_pipeline_completed",
    "assert_feature_importance_valid",
    "assert_data_split_valid",
]
