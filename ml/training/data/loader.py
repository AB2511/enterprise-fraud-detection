"""
Dataset loader for IEEE-CIS Fraud Detection dataset.

Provides:
- File existence validation
- CSV loading with proper error handling
- Dataset merging
- Type-safe return values
"""

import logging

import pandas as pd

from .config import DatasetPaths, IEEECISSchema

logger = logging.getLogger(__name__)


class DatasetNotFoundError(FileNotFoundError):
    """Raised when required dataset files are not found."""

    pass


class DatasetLoadError(Exception):
    """Raised when dataset loading fails."""

    pass


def validate_dataset_files(paths: DatasetPaths) -> None:
    """
    Validate that required dataset files exist.

    Args:
        paths: DatasetPaths configuration

    Raises:
        DatasetNotFoundError: If any required file is missing
    """
    missing_files = []

    if not paths.transaction_file.exists():
        missing_files.append(str(paths.transaction_file))

    if not paths.identity_file.exists():
        missing_files.append(str(paths.identity_file))

    if missing_files:
        raise DatasetNotFoundError(
            f"Required dataset files not found:\n"
            f"{chr(10).join(f'  - {f}' for f in missing_files)}\n\n"
            f"Expected location: {paths.data_root}\n"
            f"Please ensure the IEEE-CIS dataset is available at the configured location."
        )

    logger.info(
        "Dataset files validated",
        extra={
            "transaction_file": str(paths.transaction_file),
            "identity_file": str(paths.identity_file),
        },
    )


def load_ieee_cis_dataset(
    paths: DatasetPaths | None = None,
    merge: bool = True,
    validate_files: bool = True,
) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load IEEE-CIS Fraud Detection dataset.

    Args:
        paths: DatasetPaths configuration. If None, uses default from config
        merge: If True, merge transaction and identity tables on TransactionID
        validate_files: If True, validate files exist before loading

    Returns:
        If merge=True: Merged DataFrame
        If merge=False: Tuple of (transaction_df, identity_df)

    Raises:
        DatasetNotFoundError: If required files don't exist and validate_files=True
        DatasetLoadError: If loading fails
    """
    if paths is None:
        paths = DatasetPaths.from_data_root()

    if validate_files:
        validate_dataset_files(paths)

    schema = IEEECISSchema()

    try:
        # Load transaction data
        logger.info(f"Loading transaction data from {paths.transaction_file}")
        transaction_df = pd.read_csv(paths.transaction_file)
        logger.info(
            f"Loaded transaction data: {len(transaction_df):,} rows, "
            f"{len(transaction_df.columns)} columns"
        )

        # Load identity data
        logger.info(f"Loading identity data from {paths.identity_file}")
        identity_df = pd.read_csv(paths.identity_file)
        logger.info(
            f"Loaded identity data: {len(identity_df):,} rows, "
            f"{len(identity_df.columns)} columns"
        )

    except pd.errors.EmptyDataError as e:
        raise DatasetLoadError(f"Dataset file is empty: {e}") from e
    except pd.errors.ParserError as e:
        raise DatasetLoadError(f"Failed to parse CSV file: {e}") from e
    except Exception as e:
        raise DatasetLoadError(f"Failed to load dataset: {e}") from e

    if not merge:
        return transaction_df, identity_df

    # Merge on TransactionID
    try:
        logger.info("Merging transaction and identity data")
        merged_df = transaction_df.merge(
            identity_df, on=schema.transaction_id_col, how="left", validate="1:1"
        )
        logger.info(f"Merged dataset: {len(merged_df):,} rows, {len(merged_df.columns)} columns")
        return merged_df

    except Exception as e:
        raise DatasetLoadError(f"Failed to merge datasets: {e}") from e
