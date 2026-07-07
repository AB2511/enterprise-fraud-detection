"""
Base Feature Transformer

Abstract base class for all feature transformers in the fraud detection system.
Every feature transformer must inherit from BaseFeatureTransformer and implement
the required abstract methods.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ml.utils.logging_config import get_logger


class FeatureMetadata:
    """Metadata container for feature transformers."""

    def __init__(
        self,
        name: str,
        version: str,
        description: str,
        owner: str = "ml-team",
        dependencies: list[str] = None,
        input_columns: list[str] = None,
        output_columns: list[str] = None,
        parameters: dict[str, Any] = None,
    ):
        self.name = name
        self.version = version
        self.description = description
        self.owner = owner
        self.dependencies = dependencies or []
        self.input_columns = input_columns or []
        self.output_columns = output_columns or []
        self.parameters = parameters or {}
        self.created_at = datetime.utcnow().isoformat()
        self.fitted_at: str | None = None
        self.validation_results: dict[str, Any] = {}
        self.statistics: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "owner": self.owner,
            "dependencies": self.dependencies,
            "input_columns": self.input_columns,
            "output_columns": self.output_columns,
            "parameters": self.parameters,
            "created_at": self.created_at,
            "fitted_at": self.fitted_at,
            "validation_results": self.validation_results,
            "statistics": self.statistics,
        }


class ValidationResult:
    """Container for feature validation results."""

    def __init__(self, is_valid: bool, errors: list[str] = None, warnings: list[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.validated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "validated_at": self.validated_at,
        }


class BaseFeatureTransformer(ABC):
    """
    Abstract base class for all feature transformers.

    Every feature transformer must implement:
    - fit(): Learn parameters from training data
    - transform(): Apply transformation to new data
    - fit_transform(): Combined fit and transform
    - metadata(): Return feature metadata
    - validation(): Validate feature correctness
    - version(): Return transformer version
    """

    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        owner: str = "ml-team",
        dependencies: list[str] = None,
        **kwargs,
    ):
        """
        Initialize base feature transformer.

        Args:
            name: Transformer name (must be unique)
            version: Transformer version (semantic versioning)
            description: Human-readable description
            owner: Team/person responsible for this transformer
            dependencies: List of required column names
            **kwargs: Additional parameters
        """
        self.name = name
        self._version = version
        self.description = description
        self.owner = owner
        self.dependencies = dependencies or []
        self.parameters = kwargs

        # State tracking
        self.is_fitted = False
        self.fitted_at: datetime | None = None
        self.fit_statistics: dict[str, Any] = {}

        # Logging
        self.logger = get_logger(f"ml.features.{self.__class__.__name__}")

        # Initialize metadata
        self._metadata = FeatureMetadata(
            name=name,
            version=version,
            description=description,
            owner=owner,
            dependencies=dependencies,
            parameters=self.parameters,
        )

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "BaseFeatureTransformer":
        """
        Learn parameters from training data.

        Args:
            X: Input DataFrame
            y: Optional target series

        Returns:
            Self for method chaining
        """
        pass

    @abstractmethod
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Apply transformation to input data.

        Args:
            X: Input DataFrame

        Returns:
            Transformed DataFrame
        """
        pass

    def fit_transform(self, X: pd.DataFrame, y: pd.Series | None = None) -> pd.DataFrame:
        """
        Fit transformer and transform data in one step.

        Args:
            X: Input DataFrame
            y: Optional target series

        Returns:
            Transformed DataFrame
        """
        return self.fit(X, y).transform(X)

    def metadata(self) -> FeatureMetadata:
        """
        Return feature metadata.

        Returns:
            Feature metadata object
        """
        return self._metadata

    def validation(self, X: pd.DataFrame) -> ValidationResult:
        """
        Validate feature correctness and data quality.

        Args:
            X: Input DataFrame to validate

        Returns:
            Validation result
        """
        errors = []
        warnings = []

        # Check required dependencies
        missing_deps = set(self.dependencies) - set(X.columns)
        if missing_deps:
            errors.append(f"Missing required columns: {list(missing_deps)}")

        # Check for empty DataFrame
        if X.empty:
            errors.append("Input DataFrame is empty")

        # Check for all-null columns in dependencies
        for col in self.dependencies:
            if col in X.columns and X[col].isnull().all():
                warnings.append(f"Column '{col}' contains only null values")

        # Custom validation (can be overridden)
        custom_result = self._custom_validation(X)
        errors.extend(custom_result.errors)
        warnings.extend(custom_result.warnings)

        # Update metadata
        validation_result = ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

        self._metadata.validation_results = validation_result.to_dict()

        return validation_result

    def version(self) -> str:
        """
        Return transformer version.

        Returns:
            Version string
        """
        return self._version

    def get_feature_names_out(self, input_features: list[str] | None = None) -> list[str]:
        """
        Get output feature names for transformation.

        Args:
            input_features: Input feature names

        Returns:
            Output feature names
        """
        # Default implementation - should be overridden by subclasses
        if hasattr(self, "_feature_names_out"):
            return self._feature_names_out
        else:
            return input_features or []

    def get_params(self) -> dict[str, Any]:
        """
        Get transformer parameters.

        Returns:
            Dictionary of parameters
        """
        return self.parameters.copy()

    def set_params(self, **params) -> "BaseFeatureTransformer":
        """
        Set transformer parameters.

        Args:
            **params: Parameters to set

        Returns:
            Self for method chaining
        """
        self.parameters.update(params)
        self._metadata.parameters = self.parameters
        return self

    def _check_fitted(self):
        """Check if transformer has been fitted."""
        if not self.is_fitted:
            raise ValueError(f"Transformer {self.name} must be fitted before transform")

    def _validate_input(self, X: pd.DataFrame):
        """
        Validate input DataFrame.

        Args:
            X: Input DataFrame to validate
        """
        if not isinstance(X, pd.DataFrame):
            raise ValueError("Input must be a pandas DataFrame")

        if X.empty:
            raise ValueError("Input DataFrame cannot be empty")

        # Check required dependencies
        missing_deps = set(self.dependencies) - set(X.columns)
        if missing_deps:
            raise ValueError(f"Missing required columns: {list(missing_deps)}")

    def _custom_validation(self, X: pd.DataFrame) -> ValidationResult:
        """
        Custom validation logic (to be overridden by subclasses).

        Args:
            X: Input DataFrame

        Returns:
            Validation result
        """
        return ValidationResult(is_valid=True)

    def _compute_statistics(self, X: pd.DataFrame) -> dict[str, Any]:
        """
        Compute statistics for the transformer.

        Args:
            X: Input DataFrame

        Returns:
            Dictionary of statistics
        """
        stats = {
            "n_samples": len(X),
            "n_features": len(X.columns),
            "memory_usage_mb": X.memory_usage(deep=True).sum() / (1024 * 1024),
            "missing_values": X.isnull().sum().to_dict(),
        }

        # Add dependency-specific stats
        for col in self.dependencies:
            if col in X.columns:
                if X[col].dtype in ["int64", "float64"]:
                    stats[f"{col}_mean"] = X[col].mean()
                    stats[f"{col}_std"] = X[col].std()
                    stats[f"{col}_min"] = X[col].min()
                    stats[f"{col}_max"] = X[col].max()
                elif X[col].dtype == "object" or pd.api.types.is_categorical_dtype(X[col]):
                    stats[f"{col}_nunique"] = X[col].nunique()
                    stats[f"{col}_top_values"] = X[col].value_counts().head(5).to_dict()

        return stats

    def _update_metadata(self, X: pd.DataFrame, output_df: pd.DataFrame):
        """
        Update metadata after fitting/transforming.

        Args:
            X: Input DataFrame
            output_df: Output DataFrame
        """
        self._metadata.input_columns = list(X.columns)
        self._metadata.output_columns = list(output_df.columns)
        self._metadata.statistics = self._compute_statistics(X)

        if self.is_fitted:
            self._metadata.fitted_at = datetime.utcnow().isoformat()

    def save_metadata(self, path: str | Path):
        """
        Save transformer metadata to file.

        Args:
            path: File path to save metadata
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(self._metadata.to_dict(), f, indent=2)

        self.logger.info(f"Metadata saved to {path}")

    def load_metadata(self, path: str | Path):
        """
        Load transformer metadata from file.

        Args:
            path: File path to load metadata from
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Metadata file not found: {path}")

        with open(path) as f:
            metadata_dict = json.load(f)

        # Update metadata
        for key, value in metadata_dict.items():
            if hasattr(self._metadata, key):
                setattr(self._metadata, key, value)

        self.logger.info(f"Metadata loaded from {path}")

    def __repr__(self) -> str:
        """String representation of transformer."""
        status = "fitted" if self.is_fitted else "not fitted"
        return f"{self.__class__.__name__}(name='{self.name}', version='{self._version}', {status})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.name} v{self._version}: {self.description}"
