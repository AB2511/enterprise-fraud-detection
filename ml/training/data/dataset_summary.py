"""
Dataset summary generation for IEEE-CIS dataset.

Generates concise summaries including:
- Row and column counts
- Target distribution
- Missing value statistics
- Memory usage
- Data types
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from .config import IEEECISSchema

logger = logging.getLogger(__name__)


@dataclass
class DatasetSummary:
    """
    Concise dataset summary for validation and reporting.

    Attributes:
        num_rows: Total number of rows
        num_columns: Total number of columns
        memory_usage_mb: Memory usage in megabytes
        target_distribution: Dictionary with fraud statistics
        missing_value_stats: Dictionary with missing value statistics
        column_types: Dictionary of column type counts
        dataset_name: Name of the dataset
    """

    num_rows: int
    num_columns: int
    memory_usage_mb: float
    target_distribution: dict[str, float | int]
    missing_value_stats: dict[str, float | int]
    column_types: dict[str, int]
    dataset_name: str = "IEEE-CIS Fraud Detection"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self, path: Path) -> None:
        """
        Save summary to JSON file.

        Args:
            path: Output file path
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Dataset summary saved to {path}")

    def __str__(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Dataset Summary: {self.dataset_name}",
            "=" * 60,
            f"Rows: {self.num_rows:,}",
            f"Columns: {self.num_columns}",
            f"Memory Usage: {self.memory_usage_mb:.2f} MB",
            "",
            "Target Distribution:",
            f"  Total Samples: {self.target_distribution['total_samples']:,}",
            f"  Fraud Cases: {self.target_distribution['fraud_cases']:,}",
            f"  Legitimate Cases: {self.target_distribution['legitimate_cases']:,}",
            f"  Fraud Rate: {self.target_distribution['fraud_rate']:.4f} "
            f"({self.target_distribution['fraud_rate'] * 100:.2f}%)",
            "",
            "Missing Values:",
            f"  Columns with Missing: {self.missing_value_stats['columns_with_missing']}",
            f"  Total Missing: {self.missing_value_stats['total_missing_values']:,}",
            f"  Missing Rate: {self.missing_value_stats['overall_missing_rate']:.4f} "
            f"({self.missing_value_stats['overall_missing_rate'] * 100:.2f}%)",
            f"  Max Missing Rate: {self.missing_value_stats['max_missing_rate']:.4f} "
            f"({self.missing_value_stats['max_missing_rate'] * 100:.2f}%)",
            "",
            "Column Types:",
        ]

        for dtype, count in sorted(self.column_types.items()):
            lines.append(f"  {dtype}: {count}")

        return "\n".join(lines)


def generate_dataset_summary(
    df: pd.DataFrame, schema: IEEECISSchema | None = None
) -> DatasetSummary:
    """
    Generate comprehensive dataset summary.

    Args:
        df: DataFrame to summarize
        schema: Schema definition. If None, uses default IEEECISSchema

    Returns:
        DatasetSummary with statistics
    """
    if schema is None:
        schema = IEEECISSchema()

    logger.info("Generating dataset summary")

    # Basic stats
    num_rows = len(df)
    num_columns = len(df.columns)
    memory_usage_mb = df.memory_usage(deep=True).sum() / 1024 / 1024

    # Target distribution
    if schema.target_col in df.columns:
        target = df[schema.target_col]
        fraud_cases = int(target.sum())
        legitimate_cases = int((target == 0).sum())
        fraud_rate = float(target.mean())
    else:
        fraud_cases = 0
        legitimate_cases = num_rows
        fraud_rate = 0.0

    target_distribution = {
        "total_samples": num_rows,
        "fraud_cases": fraud_cases,
        "legitimate_cases": legitimate_cases,
        "fraud_rate": fraud_rate,
    }

    # Missing value statistics
    missing_per_column = df.isna().sum()
    columns_with_missing = int((missing_per_column > 0).sum())
    total_missing = int(missing_per_column.sum())
    overall_missing_rate = float(total_missing / (num_rows * num_columns))

    missing_rates = missing_per_column / num_rows
    max_missing_rate = float(missing_rates.max())

    missing_value_stats = {
        "columns_with_missing": columns_with_missing,
        "total_missing_values": total_missing,
        "overall_missing_rate": overall_missing_rate,
        "max_missing_rate": max_missing_rate,
    }

    # Column types
    type_counts = df.dtypes.value_counts()
    column_types = {str(dtype): int(count) for dtype, count in type_counts.items()}

    summary = DatasetSummary(
        num_rows=num_rows,
        num_columns=num_columns,
        memory_usage_mb=memory_usage_mb,
        target_distribution=target_distribution,
        missing_value_stats=missing_value_stats,
        column_types=column_types,
    )

    logger.info("Dataset summary generated successfully")

    return summary
