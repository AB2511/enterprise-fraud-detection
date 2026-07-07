"""
Risk Feature Transformers

Transformers for creating risk-based features that combine multiple signals
to identify suspicious patterns and high-risk transactions.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from ml.features.transformers.base import BaseFeatureTransformer, ValidationResult


class RiskTransformer(BaseFeatureTransformer):
    """
    Transformer for risk-based features.

    Creates:
    - High value transaction indicators
    - Foreign transaction flags
    - Rapid transaction patterns
    - Suspicious merchant/device indicators
    - Composite risk scores
    """

    def __init__(
        self,
        amount_column: str = "amount",
        timestamp_column: str = "timestamp",
        customer_id_column: str = "customer_id",
        merchant_id_column: str = "merchant_id",
        device_id_column: str = "device_id",
        country_column: str = "country",
        high_value_threshold: float = None,
        rapid_transaction_minutes: int = 5,
        suspicious_merchant_threshold: float = 0.1,
        **kwargs,
    ):

        dependencies = [
            amount_column,
            timestamp_column,
            customer_id_column,
            merchant_id_column,
            device_id_column,
            country_column,
        ]

        super().__init__(
            name="risk_transformer",
            version="1.0.0",
            description="Risk-based features for fraud detection",
            dependencies=dependencies,
            amount_column=amount_column,
            timestamp_column=timestamp_column,
            customer_id_column=customer_id_column,
            merchant_id_column=merchant_id_column,
            device_id_column=device_id_column,
            country_column=country_column,
            high_value_threshold=high_value_threshold,
            rapid_transaction_minutes=rapid_transaction_minutes,
            suspicious_merchant_threshold=suspicious_merchant_threshold,
            **kwargs,
        )
        self.amount_column = amount_column
        self.timestamp_column = timestamp_column
        self.customer_id_column = customer_id_column
        self.merchant_id_column = merchant_id_column
        self.device_id_column = device_id_column
        self.country_column = country_column
        self.high_value_threshold = high_value_threshold
        self.rapid_transaction_minutes = rapid_transaction_minutes
        self.suspicious_merchant_threshold = suspicious_merchant_threshold

        # Fit parameters
        self.amount_thresholds_ = {}
        self.suspicious_merchants_ = set()
        self.suspicious_devices_ = set()
        self.foreign_countries_ = set()
        self.customer_profiles_ = {}

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "RiskTransformer":
        """Fit the transformer by computing risk thresholds and patterns."""
        self._validate_input(X)

        with self.logger.stage_context("fitting_risk_transformer"):
            # Compute amount thresholds
            amounts = X[self.amount_column].dropna()

            self.amount_thresholds_ = {
                "p50": amounts.quantile(0.50),
                "p75": amounts.quantile(0.75),
                "p90": amounts.quantile(0.90),
                "p95": amounts.quantile(0.95),
                "p99": amounts.quantile(0.99),
            }

            # Set high value threshold if not provided
            if self.high_value_threshold is None:
                self.high_value_threshold = self.amount_thresholds_["p95"]

            # Identify suspicious merchants (if fraud labels available)
            if y is not None:
                self._identify_suspicious_entities(X, y)
            else:
                self._identify_suspicious_entities_unsupervised(X)

            # Build customer profiles
            self._build_customer_profiles(X)

            # Identify foreign countries (countries with low transaction volume)
            country_counts = X[self.country_column].value_counts()
            low_volume_threshold = country_counts.quantile(0.25)
            self.foreign_countries_ = set(
                country_counts[country_counts <= low_volume_threshold].index
            )

            # Compute global statistics
            self.fit_statistics = {
                "high_value_threshold": self.high_value_threshold,
                "n_suspicious_merchants": len(self.suspicious_merchants_),
                "n_suspicious_devices": len(self.suspicious_devices_),
                "n_foreign_countries": len(self.foreign_countries_),
                "amount_thresholds": self.amount_thresholds_,
                "rapid_transaction_threshold_minutes": self.rapid_transaction_minutes,
            }

            # Update state
            self.is_fitted = True

            self.logger.info(
                f"Risk transformer fitted - high value threshold: {self.high_value_threshold:.2f}"
            )

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform data to create risk features."""
        self._check_fitted()
        self._validate_input(X)

        result = X.copy()

        with self.logger.stage_context("transforming_risk_features"):
            # Sort by customer and timestamp for time-based features
            df_sorted = result.sort_values([self.customer_id_column, self.timestamp_column])

            # Initialize feature arrays
            n_rows = len(df_sorted)

            # Amount-based risk features
            high_value_flags = (df_sorted[self.amount_column] > self.high_value_threshold).astype(
                int
            )
            amount_percentile_ranks = df_sorted[self.amount_column].rank(pct=True)

            # Time-based risk features
            rapid_transaction_flags = self._compute_rapid_transaction_flags(df_sorted)
            off_hours_flags = self._compute_off_hours_flags(df_sorted)

            # Entity-based risk features
            suspicious_merchant_flags = (
                df_sorted[self.merchant_id_column].isin(self.suspicious_merchants_).astype(int)
            )
            suspicious_device_flags = (
                df_sorted[self.device_id_column].isin(self.suspicious_devices_).astype(int)
            )
            foreign_transaction_flags = (
                df_sorted[self.country_column].isin(self.foreign_countries_).astype(int)
            )

            # Customer behavior deviation features
            behavior_deviation_scores = self._compute_behavior_deviation_scores(df_sorted)

            # Composite risk scores
            basic_risk_scores = self._compute_basic_risk_scores(
                df_sorted,
                high_value_flags,
                rapid_transaction_flags,
                suspicious_merchant_flags,
                foreign_transaction_flags,
            )

            advanced_risk_scores = self._compute_advanced_risk_scores(
                df_sorted, behavior_deviation_scores, amount_percentile_ranks
            )

            # Create feature columns (restore original order)
            result_features = pd.DataFrame(index=result.index)

            # Map features back to original order
            sort_mapping = pd.Series(range(len(result)), index=df_sorted.index)

            result_features["is_high_value_transaction"] = high_value_flags.iloc[
                sort_mapping.values
            ].values
            result_features["amount_percentile_rank"] = amount_percentile_ranks.iloc[
                sort_mapping.values
            ].values
            result_features["is_rapid_transaction"] = rapid_transaction_flags.iloc[
                sort_mapping.values
            ].values
            result_features["is_off_hours_transaction"] = off_hours_flags.iloc[
                sort_mapping.values
            ].values
            result_features["is_suspicious_merchant"] = suspicious_merchant_flags.iloc[
                sort_mapping.values
            ].values
            result_features["is_suspicious_device"] = suspicious_device_flags.iloc[
                sort_mapping.values
            ].values
            result_features["is_foreign_transaction"] = foreign_transaction_flags.iloc[
                sort_mapping.values
            ].values
            result_features["behavior_deviation_score"] = behavior_deviation_scores.iloc[
                sort_mapping.values
            ].values
            result_features["basic_risk_score"] = basic_risk_scores.iloc[sort_mapping.values].values
            result_features["advanced_risk_score"] = advanced_risk_scores.iloc[
                sort_mapping.values
            ].values

            # Add amount threshold features
            for threshold_name, threshold_value in self.amount_thresholds_.items():
                result_features[f"amount_above_{threshold_name}"] = (
                    result[self.amount_column] > threshold_value
                ).astype(int)

            # Combine risk indicators
            result_features["total_risk_flags"] = (
                result_features["is_high_value_transaction"]
                + result_features["is_rapid_transaction"]
                + result_features["is_suspicious_merchant"]
                + result_features["is_suspicious_device"]
                + result_features["is_foreign_transaction"]
            )

            # Risk categories
            result_features["risk_category"] = pd.cut(
                result_features["advanced_risk_score"],
                bins=[0, 0.3, 0.6, 1.0],
                labels=["LOW", "MEDIUM", "HIGH"],
                include_lowest=True,
            ).astype(str)

            # Add all features to result
            for col in result_features.columns:
                result[col] = result_features[col]

            # Update feature names
            self._feature_names_out = list(result_features.columns)

            self.logger.info(f"Generated {len(self._feature_names_out)} risk features")

        # Update metadata
        self._update_metadata(X, result)

        return result

    def _identify_suspicious_entities(self, X: pd.DataFrame, y: pd.Series):
        """Identify suspicious merchants and devices using fraud labels."""
        df_with_labels = X.copy()
        df_with_labels["fraud_flag"] = y

        # Suspicious merchants (high fraud rate)
        merchant_fraud_rates = df_with_labels.groupby(self.merchant_id_column)["fraud_flag"].agg(
            ["mean", "count"]
        )
        merchant_fraud_rates = merchant_fraud_rates[
            merchant_fraud_rates["count"] >= 5
        ]  # Minimum transactions
        suspicious_merchants = merchant_fraud_rates[
            merchant_fraud_rates["mean"] > self.suspicious_merchant_threshold
        ]
        self.suspicious_merchants_ = set(suspicious_merchants.index)

        # Suspicious devices (high fraud rate)
        device_fraud_rates = df_with_labels.groupby(self.device_id_column)["fraud_flag"].agg(
            ["mean", "count"]
        )
        device_fraud_rates = device_fraud_rates[
            device_fraud_rates["count"] >= 3
        ]  # Minimum transactions
        suspicious_devices = device_fraud_rates[
            device_fraud_rates["mean"] > self.suspicious_merchant_threshold
        ]
        self.suspicious_devices_ = set(suspicious_devices.index)

    def _identify_suspicious_entities_unsupervised(self, X: pd.DataFrame):
        """Identify suspicious entities using unsupervised methods."""
        # Merchants with unusual patterns (placeholder logic)
        merchant_stats = (
            X.groupby(self.merchant_id_column)
            .agg({self.amount_column: ["mean", "std", "count"], self.customer_id_column: "nunique"})
            .reset_index()
        )

        merchant_stats.columns = [
            "merchant_id",
            "avg_amount",
            "std_amount",
            "transaction_count",
            "unique_customers",
        ]

        # Flag merchants with very high or very low average amounts
        amount_q99 = merchant_stats["avg_amount"].quantile(0.99)
        amount_q01 = merchant_stats["avg_amount"].quantile(0.01)

        suspicious_merchants = merchant_stats[
            (merchant_stats["avg_amount"] > amount_q99)
            | (merchant_stats["avg_amount"] < amount_q01)
            | (merchant_stats["unique_customers"] == 1)  # Single customer
        ]

        self.suspicious_merchants_ = set(suspicious_merchants["merchant_id"])

        # Similar logic for devices (placeholder)
        device_stats = (
            X.groupby(self.device_id_column)
            .agg({self.customer_id_column: "nunique", self.amount_column: "count"})
            .reset_index()
        )

        device_stats.columns = ["device_id", "unique_customers", "transaction_count"]

        # Flag devices used by many customers
        customer_threshold = device_stats["unique_customers"].quantile(0.95)
        suspicious_devices = device_stats[device_stats["unique_customers"] > customer_threshold]

        self.suspicious_devices_ = set(suspicious_devices["device_id"])

    def _build_customer_profiles(self, X: pd.DataFrame):
        """Build baseline customer profiles for behavior deviation detection."""
        customer_groups = X.groupby(self.customer_id_column)

        for customer_id, group in customer_groups:
            if len(group) >= 2:  # Need at least 2 transactions for profile
                profile = {
                    "avg_amount": group[self.amount_column].mean(),
                    "std_amount": group[self.amount_column].std(),
                    "common_merchants": set(
                        group[self.merchant_id_column].value_counts().head(3).index
                    ),
                    "common_countries": set(
                        group[self.country_column].value_counts().head(2).index
                    ),
                    "transaction_count": len(group),
                    "avg_hour": pd.to_datetime(group[self.timestamp_column]).dt.hour.mean(),
                }
                self.customer_profiles_[customer_id] = profile

    def _compute_rapid_transaction_flags(self, df_sorted: pd.DataFrame) -> pd.Series:
        """Compute flags for rapid consecutive transactions."""
        rapid_flags = pd.Series(0, index=df_sorted.index, dtype=int)

        for customer_id, group in df_sorted.groupby(self.customer_id_column):
            if len(group) < 2:
                continue

            timestamps = pd.to_datetime(group[self.timestamp_column])
            time_diffs = timestamps.diff()

            # Flag transactions within rapid_transaction_minutes
            rapid_mask = time_diffs <= timedelta(minutes=self.rapid_transaction_minutes)
            rapid_flags.loc[group.index[rapid_mask]] = 1

        return rapid_flags

    def _compute_off_hours_flags(self, df_sorted: pd.DataFrame) -> pd.Series:
        """Compute flags for transactions during off-hours."""
        timestamps = pd.to_datetime(df_sorted[self.timestamp_column])
        hours = timestamps.dt.hour

        # Define off-hours as midnight to 6 AM and 10 PM to midnight
        off_hours_flags = (((hours >= 0) & (hours < 6)) | (hours >= 22)).astype(int)

        return off_hours_flags

    def _compute_behavior_deviation_scores(self, df_sorted: pd.DataFrame) -> pd.Series:
        """Compute behavior deviation scores based on customer profiles."""
        deviation_scores = pd.Series(0.0, index=df_sorted.index)

        for idx, row in df_sorted.iterrows():
            customer_id = row[self.customer_id_column]

            if customer_id in self.customer_profiles_:
                profile = self.customer_profiles_[customer_id]
                score = 0.0

                # Amount deviation
                amount = row[self.amount_column]
                avg_amount = profile["avg_amount"]
                std_amount = profile["std_amount"]

                if std_amount > 0:
                    z_score = abs(amount - avg_amount) / std_amount
                    score += min(z_score / 3.0, 1.0) * 0.4  # Weight: 40%

                # Merchant deviation
                merchant = row[self.merchant_id_column]
                if merchant not in profile["common_merchants"]:
                    score += 0.3  # Weight: 30%

                # Country deviation
                country = row[self.country_column]
                if country not in profile["common_countries"]:
                    score += 0.2  # Weight: 20%

                # Time deviation
                current_hour = pd.to_datetime(row[self.timestamp_column]).hour
                avg_hour = profile["avg_hour"]
                hour_diff = min(abs(current_hour - avg_hour), 24 - abs(current_hour - avg_hour))
                score += (hour_diff / 12.0) * 0.1  # Weight: 10%

                deviation_scores.loc[idx] = min(score, 1.0)
            else:
                # New customer - moderate risk
                deviation_scores.loc[idx] = 0.5

        return deviation_scores

    def _compute_basic_risk_scores(
        self,
        df_sorted: pd.DataFrame,
        high_value_flags: pd.Series,
        rapid_flags: pd.Series,
        merchant_flags: pd.Series,
        foreign_flags: pd.Series,
    ) -> pd.Series:
        """Compute basic risk scores based on simple flags."""
        # Weighted combination of basic risk factors
        risk_scores = (
            high_value_flags * 0.3
            + rapid_flags * 0.25
            + merchant_flags * 0.25
            + foreign_flags * 0.2
        )

        return risk_scores

    def _compute_advanced_risk_scores(
        self, df_sorted: pd.DataFrame, behavior_scores: pd.Series, percentile_ranks: pd.Series
    ) -> pd.Series:
        """Compute advanced risk scores incorporating multiple factors."""
        # Combine behavior deviation with other factors
        advanced_scores = (
            behavior_scores * 0.4
            + percentile_ranks * 0.3
            + (percentile_ranks > 0.95).astype(float) * 0.3
        )

        # Apply non-linear transformation to emphasize high-risk transactions
        advanced_scores = np.power(advanced_scores, 0.7)

        return advanced_scores

    def _custom_validation(self, X: pd.DataFrame) -> ValidationResult:
        """Custom validation for risk transformer."""
        errors = []
        warnings = []

        # Check required columns
        required_cols = [
            self.amount_column,
            self.timestamp_column,
            self.customer_id_column,
            self.merchant_id_column,
            self.device_id_column,
            self.country_column,
        ]

        missing_cols = []
        for col in required_cols:
            if col not in X.columns:
                missing_cols.append(col)
            elif X[col].isnull().all():
                warnings.append(f"Column '{col}' contains only null values")

        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")

        # Check amount column
        if self.amount_column in X.columns:
            amounts = X[self.amount_column]
            if (amounts < 0).sum() > 0:
                warnings.append(f"Found {(amounts < 0).sum()} negative amounts")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
