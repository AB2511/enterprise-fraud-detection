"""
Dataset configuration for IEEE-CIS Fraud Detection dataset.

Provides:
- Path configuration with environment overrides
- Schema definitions for validation
- Type-safe configuration objects
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetPaths:
    """
    Configurable paths for IEEE-CIS dataset files.

    Attributes:
        data_root: Root directory containing raw data
        transaction_file: Path to train_transaction.csv
        identity_file: Path to train_identity.csv
    """

    data_root: Path
    transaction_file: Path
    identity_file: Path

    @classmethod
    def from_data_root(cls, data_root: Path | str | None = None) -> "DatasetPaths":
        """
        Create DatasetPaths from data root directory.

        Args:
            data_root: Root directory path. If None, uses 'data/raw' or ML_DATA_ROOT env var

        Returns:
            DatasetPaths instance with resolved paths
        """
        if data_root is None:
            # Try environment variable first, fallback to default
            data_root = Path(os.getenv("ML_DATA_ROOT", "backend/data/raw"))
        else:
            data_root = Path(data_root)

        return cls(
            data_root=data_root,
            transaction_file=data_root / "train_transaction.csv",
            identity_file=data_root / "train_identity.csv",
        )


@dataclass(frozen=True)
class IEEECISSchema:
    """
    IEEE-CIS dataset schema definition.

    Contains:
    - Required columns for validation
    - Data types
    - Key columns (TransactionID, isFraud)
    """

    # Key columns
    transaction_id_col: str = "TransactionID"
    target_col: str = "isFraud"

    # Minimum required columns in transaction table
    required_transaction_cols: tuple[str, ...] = (
        "TransactionID",
        "isFraud",
        "TransactionDT",
        "TransactionAmt",
    )

    # Minimum required columns in identity table
    required_identity_cols: tuple[str, ...] = ("TransactionID",)

    @property
    def all_required_columns(self) -> set[str]:
        """Get all required columns across both tables."""
        return set(self.required_transaction_cols) | set(self.required_identity_cols)
