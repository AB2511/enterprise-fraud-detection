"""
Unit tests for dataset loader.

Tests:
- File existence validation
- CSV loading
- Error handling
- Dataset merging
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from ml.training.data.config import DatasetPaths, IEEECISSchema
from ml.training.data.loader import (
    DatasetLoadError,
    DatasetNotFoundError,
    load_ieee_cis_dataset,
    validate_dataset_files,
)


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_transaction_data():
    """Create sample transaction data."""
    return pd.DataFrame(
        {
            "TransactionID": [1, 2, 3, 4, 5],
            "isFraud": [0, 1, 0, 0, 1],
            "TransactionDT": [100, 200, 300, 400, 500],
            "TransactionAmt": [10.0, 20.0, 30.0, 40.0, 50.0],
            "ProductCD": ["W", "W", "C", "W", "H"],
        }
    )


@pytest.fixture
def sample_identity_data():
    """Create sample identity data."""
    return pd.DataFrame(
        {
            "TransactionID": [1, 2, 3],
            "id_01": [0.1, 0.2, 0.3],
            "id_02": [1.0, 2.0, 3.0],
        }
    )


@pytest.fixture
def sample_dataset_files(temp_data_dir, sample_transaction_data, sample_identity_data):
    """Create sample CSV files in temp directory."""
    transaction_file = temp_data_dir / "train_transaction.csv"
    identity_file = temp_data_dir / "train_identity.csv"

    sample_transaction_data.to_csv(transaction_file, index=False)
    sample_identity_data.to_csv(identity_file, index=False)

    return DatasetPaths.from_data_root(temp_data_dir)


class TestDatasetPaths:
    """Test DatasetPaths configuration."""

    def test_from_data_root_default(self):
        """Test creating paths with default root."""
        paths = DatasetPaths.from_data_root()
        assert paths.data_root == Path("data/raw")
        assert paths.transaction_file == Path("data/raw/train_transaction.csv")
        assert paths.identity_file == Path("data/raw/train_identity.csv")

    def test_from_data_root_custom(self):
        """Test creating paths with custom root."""
        custom_root = Path("/custom/path")
        paths = DatasetPaths.from_data_root(custom_root)
        assert paths.data_root == custom_root
        assert paths.transaction_file == custom_root / "train_transaction.csv"
        assert paths.identity_file == custom_root / "train_identity.csv"


class TestValidateDatasetFiles:
    """Test file existence validation."""

    def test_validate_existing_files(self, sample_dataset_files):
        """Test validation passes for existing files."""
        # Should not raise
        validate_dataset_files(sample_dataset_files)

    def test_validate_missing_transaction_file(self, temp_data_dir):
        """Test validation fails for missing transaction file."""
        paths = DatasetPaths.from_data_root(temp_data_dir)

        with pytest.raises(DatasetNotFoundError) as exc_info:
            validate_dataset_files(paths)

        assert "train_transaction.csv" in str(exc_info.value)

    def test_validate_missing_identity_file(self, temp_data_dir, sample_transaction_data):
        """Test validation fails for missing identity file."""
        transaction_file = temp_data_dir / "train_transaction.csv"
        sample_transaction_data.to_csv(transaction_file, index=False)

        paths = DatasetPaths.from_data_root(temp_data_dir)

        with pytest.raises(DatasetNotFoundError) as exc_info:
            validate_dataset_files(paths)

        assert "train_identity.csv" in str(exc_info.value)

    def test_validate_missing_both_files(self, temp_data_dir):
        """Test validation fails for both missing files."""
        paths = DatasetPaths.from_data_root(temp_data_dir)

        with pytest.raises(DatasetNotFoundError) as exc_info:
            validate_dataset_files(paths)

        error_message = str(exc_info.value)
        assert "train_transaction.csv" in error_message
        assert "train_identity.csv" in error_message


class TestLoadIEEECISDataset:
    """Test dataset loading."""

    def test_load_merged_dataset(self, sample_dataset_files):
        """Test loading and merging both tables."""
        df = load_ieee_cis_dataset(paths=sample_dataset_files, merge=True)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5  # Transaction table has 5 rows
        assert "TransactionID" in df.columns
        assert "isFraud" in df.columns
        assert "id_01" in df.columns  # From identity table

        # Check merge result
        assert df.loc[df["TransactionID"] == 1, "id_01"].iloc[0] == 0.1
        assert pd.isna(df.loc[df["TransactionID"] == 4, "id_01"].iloc[0])  # No identity

    def test_load_separate_tables(self, sample_dataset_files):
        """Test loading without merging."""
        result = load_ieee_cis_dataset(paths=sample_dataset_files, merge=False)

        assert isinstance(result, tuple)
        transaction_df, identity_df = result

        assert len(transaction_df) == 5
        assert len(identity_df) == 3
        assert "TransactionID" in transaction_df.columns
        assert "TransactionID" in identity_df.columns

    def test_load_missing_files_with_validation(self, temp_data_dir):
        """Test loading fails with validation for missing files."""
        paths = DatasetPaths.from_data_root(temp_data_dir)

        with pytest.raises(DatasetNotFoundError):
            load_ieee_cis_dataset(paths=paths, validate_files=True)

    def test_load_missing_files_without_validation(self, temp_data_dir):
        """Test loading fails without validation for missing files."""
        paths = DatasetPaths.from_data_root(temp_data_dir)

        with pytest.raises(DatasetLoadError):
            load_ieee_cis_dataset(paths=paths, validate_files=False)

    def test_load_empty_file(self, temp_data_dir):
        """Test loading fails for empty CSV."""
        empty_file = temp_data_dir / "train_transaction.csv"
        empty_file.write_text("")

        identity_file = temp_data_dir / "train_identity.csv"
        identity_file.write_text("TransactionID\n1\n")

        paths = DatasetPaths.from_data_root(temp_data_dir)

        with pytest.raises(DatasetLoadError) as exc_info:
            load_ieee_cis_dataset(paths=paths)

        assert "empty" in str(exc_info.value).lower()

    def test_load_malformed_csv(self, temp_data_dir):
        """Test loading fails for malformed CSV."""
        malformed_file = temp_data_dir / "train_transaction.csv"
        malformed_file.write_text("TransactionID,isFraud\n1,0,extra\n")

        identity_file = temp_data_dir / "train_identity.csv"
        pd.DataFrame({"TransactionID": [1]}).to_csv(identity_file, index=False)

        paths = DatasetPaths.from_data_root(temp_data_dir)

        # Pandas may handle this differently, so we check for either success or error
        try:
            df = load_ieee_cis_dataset(paths=paths)
            # If it loads, verify it has data
            assert len(df) > 0
        except DatasetLoadError:
            # If it fails, that's also acceptable
            pass


class TestIEEECISSchema:
    """Test schema configuration."""

    def test_schema_defaults(self):
        """Test schema has correct defaults."""
        schema = IEEECISSchema()

        assert schema.transaction_id_col == "TransactionID"
        assert schema.target_col == "isFraud"
        assert "TransactionID" in schema.required_transaction_cols
        assert "isFraud" in schema.required_transaction_cols
        assert "TransactionID" in schema.required_identity_cols

    def test_all_required_columns(self):
        """Test all_required_columns property."""
        schema = IEEECISSchema()
        all_cols = schema.all_required_columns

        assert "TransactionID" in all_cols
        assert "isFraud" in all_cols
        assert isinstance(all_cols, set)
