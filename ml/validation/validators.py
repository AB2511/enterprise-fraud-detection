"""
Base Validators

Reusable validation infrastructure (no dataset-specific rules).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import pandas as pd

# ============================================================================
# Base Validator
# ============================================================================


class ValidationCheck:
    """Single validation check result"""

    def __init__(
        self,
        name: str,
        passed: bool,
        severity: str,  # "critical", "error", "warning"
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.name = name
        self.passed = passed
        self.severity = severity
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() + "Z",
        }


class BaseValidator(ABC):
    """
    Abstract base class for validators.

    All validators implement this interface for consistency.
    """

    def __init__(self, name: str):
        """
        Initialize validator.

        Args:
            name: Validator name
        """
        self.name = name
        self.checks: list[ValidationCheck] = []

    @abstractmethod
    def validate(self, df: pd.DataFrame) -> list[ValidationCheck]:
        """
        Validate DataFrame.

        Args:
            df: DataFrame to validate

        Returns:
            List of ValidationCheck results
        """
        pass

    def get_summary(self) -> dict[str, Any]:
        """Get validation summary"""
        if not self.checks:
            return {
                "validator": self.name,
                "total_checks": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0,
            }

        passed = sum(1 for c in self.checks if c.passed)
        failed = sum(1 for c in self.checks if not c.passed and c.severity in ["critical", "error"])
        warnings = sum(1 for c in self.checks if not c.passed and c.severity == "warning")

        return {
            "validator": self.name,
            "total_checks": len(self.checks),
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
        }


# ============================================================================
# Schema Validator
# ============================================================================


class SchemaValidator(BaseValidator):
    """Validate DataFrame schema"""

    def __init__(
        self,
        required_columns: list[str],
        optional_columns: list[str] | None = None,
        column_types: dict[str, str] | None = None,
    ):
        """
        Initialize schema validator.

        Args:
            required_columns: List of required column names
            optional_columns: List of optional column names
            column_types: Expected data types {column: dtype}
        """
        super().__init__("SchemaValidator")
        self.required_columns = required_columns
        self.optional_columns = optional_columns or []
        self.column_types = column_types or {}

    def validate(self, df: pd.DataFrame) -> list[ValidationCheck]:
        """Validate schema"""
        self.checks = []

        # Check required columns
        missing_columns = [col for col in self.required_columns if col not in df.columns]
        if missing_columns:
            self.checks.append(
                ValidationCheck(
                    name="required_columns",
                    passed=False,
                    severity="critical",
                    message=f"Missing required columns: {missing_columns}",
                    details={"missing_columns": missing_columns},
                )
            )
        else:
            self.checks.append(
                ValidationCheck(
                    name="required_columns",
                    passed=True,
                    severity="critical",
                    message="All required columns present",
                )
            )

        # Check column types
        for column, expected_type in self.column_types.items():
            if column in df.columns:
                actual_type = str(df[column].dtype)
                if not self._types_compatible(actual_type, expected_type):
                    self.checks.append(
                        ValidationCheck(
                            name=f"column_type_{column}",
                            passed=False,
                            severity="error",
                            message=f"Column '{column}' has type '{actual_type}', expected '{expected_type}'",
                            details={
                                "column": column,
                                "actual": actual_type,
                                "expected": expected_type,
                            },
                        )
                    )

        return self.checks

    def _types_compatible(self, actual: str, expected: str) -> bool:
        """Check if data types are compatible"""
        # Simplified type checking
        type_groups = {
            "numeric": ["int", "float", "Int", "Float"],
            "string": ["object", "string", "str"],
            "datetime": ["datetime", "timestamp"],
            "boolean": ["bool", "boolean"],
        }

        for group_types in type_groups.values():
            if any(t in actual.lower() for t in group_types) and any(
                t in expected.lower() for t in group_types
            ):
                return True

        return actual == expected


# ============================================================================
# Missing Value Validator
# ============================================================================


class MissingValueValidator(BaseValidator):
    """Validate missing values"""

    def __init__(
        self,
        max_missing_rate: float = 0.10,
        critical_columns: list[str] | None = None,
    ):
        """
        Initialize missing value validator.

        Args:
            max_missing_rate: Maximum allowed missing rate (0.0-1.0)
            critical_columns: Columns that cannot have missing values
        """
        super().__init__("MissingValueValidator")
        self.max_missing_rate = max_missing_rate
        self.critical_columns = critical_columns or []

    def validate(self, df: pd.DataFrame) -> list[ValidationCheck]:
        """Validate missing values"""
        self.checks = []

        # Check critical columns
        for column in self.critical_columns:
            if column in df.columns:
                missing_count = df[column].isna().sum()
                if missing_count > 0:
                    self.checks.append(
                        ValidationCheck(
                            name=f"critical_column_{column}",
                            passed=False,
                            severity="critical",
                            message=f"Critical column '{column}' has {missing_count} missing values",
                            details={"column": column, "missing_count": int(missing_count)},
                        )
                    )

        # Check all columns
        for column in df.columns:
            missing_rate = df[column].isna().mean()
            if missing_rate > self.max_missing_rate:
                self.checks.append(
                    ValidationCheck(
                        name=f"missing_rate_{column}",
                        passed=False,
                        severity="warning" if column not in self.critical_columns else "error",
                        message=f"Column '{column}' has {missing_rate:.2%} missing values (limit: {self.max_missing_rate:.2%})",
                        details={"column": column, "missing_rate": float(missing_rate)},
                    )
                )

        # Overall check
        if not self.checks:
            self.checks.append(
                ValidationCheck(
                    name="missing_values",
                    passed=True,
                    severity="info",
                    message="Missing value rates within acceptable limits",
                )
            )

        return self.checks


# ============================================================================
# Duplicate Validator
# ============================================================================


class DuplicateValidator(BaseValidator):
    """Validate duplicate records"""

    def __init__(
        self,
        max_duplicate_rate: float = 0.01,
        subset: list[str] | None = None,
    ):
        """
        Initialize duplicate validator.

        Args:
            max_duplicate_rate: Maximum allowed duplicate rate
            subset: Columns to check for duplicates (None = all columns)
        """
        super().__init__("DuplicateValidator")
        self.max_duplicate_rate = max_duplicate_rate
        self.subset = subset

    def validate(self, df: pd.DataFrame) -> list[ValidationCheck]:
        """Validate duplicates"""
        self.checks = []

        # Check duplicates
        duplicates = df.duplicated(subset=self.subset, keep=False)
        duplicate_count = duplicates.sum()
        duplicate_rate = duplicate_count / len(df)

        if duplicate_rate > self.max_duplicate_rate:
            self.checks.append(
                ValidationCheck(
                    name="duplicate_rate",
                    passed=False,
                    severity="warning",
                    message=f"Duplicate rate {duplicate_rate:.2%} exceeds limit {self.max_duplicate_rate:.2%}",
                    details={
                        "duplicate_count": int(duplicate_count),
                        "duplicate_rate": float(duplicate_rate),
                        "total_records": len(df),
                    },
                )
            )
        else:
            self.checks.append(
                ValidationCheck(
                    name="duplicate_rate",
                    passed=True,
                    severity="info",
                    message=f"Duplicate rate {duplicate_rate:.2%} within acceptable limits",
                    details={"duplicate_count": int(duplicate_count)},
                )
            )

        return self.checks


# ============================================================================
# Value Range Validator
# ============================================================================


class ValueRangeValidator(BaseValidator):
    """Validate value ranges"""

    def __init__(self, range_specs: dict[str, dict[str, float]]):
        """
        Initialize range validator.

        Args:
            range_specs: {column: {"min": value, "max": value}}
        """
        super().__init__("ValueRangeValidator")
        self.range_specs = range_specs

    def validate(self, df: pd.DataFrame) -> list[ValidationCheck]:
        """Validate ranges"""
        self.checks = []

        for column, spec in self.range_specs.items():
            if column not in df.columns:
                continue

            min_val = spec.get("min")
            max_val = spec.get("max")

            # Check minimum
            if min_val is not None:
                violations = df[column] < min_val
                violation_count = violations.sum()
                if violation_count > 0:
                    self.checks.append(
                        ValidationCheck(
                            name=f"min_value_{column}",
                            passed=False,
                            severity="error",
                            message=f"Column '{column}' has {violation_count} values below minimum {min_val}",
                            details={
                                "column": column,
                                "min_required": float(min_val),
                                "min_found": float(df[column].min()),
                                "violation_count": int(violation_count),
                            },
                        )
                    )

            # Check maximum
            if max_val is not None:
                violations = df[column] > max_val
                violation_count = violations.sum()
                if violation_count > 0:
                    self.checks.append(
                        ValidationCheck(
                            name=f"max_value_{column}",
                            passed=False,
                            severity="error",
                            message=f"Column '{column}' has {violation_count} values above maximum {max_val}",
                            details={
                                "column": column,
                                "max_required": float(max_val),
                                "max_found": float(df[column].max()),
                                "violation_count": int(violation_count),
                            },
                        )
                    )

        if not self.checks:
            self.checks.append(
                ValidationCheck(
                    name="value_ranges",
                    passed=True,
                    severity="info",
                    message="All values within specified ranges",
                )
            )

        return self.checks


# ============================================================================
# Null Percentage Validator
# ============================================================================


class NullPercentageValidator(BaseValidator):
    """Validate null percentages"""

    def __init__(self, max_null_percentage: float = 0.05):
        """
        Initialize null percentage validator.

        Args:
            max_null_percentage: Maximum allowed null percentage (0.0-1.0)
        """
        super().__init__("NullPercentageValidator")
        self.max_null_percentage = max_null_percentage

    def validate(self, df: pd.DataFrame) -> list[ValidationCheck]:
        """Validate null percentages"""
        self.checks = []

        for column in df.columns:
            null_percentage = df[column].isnull().mean()
            if null_percentage > self.max_null_percentage:
                self.checks.append(
                    ValidationCheck(
                        name=f"null_percentage_{column}",
                        passed=False,
                        severity="warning",
                        message=f"Column '{column}' has {null_percentage:.2%} nulls (limit: {self.max_null_percentage:.2%})",
                        details={"column": column, "null_percentage": float(null_percentage)},
                    )
                )

        if not self.checks:
            self.checks.append(
                ValidationCheck(
                    name="null_percentages",
                    passed=True,
                    severity="info",
                    message="Null percentages within acceptable limits",
                )
            )

        return self.checks


# ============================================================================
# Timestamp Validator
# ============================================================================


class TimestampValidator(BaseValidator):
    """Validate timestamp columns"""

    def __init__(
        self,
        timestamp_columns: list[str],
        allow_future: bool = False,
        check_ordering: bool = True,
    ):
        """
        Initialize timestamp validator.

        Args:
            timestamp_columns: List of timestamp column names
            allow_future: Allow future timestamps
            check_ordering: Check if timestamps are ordered
        """
        super().__init__("TimestampValidator")
        self.timestamp_columns = timestamp_columns
        self.allow_future = allow_future
        self.check_ordering = check_ordering

    def validate(self, df: pd.DataFrame) -> list[ValidationCheck]:
        """Validate timestamps"""
        self.checks = []
        now = pd.Timestamp.now(tz="UTC")

        for column in self.timestamp_columns:
            if column not in df.columns:
                continue

            # Check data type
            if not pd.api.types.is_datetime64_any_dtype(df[column]):
                self.checks.append(
                    ValidationCheck(
                        name=f"timestamp_type_{column}",
                        passed=False,
                        severity="error",
                        message=f"Column '{column}' is not datetime type",
                        details={"column": column, "actual_type": str(df[column].dtype)},
                    )
                )
                continue

            # Check future timestamps
            if not self.allow_future:
                future_count = (df[column] > now).sum()
                if future_count > 0:
                    self.checks.append(
                        ValidationCheck(
                            name=f"future_timestamps_{column}",
                            passed=False,
                            severity="error",
                            message=f"Column '{column}' has {future_count} future timestamps",
                            details={"column": column, "future_count": int(future_count)},
                        )
                    )

            # Check ordering
            if self.check_ordering:
                if not df[column].is_monotonic_increasing:
                    self.checks.append(
                        ValidationCheck(
                            name=f"timestamp_ordering_{column}",
                            passed=False,
                            severity="warning",
                            message=f"Column '{column}' is not monotonically increasing",
                            details={"column": column},
                        )
                    )

        if not self.checks:
            self.checks.append(
                ValidationCheck(
                    name="timestamps",
                    passed=True,
                    severity="info",
                    message="Timestamp validation passed",
                )
            )

        return self.checks


# ============================================================================
# Categorical Consistency Validator
# ============================================================================


class CategoricalConsistencyValidator(BaseValidator):
    """Validate categorical consistency"""

    def __init__(
        self,
        categorical_columns: list[str],
        max_unique_ratio: float = 0.50,
    ):
        """
        Initialize categorical validator.

        Args:
            categorical_columns: List of categorical column names
            max_unique_ratio: Maximum unique value ratio (cardinality check)
        """
        super().__init__("CategoricalConsistencyValidator")
        self.categorical_columns = categorical_columns
        self.max_unique_ratio = max_unique_ratio

    def validate(self, df: pd.DataFrame) -> list[ValidationCheck]:
        """Validate categorical consistency"""
        self.checks = []

        for column in self.categorical_columns:
            if column not in df.columns:
                continue

            # Check cardinality
            unique_ratio = df[column].nunique() / len(df)
            if unique_ratio > self.max_unique_ratio:
                self.checks.append(
                    ValidationCheck(
                        name=f"cardinality_{column}",
                        passed=False,
                        severity="warning",
                        message=f"Column '{column}' has high cardinality ({unique_ratio:.2%})",
                        details={
                            "column": column,
                            "unique_values": int(df[column].nunique()),
                            "unique_ratio": float(unique_ratio),
                        },
                    )
                )

        if not self.checks:
            self.checks.append(
                ValidationCheck(
                    name="categorical_consistency",
                    passed=True,
                    severity="info",
                    message="Categorical consistency validated",
                )
            )

        return self.checks
