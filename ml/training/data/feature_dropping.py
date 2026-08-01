"""
Feature dropping module for preprocessing pipeline.

Implements configurable feature dropping based on:
- Identifier columns
- Extreme missing values (>threshold)
- Constant features
- Exact duplicate features (100% identical)
- Highly correlated features (flagged, optionally dropped)
"""

import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


class FeatureDropper:
    """
    Configurable feature dropper.

    Drops features based on:
    - Identifier columns (e.g., TransactionID)
    - Extreme missing values (configurable threshold)
    - Constant features (only 1 unique value)
    - Exact duplicate features (100% identical values)
    - Highly correlated features (optional, based on config)
    """

    def __init__(self, config_path: Path | str | None = None):
        """
        Initialize feature dropper with configuration.

        Args:
            config_path: Path to preprocessing_config.yaml.
                        If None, uses default config.
        """
        self.config = self._load_config(config_path)
        self.dropped_columns: dict[str, list[str]] = {}
        self.flagged_columns: dict[str, list[tuple[str, str, float]]] = {}
        self.column_metadata: list[dict[str, Any]] = []
        self.statistics: dict[str, Any] = {}

    def _load_config(self, config_path: Path | str | None) -> dict[str, Any]:
        """Load preprocessing configuration from YAML."""
        if config_path is None:
            config_path = Path("ml/training/data/preprocessing_config.yaml")
        else:
            config_path = Path(config_path)

        with open(config_path, encoding="utf-8") as f:
            config: dict[str, Any] = yaml.safe_load(f)
            return config

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Drop features based on configuration.

        Args:
            df: Input dataframe

        Returns:
            DataFrame with specified features dropped
        """
        start_time = time.time()

        # Initialize statistics
        self.statistics["input_shape"] = df.shape
        self.statistics["input_memory_mb"] = df.memory_usage(deep=True).sum() / 1024**2
        self.statistics["input_null_count"] = df.isna().sum().sum()

        # Collect metadata for all columns before dropping
        self._collect_column_metadata(df)

        # Drop identifier columns
        df = self._drop_identifiers(df)

        # Drop extreme missing value columns
        df = self._drop_extreme_missing(df)

        # Drop constant features
        df = self._drop_constant_features(df)

        # Drop exact duplicates and flag correlated features
        df = self._drop_exact_duplicates_and_flag_correlated(df)

        # Final statistics
        self.statistics["output_shape"] = df.shape
        self.statistics["output_memory_mb"] = df.memory_usage(deep=True).sum() / 1024**2
        self.statistics["output_null_count"] = df.isna().sum().sum()
        self.statistics["execution_time_seconds"] = time.time() - start_time
        self.statistics["columns_dropped_total"] = sum(
            len(cols) for cols in self.dropped_columns.values()
        )
        self.statistics["columns_flagged_total"] = sum(
            len(cols) for cols in self.flagged_columns.values()
        )

        return df

    def _collect_column_metadata(self, df: pd.DataFrame) -> None:
        """Collect metadata for all columns for reporting."""
        for col in df.columns:
            missing_pct = (df[col].isna().sum() / len(df)) * 100
            unique_values = df[col].nunique()

            self.column_metadata.append(
                {
                    "column": col,
                    "missing_pct": round(missing_pct, 2),
                    "unique_values": unique_values,
                    "dtype": str(df[col].dtype),
                }
            )

    def _drop_identifiers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop identifier columns specified in config."""
        identifier_cols = self.config["dropping"]["identifier_columns"]
        to_drop = [col for col in identifier_cols if col in df.columns]

        if to_drop:
            df = df.drop(columns=to_drop)
            self.dropped_columns["identifiers"] = to_drop

        return df

    def _drop_extreme_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop columns with extreme missing values."""
        threshold = self.config["dropping"]["auto_drop_threshold"]

        missing_pcts = (df.isna().sum() / len(df)) * 100
        extreme_missing = missing_pcts[missing_pcts > threshold].index.tolist()

        if extreme_missing:
            df = df.drop(columns=extreme_missing)
            self.dropped_columns["extreme_missing"] = extreme_missing

        return df

    def _drop_constant_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop features with only 1 unique value."""
        if not self.config["dropping"]["drop_constant_features"]:
            return df

        constant_cols = []
        for col in df.columns:
            if df[col].nunique() == 1:
                constant_cols.append(col)

        if constant_cols:
            df = df.drop(columns=constant_cols)
            self.dropped_columns["constant"] = constant_cols

        return df

    def _drop_exact_duplicates_and_flag_correlated(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Drop exact duplicate columns and flag highly correlated features.

        Exact duplicates (100% correlation) are always dropped.
        Highly correlated features are flagged for review.
        """
        if not self.config["dropping"]["drop_duplicates"]:
            return df

        correlation_threshold = self.config["dropping"]["duplicate_correlation_threshold"]

        # Only compute correlation for numerical columns
        numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if len(numerical_cols) < 2:
            return df

        # Sample rows for large datasets, but use ALL numerical columns
        sample_size = min(50000, len(df))
        df_sample = (
            df[numerical_cols].sample(n=sample_size, random_state=42)
            if len(df) > 50000
            else df[numerical_cols]
        )

        # Compute correlation matrix on ALL numerical features
        corr_matrix = df_sample.corr().abs()

        # Track exact duplicates and correlated pairs
        exact_duplicates: set[str] = set()
        correlated_pairs: list[tuple[str, str, float]] = []

        for i in range(len(corr_matrix.columns)):
            col_i = corr_matrix.columns[i]

            # Skip if already marked for dropping
            if col_i in exact_duplicates:
                continue

            for j in range(i + 1, len(corr_matrix.columns)):
                col_j = corr_matrix.columns[j]
                correlation = corr_matrix.iloc[i, j]

                # Exact duplicates: 100% correlation (or very close due to floating point)
                if correlation >= 0.9999:
                    exact_duplicates.add(col_j)
                # Highly correlated but not exact: flag for review
                elif correlation > correlation_threshold:
                    correlated_pairs.append((col_i, col_j, round(correlation, 4)))

        # Drop exact duplicates
        exact_duplicates_list = list(exact_duplicates)
        if exact_duplicates_list:
            # Only drop if they exist in df
            exact_duplicates_final = [col for col in exact_duplicates_list if col in df.columns]
            if exact_duplicates_final:
                df = df.drop(columns=exact_duplicates_final)
                self.dropped_columns["exact_duplicates"] = exact_duplicates_final

        # Store correlated pairs for reporting (not dropped, just flagged)
        if correlated_pairs:
            self.flagged_columns["highly_correlated"] = correlated_pairs

        return df

    def get_statistics(self) -> dict[str, Any]:
        """Get preprocessing statistics."""
        return self.statistics

    def get_dropped_columns(self) -> dict[str, list[str]]:
        """Get dictionary of dropped columns by reason."""
        return self.dropped_columns

    def get_flagged_columns(self) -> dict[str, list[tuple[str, str, float]]]:
        """Get dictionary of flagged columns (not dropped, for review)."""
        return self.flagged_columns

    def get_all_dropped_columns(self) -> list[str]:
        """Get flat list of all dropped columns."""
        all_dropped = []
        for cols in self.dropped_columns.values():
            all_dropped.extend(cols)
        return all_dropped

    def generate_dropped_columns_report(self, output_path: Path | str) -> None:
        """
        Generate CSV report of dropped and flagged columns.

        Args:
            output_path: Path to save the CSV report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build report rows
        report_rows = []

        # Add dropped columns
        for reason, cols in self.dropped_columns.items():
            for col in cols:
                # Find metadata for this column
                meta = next((m for m in self.column_metadata if m["column"] == col), None)
                if meta:
                    report_rows.append(
                        {
                            "column": col,
                            "reason": reason,
                            "missing_pct": meta["missing_pct"],
                            "unique_values": meta["unique_values"],
                            "correlation": "-",
                            "action": "dropped",
                        }
                    )

        # Add flagged correlated columns
        if "highly_correlated" in self.flagged_columns:
            for col1, col2, corr in self.flagged_columns["highly_correlated"]:
                # Find metadata for col2 (the one that would be dropped if configured)
                meta = next((m for m in self.column_metadata if m["column"] == col2), None)
                if meta:
                    report_rows.append(
                        {
                            "column": col2,
                            "reason": f"highly_correlated_with_{col1}",
                            "missing_pct": meta["missing_pct"],
                            "unique_values": meta["unique_values"],
                            "correlation": corr,
                            "action": "flagged",
                        }
                    )

        # Create DataFrame and save
        report_df = pd.DataFrame(report_rows)

        # Sort by action (dropped first) then by reason
        if not report_df.empty:
            report_df = report_df.sort_values(["action", "reason", "column"])

        report_df.to_csv(output_path, index=False)
