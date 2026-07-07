"""
Velocity Feature Transformers

Transformers for creating velocity-based features that capture transaction
patterns over time windows, including frequency, amounts, and rolling statistics.
"""

import numpy as np
import pandas as pd

from ml.features.transformers.base import BaseFeatureTransformer, ValidationResult


class VelocityTransformer(BaseFeatureTransformer):
    """
    Transformer for velocity features based on time windows.

    Creates:
    - Transaction counts in 1 hour, 24 hours, 7 days
    - Average, maximum, minimum amounts in time windows
    - Rolling statistics
    """

    def __init__(
        self,
        timestamp_column: str = "timestamp",
        amount_column: str = "amount",
        customer_id_column: str = "customer_id",
        time_windows: list[str] = None,
        rolling_statistics: list[str] = None,
        **kwargs,
    ):

        if time_windows is None:
            time_windows = ["1H", "24H", "7D"]  # 1 hour, 24 hours, 7 days

        if rolling_statistics is None:
            rolling_statistics = ["mean", "std", "min", "max", "median"]

        super().__init__(
            name="velocity_transformer",
            version="1.0.0",
            description="Velocity features based on transaction patterns over time windows",
            dependencies=[timestamp_column, amount_column, customer_id_column],
            timestamp_column=timestamp_column,
            amount_column=amount_column,
            customer_id_column=customer_id_column,
            time_windows=time_windows,
            rolling_statistics=rolling_statistics,
            **kwargs,
        )
        self.timestamp_column = timestamp_column
        self.amount_column = amount_column
        self.customer_id_column = customer_id_column
        self.time_windows = time_windows
        self.rolling_statistics = rolling_statistics

        # Convert time windows to timedeltas
        self.window_deltas = {}
        for window in time_windows:
            self.window_deltas[window] = pd.Timedelta(window)

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "VelocityTransformer":
        """Fit the transformer (compute reference statistics)."""
        self._validate_input(X)

        with self.logger.stage_context("fitting_velocity_transformer"):
            # Sort by timestamp for proper velocity calculation
            df_sorted = X.sort_values([self.customer_id_column, self.timestamp_column])

            # Compute baseline statistics
            self.fit_statistics = {}

            for window in self.time_windows:
                # Compute sample velocity features to get distribution
                sample_velocity = self._compute_velocity_features_for_window(
                    df_sorted.head(min(10000, len(df_sorted))), window
                )

                self.fit_statistics[f"{window}_stats"] = {
                    "count_mean": sample_velocity[f"txn_count_{window}"].mean(),
                    "count_std": sample_velocity[f"txn_count_{window}"].std(),
                    "amount_mean": sample_velocity[f"amount_mean_{window}"].mean(),
                    "amount_std": sample_velocity[f"amount_mean_{window}"].std(),
                }

            # Update state
            self.is_fitted = True

            self.logger.info(f"Velocity transformer fitted for windows: {self.time_windows}")

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform data to create velocity features."""
        self._check_fitted()
        self._validate_input(X)

        result = X.copy()

        with self.logger.stage_context("transforming_velocity_features"):
            # Sort by customer and timestamp
            df_sorted = result.sort_values([self.customer_id_column, self.timestamp_column])

            # Generate velocity features for each time window
            all_features = []

            for window in self.time_windows:
                window_features = self._compute_velocity_features_for_window(df_sorted, window)
                all_features.append(window_features)

            # Combine all velocity features
            if all_features:
                velocity_df = pd.concat(all_features, axis=1)
                # Remove duplicate columns (keep first occurrence)
                velocity_df = velocity_df.loc[:, ~velocity_df.columns.duplicated()]

                # Merge with original data (maintaining original order)
                result = result.merge(velocity_df, left_index=True, right_index=True, how="left")

            # Fill NaN values with 0 (for customers with no prior history)
            velocity_columns = [
                col for col in result.columns if any(window in col for window in self.time_windows)
            ]
            result[velocity_columns] = result[velocity_columns].fillna(0)

            # Update feature names
            self._feature_names_out = velocity_columns

            self.logger.info(f"Generated {len(self._feature_names_out)} velocity features")

        # Update metadata
        self._update_metadata(X, result)

        return result

    def _compute_velocity_features_for_window(self, df: pd.DataFrame, window: str) -> pd.DataFrame:
        """
        Compute velocity features for a specific time window.

        Args:
            df: Sorted DataFrame by customer_id and timestamp
            window: Time window string (e.g., "1H", "24H", "7D")

        Returns:
            DataFrame with velocity features
        """
        window_delta = self.window_deltas[window]
        features = pd.DataFrame(index=df.index)

        # Convert timestamp to datetime if needed
        timestamps = pd.to_datetime(df[self.timestamp_column])
        amounts = df[self.amount_column]
        customers = df[self.customer_id_column]

        # Initialize feature arrays
        txn_counts = np.zeros(len(df))
        amount_means = np.zeros(len(df))
        amount_maxs = np.zeros(len(df))
        amount_mins = np.zeros(len(df))
        amount_stds = np.zeros(len(df))
        amount_sums = np.zeros(len(df))

        # Group by customer for efficient computation
        for customer_id, group in df.groupby(self.customer_id_column):
            group_timestamps = pd.to_datetime(group[self.timestamp_column])
            group_amounts = group[self.amount_column].values
            group_indices = group.index

            # For each transaction, look back in the time window
            for i, (idx, current_time) in enumerate(zip(group_indices, group_timestamps)):
                # Find transactions within the time window (excluding current transaction)
                window_start = current_time - window_delta

                # Transactions in the window (before current transaction)
                mask = (group_timestamps < current_time) & (group_timestamps >= window_start)
                window_transactions = group_amounts[:i][mask[:i]]

                if len(window_transactions) > 0:
                    txn_counts[df.index.get_loc(idx)] = len(window_transactions)
                    amount_means[df.index.get_loc(idx)] = np.mean(window_transactions)
                    amount_maxs[df.index.get_loc(idx)] = np.max(window_transactions)
                    amount_mins[df.index.get_loc(idx)] = np.min(window_transactions)
                    amount_stds[df.index.get_loc(idx)] = (
                        np.std(window_transactions) if len(window_transactions) > 1 else 0
                    )
                    amount_sums[df.index.get_loc(idx)] = np.sum(window_transactions)

        # Create feature columns
        features[f"txn_count_{window}"] = txn_counts
        features[f"amount_mean_{window}"] = amount_means
        features[f"amount_max_{window}"] = amount_maxs
        features[f"amount_min_{window}"] = amount_mins
        features[f"amount_std_{window}"] = amount_stds
        features[f"amount_sum_{window}"] = amount_sums

        # Additional derived features
        features[f"amount_range_{window}"] = amount_maxs - amount_mins
        features[f"avg_amount_ratio_{window}"] = np.where(
            amount_means > 0, amounts / amount_means, 0
        )

        return features

    def _custom_validation(self, X: pd.DataFrame) -> ValidationResult:
        """Custom validation for velocity transformer."""
        errors = []
        warnings = []

        # Check timestamp column
        try:
            timestamps = pd.to_datetime(X[self.timestamp_column])
        except Exception as e:
            errors.append(f"Cannot convert {self.timestamp_column} to datetime: {e}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Check if data is sorted by customer and timestamp
        df_check = X[[self.customer_id_column, self.timestamp_column]].copy()
        df_check["timestamp_dt"] = pd.to_datetime(df_check[self.timestamp_column])

        # Check for duplicate timestamps within customers
        duplicates = (
            df_check.groupby(self.customer_id_column)["timestamp_dt"]
            .apply(lambda x: x.duplicated().sum())
            .sum()
        )

        if duplicates > 0:
            warnings.append(f"Found {duplicates} duplicate timestamps within customers")

        # Check customer ID distribution
        customer_counts = X[self.customer_id_column].value_counts()
        single_transaction_customers = (customer_counts == 1).sum()

        if single_transaction_customers > 0:
            warnings.append(f"{single_transaction_customers} customers have only one transaction")

        # Check amount column
        amounts = X[self.amount_column]
        if amounts.isnull().sum() > 0:
            warnings.append(f"Found {amounts.isnull().sum()} null amounts")

        if (amounts < 0).sum() > 0:
            warnings.append(f"Found {(amounts < 0).sum()} negative amounts")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class RollingStatisticsTransformer(BaseFeatureTransformer):
    """
    Transformer for rolling window statistics.

    Creates rolling statistics over specified windows for amount features.
    """

    def __init__(
        self,
        timestamp_column: str = "timestamp",
        amount_column: str = "amount",
        customer_id_column: str = "customer_id",
        windows: list[int] = None,
        statistics: list[str] = None,
        **kwargs,
    ):

        if windows is None:
            windows = [3, 5, 10, 20]  # Number of transactions

        if statistics is None:
            statistics = ["mean", "std", "min", "max", "median"]

        super().__init__(
            name="rolling_statistics_transformer",
            version="1.0.0",
            description="Rolling window statistics for transaction amounts",
            dependencies=[timestamp_column, amount_column, customer_id_column],
            timestamp_column=timestamp_column,
            amount_column=amount_column,
            customer_id_column=customer_id_column,
            windows=windows,
            statistics=statistics,
            **kwargs,
        )
        self.timestamp_column = timestamp_column
        self.amount_column = amount_column
        self.customer_id_column = customer_id_column
        self.windows = windows
        self.statistics = statistics

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "RollingStatisticsTransformer":
        """Fit the transformer (no parameters to learn)."""
        self._validate_input(X)

        with self.logger.stage_context("fitting_rolling_statistics_transformer"):
            # Compute baseline statistics
            amounts = X[self.amount_column]

            self.fit_statistics = {
                "amount_mean": amounts.mean(),
                "amount_std": amounts.std(),
                "amount_min": amounts.min(),
                "amount_max": amounts.max(),
                "windows": self.windows,
                "statistics": self.statistics,
            }

            # Update state
            self.is_fitted = True

            self.logger.info(f"Rolling statistics transformer fitted for windows: {self.windows}")

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform data to create rolling statistics features."""
        self._check_fitted()
        self._validate_input(X)

        result = X.copy()

        with self.logger.stage_context("transforming_rolling_statistics"):
            # Sort by customer and timestamp
            df_sorted = result.sort_values([self.customer_id_column, self.timestamp_column])

            # Compute rolling statistics for each customer
            rolling_features = []

            for customer_id, group in df_sorted.groupby(self.customer_id_column):
                customer_features = self._compute_customer_rolling_stats(group)
                rolling_features.append(customer_features)

            # Combine all rolling features
            if rolling_features:
                rolling_df = pd.concat(rolling_features, ignore_index=False)
                rolling_df = rolling_df.sort_index()

                # Merge with original data
                feature_columns = [col for col in rolling_df.columns if col.startswith("rolling_")]
                result = result.join(rolling_df[feature_columns], how="left")

            # Fill NaN values with appropriate defaults
            feature_columns = [col for col in result.columns if col.startswith("rolling_")]
            for col in feature_columns:
                if "count" in col:
                    result[col] = result[col].fillna(0)
                else:
                    result[col] = result[col].fillna(
                        result[self.amount_column].iloc[0] if len(result) > 0 else 0
                    )

            # Update feature names
            self._feature_names_out = feature_columns

            self.logger.info(
                f"Generated {len(self._feature_names_out)} rolling statistics features"
            )

        # Update metadata
        self._update_metadata(X, result)

        return result

    def _compute_customer_rolling_stats(self, group: pd.DataFrame) -> pd.DataFrame:
        """Compute rolling statistics for a single customer."""
        features = pd.DataFrame(index=group.index)
        amounts = group[self.amount_column]

        for window in self.windows:
            for stat in self.statistics:
                col_name = f"rolling_{stat}_{window}"

                if stat == "mean":
                    features[col_name] = amounts.rolling(window=window, min_periods=1).mean()
                elif stat == "std":
                    features[col_name] = (
                        amounts.rolling(window=window, min_periods=1).std().fillna(0)
                    )
                elif stat == "min":
                    features[col_name] = amounts.rolling(window=window, min_periods=1).min()
                elif stat == "max":
                    features[col_name] = amounts.rolling(window=window, min_periods=1).max()
                elif stat == "median":
                    features[col_name] = amounts.rolling(window=window, min_periods=1).median()
                elif stat == "sum":
                    features[col_name] = amounts.rolling(window=window, min_periods=1).sum()
                elif stat == "count":
                    features[col_name] = amounts.rolling(window=window, min_periods=1).count()

        # Additional derived features
        for window in self.windows:
            if "mean" in self.statistics and "std" in self.statistics:
                # Z-score of current amount vs rolling mean/std
                mean_col = f"rolling_mean_{window}"
                std_col = f"rolling_std_{window}"
                features[f"rolling_zscore_{window}"] = np.where(
                    features[std_col] > 0, (amounts - features[mean_col]) / features[std_col], 0
                )

            if "min" in self.statistics and "max" in self.statistics:
                # Position within rolling range
                min_col = f"rolling_min_{window}"
                max_col = f"rolling_max_{window}"
                features[f"rolling_position_{window}"] = np.where(
                    (features[max_col] - features[min_col]) > 0,
                    (amounts - features[min_col]) / (features[max_col] - features[min_col]),
                    0.5,
                )

        return features
