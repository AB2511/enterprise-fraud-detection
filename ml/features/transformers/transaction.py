"""
Transaction Feature Transformers

Transformers for creating transaction-specific features like amount processing,
buckets, percentiles, and other transaction characteristics.
"""

import numpy as np
import pandas as pd

from ml.features.transformers.base import BaseFeatureTransformer, ValidationResult


class AmountTransformer(BaseFeatureTransformer):
    """
    Transformer for basic amount features.

    Creates:
    - amount (original)
    - log_amount (log transformation)
    - normalized_amount (z-score normalization)
    """

    def __init__(self, amount_column: str = "amount", log_offset: float = 1e-6, **kwargs):
        super().__init__(
            name="amount_transformer",
            version="1.0.0",
            description="Basic amount feature transformations including log and normalization",
            dependencies=[amount_column],
            amount_column=amount_column,
            log_offset=log_offset,
            **kwargs,
        )
        self.amount_column = amount_column
        self.log_offset = log_offset

        # Fit parameters
        self.amount_mean_ = None
        self.amount_std_ = None

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "AmountTransformer":
        """Fit the transformer by computing normalization parameters."""
        self._validate_input(X)

        with self.logger.stage_context("fitting_amount_transformer"):
            # Compute normalization parameters
            amounts = X[self.amount_column].dropna()
            self.amount_mean_ = amounts.mean()
            self.amount_std_ = amounts.std()

            # Update state
            self.is_fitted = True
            self.fit_statistics = {
                "amount_mean": self.amount_mean_,
                "amount_std": self.amount_std_,
                "amount_min": amounts.min(),
                "amount_max": amounts.max(),
                "amount_median": amounts.median(),
                "n_zero_amounts": (amounts == 0).sum(),
            }

            self.logger.info(
                f"Amount transformer fitted - mean: {self.amount_mean_:.2f}, std: {self.amount_std_:.2f}"
            )

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform amount features."""
        self._check_fitted()
        self._validate_input(X)

        result = X.copy()

        with self.logger.stage_context("transforming_amount_features"):
            # Original amount (ensure float type)
            result["amount"] = X[self.amount_column].astype(float)

            # Log amount (handle zeros and negatives)
            amounts = X[self.amount_column]
            result["log_amount"] = np.log(np.maximum(amounts, self.log_offset))

            # Normalized amount (z-score)
            if self.amount_std_ > 0:
                result["normalized_amount"] = (amounts - self.amount_mean_) / self.amount_std_
            else:
                result["normalized_amount"] = 0.0

            # Update feature names
            self._feature_names_out = ["amount", "log_amount", "normalized_amount"]

            self.logger.info(f"Generated {len(self._feature_names_out)} amount features")

        # Update metadata
        self._update_metadata(X, result)

        return result

    def _custom_validation(self, X: pd.DataFrame) -> ValidationResult:
        """Custom validation for amount transformer."""
        errors = []
        warnings = []

        amounts = X[self.amount_column]

        # Check for negative amounts
        negative_count = (amounts < 0).sum()
        if negative_count > 0:
            warnings.append(f"Found {negative_count} negative amounts")

        # Check for extremely large amounts (potential outliers)
        if amounts.max() > 1000000:  # > 1M
            warnings.append(f"Found extremely large amounts (max: {amounts.max():.2f})")

        # Check for too many zero amounts
        zero_count = (amounts == 0).sum()
        zero_rate = zero_count / len(amounts)
        if zero_rate > 0.1:  # > 10%
            warnings.append(f"High rate of zero amounts: {zero_rate:.1%}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class AmountBucketTransformer(BaseFeatureTransformer):
    """
    Transformer for amount bucketing features.

    Creates categorical buckets for transaction amounts.
    """

    def __init__(
        self,
        amount_column: str = "amount",
        n_buckets: int = 10,
        bucket_method: str = "quantile",  # "quantile", "uniform", "custom"
        custom_thresholds: list[float] = None,
        **kwargs,
    ):
        super().__init__(
            name="amount_bucket_transformer",
            version="1.0.0",
            description="Create categorical buckets for transaction amounts",
            dependencies=[amount_column],
            amount_column=amount_column,
            n_buckets=n_buckets,
            bucket_method=bucket_method,
            custom_thresholds=custom_thresholds,
            **kwargs,
        )
        self.amount_column = amount_column
        self.n_buckets = n_buckets
        self.bucket_method = bucket_method
        self.custom_thresholds = custom_thresholds or []

        # Fit parameters
        self.bucket_edges_ = None
        self.bucket_labels_ = None

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "AmountBucketTransformer":
        """Fit the transformer by computing bucket edges."""
        self._validate_input(X)

        with self.logger.stage_context("fitting_amount_bucket_transformer"):
            amounts = X[self.amount_column].dropna()

            if self.bucket_method == "quantile":
                # Quantile-based buckets
                quantiles = np.linspace(0, 1, self.n_buckets + 1)
                self.bucket_edges_ = amounts.quantile(quantiles).values
            elif self.bucket_method == "uniform":
                # Uniform-width buckets
                min_amt, max_amt = amounts.min(), amounts.max()
                self.bucket_edges_ = np.linspace(min_amt, max_amt, self.n_buckets + 1)
            elif self.bucket_method == "custom":
                # Custom thresholds
                if not self.custom_thresholds:
                    raise ValueError("custom_thresholds must be provided for custom bucket method")
                self.bucket_edges_ = np.array([0] + sorted(self.custom_thresholds) + [float("inf")])
                self.n_buckets = len(self.bucket_edges_) - 1
            else:
                raise ValueError(f"Unknown bucket_method: {self.bucket_method}")

            # Create bucket labels
            self.bucket_labels_ = [f"bucket_{i:02d}" for i in range(self.n_buckets)]

            # Update state
            self.is_fitted = True
            self.fit_statistics = {
                "bucket_method": self.bucket_method,
                "n_buckets": self.n_buckets,
                "bucket_edges": self.bucket_edges_.tolist(),
                "bucket_labels": self.bucket_labels_,
            }

            self.logger.info(f"Amount bucket transformer fitted with {self.n_buckets} buckets")

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform amounts into buckets."""
        self._check_fitted()
        self._validate_input(X)

        result = X.copy()

        with self.logger.stage_context("transforming_amount_buckets"):
            amounts = X[self.amount_column]

            # Create buckets
            bucket_indices = pd.cut(
                amounts, bins=self.bucket_edges_, labels=False, include_lowest=True
            )
            result["amount_bucket"] = bucket_indices

            # Create one-hot encoded buckets
            for i, label in enumerate(self.bucket_labels_):
                result[f"amount_{label}"] = (bucket_indices == i).astype(int)

            # Update feature names
            self._feature_names_out = ["amount_bucket"] + [
                f"amount_{label}" for label in self.bucket_labels_
            ]

            self.logger.info(f"Generated {len(self._feature_names_out)} bucket features")

        # Update metadata
        self._update_metadata(X, result)

        return result


class AmountPercentileTransformer(BaseFeatureTransformer):
    """
    Transformer for amount percentile features.

    Creates percentile ranks for transaction amounts.
    """

    def __init__(self, amount_column: str = "amount", percentiles: list[int] = None, **kwargs):
        if percentiles is None:
            percentiles = [25, 50, 75, 90, 95, 99]

        super().__init__(
            name="amount_percentile_transformer",
            version="1.0.0",
            description="Create percentile features for transaction amounts",
            dependencies=[amount_column],
            amount_column=amount_column,
            percentiles=percentiles,
            **kwargs,
        )
        self.amount_column = amount_column
        self.percentiles = sorted(percentiles)

        # Fit parameters
        self.percentile_values_ = {}

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "AmountPercentileTransformer":
        """Fit the transformer by computing percentile values."""
        self._validate_input(X)

        with self.logger.stage_context("fitting_amount_percentile_transformer"):
            amounts = X[self.amount_column].dropna()

            # Compute percentile values
            for p in self.percentiles:
                self.percentile_values_[p] = amounts.quantile(p / 100)

            # Update state
            self.is_fitted = True
            self.fit_statistics = {
                "percentiles": self.percentiles,
                "percentile_values": self.percentile_values_,
                "min_amount": amounts.min(),
                "max_amount": amounts.max(),
            }

            self.logger.info(
                f"Amount percentile transformer fitted for percentiles: {self.percentiles}"
            )

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform amounts into percentile features."""
        self._check_fitted()
        self._validate_input(X)

        result = X.copy()

        with self.logger.stage_context("transforming_amount_percentiles"):
            amounts = X[self.amount_column]

            # Create percentile rank (0-1 scale)
            result["amount_percentile_rank"] = amounts.rank(pct=True)

            # Create binary features for percentile thresholds
            for p in self.percentiles:
                threshold = self.percentile_values_[p]
                result[f"amount_above_p{p}"] = (amounts > threshold).astype(int)

            # Create percentile bin assignment
            bin_edges = [0] + list(self.percentile_values_.values()) + [float("inf")]
            percentile_bins = pd.cut(amounts, bins=bin_edges, labels=False, include_lowest=True)
            result["amount_percentile_bin"] = percentile_bins

            # Update feature names
            self._feature_names_out = ["amount_percentile_rank", "amount_percentile_bin"] + [
                f"amount_above_p{p}" for p in self.percentiles
            ]

            self.logger.info(f"Generated {len(self._feature_names_out)} percentile features")

        # Update metadata
        self._update_metadata(X, result)

        return result
