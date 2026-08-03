"""
Tests for train/validation/test split module.

Tests cover:
- Empty dataframe
- Single-row dataframe
- Unsorted dataframe
- Already sorted dataframe
- Duplicate timestamps
- Missing TransactionDT
- Invalid split ratios
- Ratio sum != 1.0
- Overlapping indices
- Duplicate indices
- Fraud rate calculation
- Parquet persistence
- Index persistence (.npy files)
- Metadata generation
- Leakage validation
- Temporal ordering
- Reproducibility
- Benchmark generation
- Configuration loading
- Error handling
"""

import json

import numpy as np
import pandas as pd
import pytest

from ml.training.data.train_val_test_split import TemporalSplitter


@pytest.fixture
def sample_config_path(tmp_path):
    """Create a temporary config file for testing."""
    config_content = """
random_seed: 42
split:
  strategy: "time_based"
  train_ratio: 0.6
  val_ratio: 0.2
  test_ratio: 0.2
"""
    config_path = tmp_path / "preprocessing_config.yaml"
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def sample_dataframe():
    """Create a sample dataframe for testing."""
    return pd.DataFrame(
        {
            "TransactionDT": [
                1000.0,
                2000.0,
                3000.0,
                4000.0,
                5000.0,
                6000.0,
                7000.0,
                8000.0,
                9000.0,
                10000.0,
            ],
            "TransactionAmt": [
                100.0,
                200.0,
                150.0,
                300.0,
                250.0,
                180.0,
                220.0,
                400.0,
                350.0,
                500.0,
            ],
            "isFraud": [0, 0, 1, 0, 1, 0, 0, 1, 0, 1],
        }
    )


def test_temporal_splitter_initialization(sample_config_path):
    """Test TemporalSplitter can be initialized."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    assert splitter is not None
    assert splitter.config is not None
    assert splitter.train_indices is None
    assert splitter.val_indices is None
    assert splitter.test_indices is None


def test_split_basic_functionality(sample_config_path, sample_dataframe):
    """Test basic split functionality with valid data."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    # Check split sizes
    assert len(train_df) == 6  # 60% of 10
    assert len(val_df) == 2  # 20% of 10
    assert len(test_df) == 2  # 20% of 10

    # Check total rows preserved
    assert len(train_df) + len(val_df) + len(test_df) == len(sample_dataframe)


def test_empty_dataframe_raises_error(sample_config_path):
    """Test that empty dataframe raises ValueError."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    empty_df = pd.DataFrame()

    with pytest.raises(ValueError, match="Cannot split empty dataframe"):
        splitter.split(empty_df)


def test_single_row_dataframe(sample_config_path):
    """Test splitting single-row dataframe."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    single_row_df = pd.DataFrame(
        {
            "TransactionDT": [1000.0],
            "TransactionAmt": [100.0],
            "isFraud": [0],
        }
    )

    train_df, val_df, test_df = splitter.split(single_row_df.copy())

    # With ratios 0.6/0.2/0.2 and n=1:
    # train_end = int(1 * 0.6) = 0, so train gets 0 rows
    # val_end = 0 + int(1 * 0.2) = 0, so val gets 0 rows
    # test gets remaining: 1 row
    assert len(train_df) == 0
    assert len(val_df) == 0
    assert len(test_df) == 1


def test_unsorted_dataframe_gets_sorted(sample_config_path):
    """Test that unsorted dataframe is sorted by TransactionDT."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    unsorted_df = pd.DataFrame(
        {
            "TransactionDT": [5000.0, 1000.0, 3000.0, 2000.0, 4000.0],
            "TransactionAmt": [250.0, 100.0, 150.0, 200.0, 300.0],
            "isFraud": [1, 0, 1, 0, 0],
        }
    )

    train_df, val_df, test_df = splitter.split(unsorted_df.copy())

    # Check train data has earliest timestamps
    assert train_df["TransactionDT"].min() == 1000.0
    assert train_df["TransactionDT"].max() == 3000.0

    # Check test data has latest timestamps
    assert test_df["TransactionDT"].min() == 5000.0
    assert test_df["TransactionDT"].max() == 5000.0


def test_already_sorted_dataframe(sample_config_path, sample_dataframe):
    """Test that already sorted dataframe works correctly."""
    splitter = TemporalSplitter(config_path=sample_config_path)

    # Dataframe is already sorted
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    # Check temporal ordering
    assert train_df["TransactionDT"].is_monotonic_increasing
    assert val_df["TransactionDT"].is_monotonic_increasing
    assert test_df["TransactionDT"].is_monotonic_increasing


def test_duplicate_timestamps_allowed(sample_config_path):
    """Test that duplicate timestamps are allowed and handled correctly."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    df_with_dupes = pd.DataFrame(
        {
            "TransactionDT": [
                1000.0,
                1000.0,
                2000.0,
                2000.0,
                3000.0,
                3000.0,
                4000.0,
                4000.0,
                5000.0,
                5000.0,
            ],
            "TransactionAmt": [
                100.0,
                150.0,
                200.0,
                250.0,
                300.0,
                350.0,
                400.0,
                450.0,
                500.0,
                550.0,
            ],
            "isFraud": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        }
    )

    train_df, val_df, test_df = splitter.split(df_with_dupes.copy())

    # Should split successfully without errors
    assert len(train_df) + len(val_df) + len(test_df) == len(df_with_dupes)


def test_missing_transactiondt_column_raises_error(sample_config_path):
    """Test that missing TransactionDT column raises ValueError."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    df_no_time = pd.DataFrame(
        {
            "TransactionAmt": [100.0, 200.0, 300.0],
            "isFraud": [0, 1, 0],
        }
    )

    with pytest.raises(ValueError, match="Time column 'TransactionDT' not found"):
        splitter.split(df_no_time)


def test_all_nan_transactiondt_raises_error(sample_config_path):
    """Test that all-NaN TransactionDT raises ValueError."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    df_all_nan = pd.DataFrame(
        {
            "TransactionDT": [np.nan, np.nan, np.nan],
            "TransactionAmt": [100.0, 200.0, 300.0],
            "isFraud": [0, 1, 0],
        }
    )

    with pytest.raises(ValueError, match="contains all NaN values"):
        splitter.split(df_all_nan)


def test_invalid_split_ratios_negative(tmp_path):
    """Test that negative split ratios raise ValueError."""
    config_content = """
random_seed: 42
split:
  strategy: "time_based"
  train_ratio: -0.6
  val_ratio: 0.2
  test_ratio: 0.2
"""
    config_path = tmp_path / "bad_config.yaml"
    config_path.write_text(config_content)

    splitter = TemporalSplitter(config_path=config_path)
    df = pd.DataFrame({"TransactionDT": [1000.0, 2000.0], "isFraud": [0, 1]})

    with pytest.raises(ValueError, match="must be positive"):
        splitter.split(df)


def test_invalid_split_ratios_sum_not_one(tmp_path):
    """Test that ratios not summing to 1.0 raise ValueError."""
    config_content = """
random_seed: 42
split:
  strategy: "time_based"
  train_ratio: 0.5
  val_ratio: 0.3
  test_ratio: 0.3
"""
    config_path = tmp_path / "bad_config.yaml"
    config_path.write_text(config_content)

    splitter = TemporalSplitter(config_path=config_path)
    df = pd.DataFrame({"TransactionDT": [1000.0, 2000.0], "isFraud": [0, 1]})

    with pytest.raises(ValueError, match="must sum to 1.0"):
        splitter.split(df)


def test_no_overlapping_indices(sample_config_path, sample_dataframe):
    """Test that train/val/test have no overlapping indices."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    # Check no overlap
    train_set = set(train_df.index)
    val_set = set(val_df.index)
    test_set = set(test_df.index)

    assert len(train_set & val_set) == 0
    assert len(train_set & test_set) == 0
    assert len(val_set & test_set) == 0


def test_no_duplicate_indices(sample_config_path, sample_dataframe):
    """Test that each split has no duplicate indices."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    # Check no duplicates within each split
    assert len(train_df) == len(train_df.index.unique())
    assert len(val_df) == len(val_df.index.unique())
    assert len(test_df) == len(test_df.index.unique())


def test_fraud_rate_calculation(sample_config_path, sample_dataframe):
    """Test that fraud rates are calculated correctly."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    stats = splitter.get_statistics()

    # Check fraud stats exist
    assert "train" in stats
    assert "fraud_count" in stats["train"]
    assert "fraud_rate" in stats["train"]

    # Check fraud rate is between 0 and 1
    assert 0 <= stats["train"]["fraud_rate"] <= 1
    assert 0 <= stats["validation"]["fraud_rate"] <= 1
    assert 0 <= stats["test"]["fraud_rate"] <= 1


def test_parquet_persistence(sample_config_path, sample_dataframe, tmp_path):
    """Test saving datasets to parquet files."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    output_dir = tmp_path / "splits"
    splitter.save_datasets(train_df, val_df, test_df, output_dir)

    # Check files exist
    assert (output_dir / "train.parquet").exists()
    assert (output_dir / "validation.parquet").exists()
    assert (output_dir / "test.parquet").exists()

    # Check data can be loaded back
    loaded_train = pd.read_parquet(output_dir / "train.parquet")
    pd.testing.assert_frame_equal(loaded_train, train_df)


def test_index_persistence(sample_config_path, sample_dataframe, tmp_path):
    """Test saving indices to .npy files."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    output_dir = tmp_path / "splits"
    splitter.save_indices(output_dir)

    # Check files exist
    assert (output_dir / "train_indices.npy").exists()
    assert (output_dir / "validation_indices.npy").exists()
    assert (output_dir / "test_indices.npy").exists()

    # Check indices can be loaded back
    loaded_train = np.load(output_dir / "train_indices.npy")
    np.testing.assert_array_equal(loaded_train, splitter.train_indices)


def test_metadata_generation(sample_config_path, sample_dataframe, tmp_path):
    """Test metadata generation and persistence."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    output_dir = tmp_path / "splits"
    splitter.save_metadata(output_dir)

    # Check file exists
    assert (output_dir / "split_metadata.json").exists()

    # Check metadata content
    with open(output_dir / "split_metadata.json") as f:
        metadata = json.load(f)

    assert "train" in metadata
    assert "validation" in metadata
    assert "test" in metadata
    assert "execution_time_seconds" in metadata
    assert "timestamp" in metadata
    assert "preprocessing_config" in metadata


def test_temporal_leakage_validation(sample_config_path, sample_dataframe):
    """Test that temporal boundaries are validated (no leakage)."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    # Verify temporal ordering
    train_max = train_df["TransactionDT"].max()
    val_min = val_df["TransactionDT"].min()
    val_max = val_df["TransactionDT"].max()
    test_min = test_df["TransactionDT"].min()

    assert train_max < val_min
    assert val_max < test_min


def test_temporal_ordering_monotonic(sample_config_path, sample_dataframe):
    """Test that each split is temporally ordered."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    # Check monotonic increasing
    assert train_df["TransactionDT"].is_monotonic_increasing
    assert val_df["TransactionDT"].is_monotonic_increasing
    assert test_df["TransactionDT"].is_monotonic_increasing


def test_reproducibility_same_seed(sample_config_path, sample_dataframe):
    """Test that same seed produces same split."""
    splitter1 = TemporalSplitter(config_path=sample_config_path)
    train_df1, val_df1, test_df1 = splitter1.split(sample_dataframe.copy())

    splitter2 = TemporalSplitter(config_path=sample_config_path)
    train_df2, val_df2, test_df2 = splitter2.split(sample_dataframe.copy())

    # Check same splits
    pd.testing.assert_frame_equal(train_df1, train_df2)
    pd.testing.assert_frame_equal(val_df1, val_df2)
    pd.testing.assert_frame_equal(test_df1, test_df2)


def test_statistics_collection(sample_config_path, sample_dataframe):
    """Test that statistics are collected correctly."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    stats = splitter.get_statistics()

    # Check statistics exist
    assert "execution_time_seconds" in stats
    assert "total_rows" in stats
    assert "total_columns" in stats
    assert "split_ratios" in stats
    assert "train" in stats
    assert "validation" in stats
    assert "test" in stats

    # Check values
    assert stats["total_rows"] == len(sample_dataframe)
    assert stats["train"]["row_count"] == len(train_df)
    assert stats["validation"]["row_count"] == len(val_df)
    assert stats["test"]["row_count"] == len(test_df)


def test_configuration_loading(sample_config_path):
    """Test that configuration is loaded correctly from YAML."""
    splitter = TemporalSplitter(config_path=sample_config_path)

    # Check config loaded
    assert splitter.config["split"]["train_ratio"] == 0.6
    assert splitter.config["split"]["val_ratio"] == 0.2
    assert splitter.config["split"]["test_ratio"] == 0.2
    assert splitter.config["random_seed"] == 42


def test_error_handling_save_indices_before_split(sample_config_path, tmp_path):
    """Test that saving indices before split raises error."""
    splitter = TemporalSplitter(config_path=sample_config_path)

    output_dir = tmp_path / "splits"

    with pytest.raises(ValueError, match="Must call split"):
        splitter.save_indices(output_dir)


def test_error_handling_save_metadata_before_split(sample_config_path, tmp_path):
    """Test that saving metadata before split raises error."""
    splitter = TemporalSplitter(config_path=sample_config_path)

    output_dir = tmp_path / "splits"

    with pytest.raises(ValueError, match="Must call split"):
        splitter.save_metadata(output_dir)


def test_time_column_custom_name(sample_config_path):
    """Test using custom time column name."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    df = pd.DataFrame(
        {
            "custom_time": [1000.0, 2000.0, 3000.0, 4000.0, 5000.0],
            "value": [100.0, 200.0, 300.0, 400.0, 500.0],
        }
    )

    train_df, val_df, test_df = splitter.split(df.copy(), time_column="custom_time")

    # Check split worked
    assert len(train_df) + len(val_df) + len(test_df) == len(df)


def test_dataframe_without_isfraud_column(sample_config_path):
    """Test splitting dataframe without isFraud column."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    df_no_fraud = pd.DataFrame(
        {
            "TransactionDT": [1000.0, 2000.0, 3000.0, 4000.0, 5000.0],
            "TransactionAmt": [100.0, 200.0, 300.0, 400.0, 500.0],
        }
    )

    train_df, val_df, test_df = splitter.split(df_no_fraud.copy())

    stats = splitter.get_statistics()

    # Should work without fraud stats
    assert "fraud_count" not in stats["train"]
    assert "fraud_rate" not in stats["train"]


def test_indices_are_numpy_arrays(sample_config_path, sample_dataframe):
    """Test that split indices are numpy arrays."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    # Check types
    assert isinstance(splitter.train_indices, np.ndarray)
    assert isinstance(splitter.val_indices, np.ndarray)
    assert isinstance(splitter.test_indices, np.ndarray)


def test_split_ratios_reflected_in_metadata(sample_config_path, sample_dataframe, tmp_path):
    """Test that configured split ratios are reflected in metadata."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    output_dir = tmp_path / "splits"
    splitter.save_metadata(output_dir)

    with open(output_dir / "split_metadata.json") as f:
        metadata = json.load(f)

    # Check ratios in metadata
    assert metadata["preprocessing_config"]["train_ratio"] == 0.6
    assert metadata["preprocessing_config"]["val_ratio"] == 0.2
    assert metadata["preprocessing_config"]["test_ratio"] == 0.2


def test_benchmark_generation_timing(sample_config_path, sample_dataframe):
    """Test that execution timing is captured."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    stats = splitter.get_statistics()

    # Check execution time exists and is positive
    assert "execution_time_seconds" in stats
    assert stats["execution_time_seconds"] > 0


def test_column_preservation(sample_config_path, sample_dataframe):
    """Test that all columns are preserved in splits."""
    splitter = TemporalSplitter(config_path=sample_config_path)
    original_columns = set(sample_dataframe.columns)

    train_df, val_df, test_df = splitter.split(sample_dataframe.copy())

    # Check all columns preserved
    assert set(train_df.columns) == original_columns
    assert set(val_df.columns) == original_columns
    assert set(test_df.columns) == original_columns


def test_large_dataset_split_proportions(sample_config_path):
    """Test split proportions with larger dataset."""
    splitter = TemporalSplitter(config_path=sample_config_path)

    # Create larger dataset
    n = 1000
    large_df = pd.DataFrame(
        {
            "TransactionDT": np.arange(1000.0, 1000.0 + n),
            "TransactionAmt": np.random.uniform(10, 1000, n),
            "isFraud": np.random.randint(0, 2, n),
        }
    )

    train_df, val_df, test_df = splitter.split(large_df.copy())

    # Check proportions are approximately correct
    assert abs(len(train_df) / n - 0.6) < 0.01  # Within 1%
    assert abs(len(val_df) / n - 0.2) < 0.01
    assert abs(len(test_df) / n - 0.2) < 0.01
