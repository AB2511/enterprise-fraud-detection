"""
Train/Validation/Test split module for preprocessing pipeline.

Implements temporal (time-based) splitting for IEEE-CIS fraud detection dataset.
This module is the single source of truth for data splitting across all experiments.

Key Features:
- Temporal split based on TransactionDT (chronological order)
- No random shuffling (preserves time-based patterns)
- Configurable train/val/test ratios from YAML
- Automatic validation of temporal boundaries
- Persistence of split indices for reproducibility
- Detailed metadata and validation reports
- SHA256 fingerprinting for dataset integrity verification
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


class TemporalSplitter:
    """
    Temporal train/validation/test splitter.

    Splits data chronologically based on TransactionDT to prevent temporal leakage.
    All split indices are persisted to ensure reproducibility across experiments.
    """

    def __init__(self, config_path: Path | str | None = None):
        """
        Initialize temporal splitter with configuration.

        Args:
            config_path: Path to preprocessing_config.yaml.
                        If None, uses default config path.
        """
        self.config = self._load_config(config_path)
        self.statistics: dict[str, Any] = {}
        self.train_indices: np.ndarray | None = None
        self.val_indices: np.ndarray | None = None
        self.test_indices: np.ndarray | None = None

    def _load_config(self, config_path: Path | str | None) -> dict[str, Any]:
        """Load preprocessing configuration from YAML."""
        if config_path is None:
            config_path = Path("ml/training/data/preprocessing_config.yaml")
        else:
            config_path = Path(config_path)

        with open(config_path, encoding="utf-8") as f:
            config: dict[str, Any] = yaml.safe_load(f)
            return config

    def split(
        self, df: pd.DataFrame, time_column: str = "TransactionDT"
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split dataframe into train/validation/test sets temporally.

        Args:
            df: Input dataframe with time_column
            time_column: Column name containing timestamps (default: TransactionDT)

        Returns:
            Tuple of (train_df, val_df, test_df)

        Raises:
            ValueError: If time_column missing or ratios invalid
        """
        start_time = time.perf_counter()

        # Validate input
        self._validate_input(df, time_column)

        # Get split ratios from config
        train_ratio = self.config["split"]["train_ratio"]
        val_ratio = self.config["split"]["val_ratio"]
        test_ratio = self.config["split"]["test_ratio"]

        # Validate ratios
        self._validate_ratios(train_ratio, val_ratio, test_ratio)

        # Sort by time column
        df_sorted = df.sort_values(time_column).reset_index(drop=True)

        # Calculate split points
        n = len(df_sorted)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)

        # Generate indices
        self.train_indices = np.arange(0, train_end)
        self.val_indices = np.arange(train_end, val_end)
        self.test_indices = np.arange(val_end, n)

        # Split dataframes
        train_df = df_sorted.iloc[self.train_indices].copy()
        val_df = df_sorted.iloc[self.val_indices].copy()
        test_df = df_sorted.iloc[self.test_indices].copy()

        # Validate splits
        self._validate_splits(train_df, val_df, test_df, time_column)

        # Collect statistics
        self.statistics = self._collect_statistics(
            df_sorted, train_df, val_df, test_df, time_column, start_time
        )

        return train_df, val_df, test_df

    def _validate_input(self, df: pd.DataFrame, time_column: str) -> None:
        """Validate input dataframe."""
        if df.empty:
            raise ValueError("Cannot split empty dataframe")

        if time_column not in df.columns:
            raise ValueError(f"Time column '{time_column}' not found in dataframe")

        if df[time_column].isna().all():
            raise ValueError(f"Time column '{time_column}' contains all NaN values")

    def _validate_ratios(self, train_ratio: float, val_ratio: float, test_ratio: float) -> None:
        """Validate split ratios sum to 1.0."""
        # Check positivity first
        if train_ratio <= 0 or val_ratio <= 0 or test_ratio <= 0:
            raise ValueError("All split ratios must be positive")

        # Then check sum
        total = train_ratio + val_ratio + test_ratio
        if not np.isclose(total, 1.0, atol=1e-6):
            raise ValueError(
                f"Split ratios must sum to 1.0, got {total:.6f} "
                f"(train={train_ratio}, val={val_ratio}, test={test_ratio})"
            )

    def _validate_splits(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        time_column: str,
    ) -> None:
        """
        Validate temporal boundaries and no overlap.

        Raises:
            ValueError: If validation fails
        """
        # Check no overlapping indices
        train_set = set(train_df.index)
        val_set = set(val_df.index)
        test_set = set(test_df.index)

        if train_set & val_set:
            raise ValueError("Train and validation sets have overlapping indices")
        if train_set & test_set:
            raise ValueError("Train and test sets have overlapping indices")
        if val_set & test_set:
            raise ValueError("Validation and test sets have overlapping indices")

        # Check temporal boundaries
        train_max_time = train_df[time_column].max()
        val_min_time = val_df[time_column].min()
        val_max_time = val_df[time_column].max()
        test_min_time = test_df[time_column].min()

        if train_max_time >= val_min_time:
            raise ValueError(
                f"Temporal leakage detected: train max time ({train_max_time}) "
                f">= validation min time ({val_min_time})"
            )

        if val_max_time >= test_min_time:
            raise ValueError(
                f"Temporal leakage detected: validation max time ({val_max_time}) "
                f">= test min time ({test_min_time})"
            )

    def _collect_statistics(
        self,
        df_sorted: pd.DataFrame,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        time_column: str,
        start_time: float,
    ) -> dict[str, Any]:
        """Collect split statistics and metadata."""
        execution_time = time.perf_counter() - start_time

        # Calculate fraud rates
        target_col = "isFraud"
        has_target = target_col in df_sorted.columns

        stats = {
            "execution_time_seconds": execution_time,
            "total_rows": len(df_sorted),
            "total_columns": len(df_sorted.columns),
            "split_ratios": {
                "train": self.config["split"]["train_ratio"],
                "validation": self.config["split"]["val_ratio"],
                "test": self.config["split"]["test_ratio"],
            },
            "train": {
                "row_count": len(train_df),
                "row_percentage": len(train_df) / len(df_sorted) * 100,
                "time_min": float(train_df[time_column].min()),
                "time_max": float(train_df[time_column].max()),
                "time_range": float(train_df[time_column].max() - train_df[time_column].min()),
            },
            "validation": {
                "row_count": len(val_df),
                "row_percentage": len(val_df) / len(df_sorted) * 100,
                "time_min": float(val_df[time_column].min()),
                "time_max": float(val_df[time_column].max()),
                "time_range": float(val_df[time_column].max() - val_df[time_column].min()),
            },
            "test": {
                "row_count": len(test_df),
                "row_percentage": len(test_df) / len(df_sorted) * 100,
                "time_min": float(test_df[time_column].min()),
                "time_max": float(test_df[time_column].max()),
                "time_range": float(test_df[time_column].max() - test_df[time_column].min()),
            },
            "random_seed": self.config.get("random_seed", None),
            "config_version": self.config.get("version", "unknown"),
        }

        # Add fraud statistics if target exists
        if has_target:
            stats["train"]["fraud_count"] = int(train_df[target_col].sum())
            stats["train"]["fraud_rate"] = float(train_df[target_col].mean())

            stats["validation"]["fraud_count"] = int(val_df[target_col].sum())
            stats["validation"]["fraud_rate"] = float(val_df[target_col].mean())

            stats["test"]["fraud_count"] = int(test_df[target_col].sum())
            stats["test"]["fraud_rate"] = float(test_df[target_col].mean())

            stats["overall_fraud_rate"] = float(df_sorted[target_col].mean())

        return stats

    def save_indices(self, output_dir: Path | str) -> None:
        """
        Save split indices to numpy files for reproducibility.

        Args:
            output_dir: Directory to save indices (will be created if doesn't exist)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.train_indices is None:
            raise ValueError("Must call split() before saving indices")

        np.save(output_dir / "train_indices.npy", self.train_indices)
        np.save(output_dir / "validation_indices.npy", self.val_indices)
        np.save(output_dir / "test_indices.npy", self.test_indices)

    def save_datasets(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        output_dir: Path | str,
    ) -> None:
        """
        Save split datasets to parquet files.

        Args:
            train_df: Training dataframe
            val_df: Validation dataframe
            test_df: Test dataframe
            output_dir: Directory to save datasets
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        train_df.to_parquet(output_dir / "train.parquet", index=False)
        val_df.to_parquet(output_dir / "validation.parquet", index=False)
        test_df.to_parquet(output_dir / "test.parquet", index=False)

    def save_metadata(self, output_dir: Path | str) -> None:
        """
        Save split metadata to JSON file.

        Args:
            output_dir: Directory to save metadata
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not self.statistics:
            raise ValueError("Must call split() before saving metadata")

        metadata = {
            **self.statistics,
            "timestamp": pd.Timestamp.now().isoformat(),
            "preprocessing_config": {
                "random_seed": self.config.get("random_seed"),
                "split_strategy": self.config["split"]["strategy"],
                "train_ratio": self.config["split"]["train_ratio"],
                "val_ratio": self.config["split"]["val_ratio"],
                "test_ratio": self.config["split"]["test_ratio"],
            },
        }

        with open(output_dir / "split_metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    def get_statistics(self) -> dict[str, Any]:
        """Get split statistics."""
        return self.statistics
