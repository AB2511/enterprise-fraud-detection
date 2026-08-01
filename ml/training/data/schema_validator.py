"""
Schema validation for IEEE-CIS dataset.

Validates:
- Required columns exist
- Column types are appropriate
- Key columns have valid values
"""

import logging
from dataclasses import dataclass, field

import pandas as pd

from .config import IEEECISSchema

logger = logging.getLogger(__name__)


@dataclass
class SchemaValidationResult:
    """
    Result of schema validation.

    Attributes:
        is_valid: Whether schema validation passed
        errors: List of validation errors (blocking issues)
        warnings: List of validation warnings (non-blocking issues)
        missing_columns: Columns that are required but missing
        extra_columns: Columns present but not in schema
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_columns: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        """Human-readable validation result."""
        lines = [f"Schema Validation: {'✓ PASSED' if self.is_valid else '✗ FAILED'}"]

        if self.errors:
            lines.append("\nErrors:")
            for error in self.errors:
                lines.append(f"  ✗ {error}")

        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")

        if self.missing_columns:
            lines.append(f"\nMissing columns: {', '.join(self.missing_columns)}")

        if self.extra_columns:
            lines.append(f"\nExtra columns (not in schema): {len(self.extra_columns)} columns")

        return "\n".join(lines)


def validate_schema(
    df: pd.DataFrame, table_name: str = "merged", schema: IEEECISSchema | None = None
) -> SchemaValidationResult:
    """
    Validate DataFrame against IEEE-CIS schema.

    Args:
        df: DataFrame to validate
        table_name: Name of table for error messages ('transaction', 'identity', 'merged')
        schema: Schema definition. If None, uses default IEEECISSchema

    Returns:
        SchemaValidationResult with validation details
    """
    if schema is None:
        schema = IEEECISSchema()

    errors: list[str] = []
    warnings: list[str] = []
    missing_columns: list[str] = []
    extra_columns: list[str] = []

    # Determine required columns based on table name
    if table_name == "transaction":
        required_cols = set(schema.required_transaction_cols)
    elif table_name == "identity":
        required_cols = set(schema.required_identity_cols)
    else:  # merged or unknown
        required_cols = set(schema.required_transaction_cols)

    # Check for missing required columns
    df_columns = set(df.columns)
    missing = required_cols - df_columns

    if missing:
        missing_columns = sorted(missing)
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")

    # Check TransactionID exists and is valid
    if schema.transaction_id_col in df.columns:
        transaction_id = df[schema.transaction_id_col]

        # Check for nulls
        null_count = transaction_id.isna().sum()
        if null_count > 0:
            errors.append(
                f"{schema.transaction_id_col} has {null_count:,} null values "
                f"({null_count / len(df) * 100:.2f}%)"
            )

        # Check for duplicates
        duplicate_count = transaction_id.duplicated().sum()
        if duplicate_count > 0:
            errors.append(
                f"{schema.transaction_id_col} has {duplicate_count:,} duplicate values "
                f"({duplicate_count / len(df) * 100:.2f}%)"
            )
    else:
        errors.append(f"Key column {schema.transaction_id_col} not found")

    # Check target column (only for transaction or merged tables)
    if table_name in ("transaction", "merged"):
        if schema.target_col in df.columns:
            target = df[schema.target_col]

            # Check for nulls
            null_count = target.isna().sum()
            if null_count > 0:
                errors.append(
                    f"{schema.target_col} has {null_count:,} null values "
                    f"({null_count / len(df) * 100:.2f}%)"
                )

            # Check values are binary (0 or 1)
            unique_values = target.dropna().unique()
            if not set(unique_values).issubset({0, 1}):
                errors.append(f"{schema.target_col} contains non-binary values: {unique_values}")

            # Check fraud rate is reasonable
            fraud_rate = target.mean()
            if fraud_rate < 0.001:
                warnings.append(f"Very low fraud rate: {fraud_rate * 100:.4f}% (< 0.1%)")
            elif fraud_rate > 0.5:
                warnings.append(f"Unusually high fraud rate: {fraud_rate * 100:.2f}% (> 50%)")
        else:
            errors.append(f"Target column {schema.target_col} not found")

    # Check DataFrame is not empty
    if len(df) == 0:
        errors.append("DataFrame is empty (0 rows)")

    # Identify extra columns (informational only)
    if table_name == "transaction":
        extra_columns = sorted(df_columns - set(schema.required_transaction_cols))
    elif table_name == "identity":
        extra_columns = sorted(df_columns - set(schema.required_identity_cols))

    is_valid = len(errors) == 0

    result = SchemaValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        missing_columns=missing_columns,
        extra_columns=extra_columns,
    )

    # Log result
    if is_valid:
        logger.info(f"Schema validation passed for {table_name} table")
    else:
        logger.error(f"Schema validation failed for {table_name} table: {len(errors)} errors")

    return result
