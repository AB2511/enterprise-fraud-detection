"""
Customer Feature Transformers

Transformers for creating customer-specific features including demographics,
behavior patterns, history, and risk metrics.
"""

import numpy as np
import pandas as pd

from ml.features.transformers.base import BaseFeatureTransformer, ValidationResult


class CustomerTransformer(BaseFeatureTransformer):
    """
    Transformer for customer demographic and account features.

    Creates:
    - Customer age (if birthdate available)
    - Account age
    - Historical fraud metrics
    - Transaction frequency patterns
    """

    def __init__(
        self,
        customer_id_column: str = "customer_id",
        timestamp_column: str = "timestamp",
        amount_column: str = "amount",
        fraud_column: str = "is_fraud",
        birthdate_column: str = None,
        account_created_column: str = None,
        **kwargs,
    ):

        dependencies = [customer_id_column, timestamp_column, amount_column, fraud_column]
        if birthdate_column:
            dependencies.append(birthdate_column)
        if account_created_column:
            dependencies.append(account_created_column)

        super().__init__(
            name="customer_transformer",
            version="1.0.0",
            description="Customer demographic and behavioral features",
            dependencies=dependencies,
            customer_id_column=customer_id_column,
            timestamp_column=timestamp_column,
            amount_column=amount_column,
            fraud_column=fraud_column,
            birthdate_column=birthdate_column,
            account_created_column=account_created_column,
            **kwargs,
        )
        self.customer_id_column = customer_id_column
        self.timestamp_column = timestamp_column
        self.amount_column = amount_column
        self.fraud_column = fraud_column
        self.birthdate_column = birthdate_column
        self.account_created_column = account_created_column

        # Fit parameters
        self.customer_stats_ = {}
        self.reference_date_ = None

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "CustomerTransformer":
        """Fit the transformer by computing customer statistics."""
        self._validate_input(X)

        with self.logger.stage_context("fitting_customer_transformer"):
            # Use the latest timestamp as reference date
            timestamps = pd.to_datetime(X[self.timestamp_column])
            self.reference_date_ = timestamps.max()

            # Compute customer-level statistics
            customer_groups = X.groupby(self.customer_id_column)

            self.customer_stats_ = {}

            for customer_id, group in customer_groups:
                stats = self._compute_customer_stats(group, self.reference_date_)
                self.customer_stats_[customer_id] = stats

            # Compute global statistics
            self.fit_statistics = {
                "n_customers": len(self.customer_stats_),
                "reference_date": self.reference_date_.isoformat(),
                "avg_transactions_per_customer": np.mean(
                    [stats["transaction_count"] for stats in self.customer_stats_.values()]
                ),
                "avg_customer_lifetime_value": np.mean(
                    [stats["lifetime_value"] for stats in self.customer_stats_.values()]
                ),
                "fraud_rate_by_customer": np.mean(
                    [stats["fraud_rate"] for stats in self.customer_stats_.values()]
                ),
            }

            # Update state
            self.is_fitted = True

            self.logger.info(
                f"Customer transformer fitted for {len(self.customer_stats_)} customers"
            )

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform data to create customer features."""
        self._check_fitted()
        self._validate_input(X)

        result = X.copy()

        with self.logger.stage_context("transforming_customer_features"):
            # Current timestamp for age calculations
            current_timestamps = pd.to_datetime(X[self.timestamp_column])

            # Initialize feature arrays
            n_rows = len(X)
            customer_ages = np.full(n_rows, np.nan)
            account_ages = np.full(n_rows, np.nan)
            historical_fraud_counts = np.zeros(n_rows)
            historical_fraud_rates = np.zeros(n_rows)
            transaction_frequencies = np.zeros(n_rows)
            customer_lifetime_values = np.zeros(n_rows)
            days_since_last_transaction = np.zeros(n_rows)

            # Process each customer
            for idx, row in X.iterrows():
                customer_id = row[self.customer_id_column]
                current_time = pd.to_datetime(row[self.timestamp_column])

                # Get customer stats (use default if not found in fit data)
                if customer_id in self.customer_stats_:
                    customer_stats = self.customer_stats_[customer_id]
                else:
                    # New customer - compute stats from available data up to current transaction
                    customer_history = X[
                        (X[self.customer_id_column] == customer_id)
                        & (pd.to_datetime(X[self.timestamp_column]) < current_time)
                    ]

                    if len(customer_history) > 0:
                        customer_stats = self._compute_customer_stats(
                            customer_history, current_time
                        )
                    else:
                        customer_stats = self._get_default_customer_stats()

                # Customer age (if birthdate available)
                if self.birthdate_column and self.birthdate_column in X.columns:
                    birthdate = pd.to_datetime(row[self.birthdate_column], errors="coerce")
                    if pd.notna(birthdate):
                        customer_ages[X.index.get_loc(idx)] = (
                            current_time - birthdate
                        ).days / 365.25

                # Account age
                if self.account_created_column and self.account_created_column in X.columns:
                    account_created = pd.to_datetime(
                        row[self.account_created_column], errors="coerce"
                    )
                    if pd.notna(account_created):
                        account_ages[X.index.get_loc(idx)] = (current_time - account_created).days

                # Historical metrics (excluding current transaction)
                row_idx = X.index.get_loc(idx)
                historical_fraud_counts[row_idx] = customer_stats["fraud_count"]
                historical_fraud_rates[row_idx] = customer_stats["fraud_rate"]
                transaction_frequencies[row_idx] = customer_stats["transaction_frequency"]
                customer_lifetime_values[row_idx] = customer_stats["lifetime_value"]
                days_since_last_transaction[row_idx] = customer_stats["days_since_last_transaction"]

            # Create feature columns
            if self.birthdate_column and self.birthdate_column in X.columns:
                result["customer_age_years"] = customer_ages

            if self.account_created_column and self.account_created_column in X.columns:
                result["account_age_days"] = account_ages

            result["historical_fraud_count"] = historical_fraud_counts
            result["historical_fraud_rate"] = historical_fraud_rates
            result["transaction_frequency_per_day"] = transaction_frequencies
            result["customer_lifetime_value"] = customer_lifetime_values
            result["days_since_last_transaction"] = days_since_last_transaction

            # Derived features
            result["is_new_customer"] = (result["historical_fraud_count"] == 0).astype(int)
            result["is_high_frequency_customer"] = (
                result["transaction_frequency_per_day"]
                > result["transaction_frequency_per_day"].quantile(0.75)
            ).astype(int)
            result["is_high_value_customer"] = (
                result["customer_lifetime_value"] > result["customer_lifetime_value"].quantile(0.9)
            ).astype(int)

            # Update feature names
            feature_columns = [col for col in result.columns if col not in X.columns]
            self._feature_names_out = feature_columns

            self.logger.info(f"Generated {len(self._feature_names_out)} customer features")

        # Update metadata
        self._update_metadata(X, result)

        return result

    def _compute_customer_stats(
        self, customer_data: pd.DataFrame, reference_date: pd.Timestamp
    ) -> dict[str, float]:
        """Compute statistics for a single customer."""
        if len(customer_data) == 0:
            return self._get_default_customer_stats()

        timestamps = pd.to_datetime(customer_data[self.timestamp_column])
        amounts = customer_data[self.amount_column]
        fraud_flags = (
            customer_data[self.fraud_column]
            if self.fraud_column in customer_data.columns
            else pd.Series([0] * len(customer_data))
        )

        # Basic counts and sums
        transaction_count = len(customer_data)
        fraud_count = fraud_flags.sum()
        fraud_rate = fraud_count / transaction_count if transaction_count > 0 else 0.0
        lifetime_value = amounts.sum()

        # Time-based metrics
        first_transaction = timestamps.min()
        last_transaction = timestamps.max()
        customer_lifespan_days = (last_transaction - first_transaction).days + 1

        transaction_frequency = (
            transaction_count / customer_lifespan_days if customer_lifespan_days > 0 else 0.0
        )
        days_since_last_transaction = (reference_date - last_transaction).days

        return {
            "transaction_count": transaction_count,
            "fraud_count": fraud_count,
            "fraud_rate": fraud_rate,
            "lifetime_value": lifetime_value,
            "transaction_frequency": transaction_frequency,
            "days_since_last_transaction": max(0, days_since_last_transaction),
            "customer_lifespan_days": customer_lifespan_days,
        }

    def _get_default_customer_stats(self) -> dict[str, float]:
        """Get default statistics for new customers."""
        return {
            "transaction_count": 0,
            "fraud_count": 0,
            "fraud_rate": 0.0,
            "lifetime_value": 0.0,
            "transaction_frequency": 0.0,
            "days_since_last_transaction": 0.0,
            "customer_lifespan_days": 0,
        }

    def _custom_validation(self, X: pd.DataFrame) -> ValidationResult:
        """Custom validation for customer transformer."""
        errors = []
        warnings = []

        # Check timestamp column
        try:
            timestamps = pd.to_datetime(X[self.timestamp_column])
        except Exception as e:
            errors.append(f"Cannot convert {self.timestamp_column} to datetime: {e}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Check for missing customer IDs
        missing_customers = X[self.customer_id_column].isnull().sum()
        if missing_customers > 0:
            errors.append(f"Found {missing_customers} rows with missing customer IDs")

        # Check birthdate column if provided
        if self.birthdate_column and self.birthdate_column in X.columns:
            birthdates = pd.to_datetime(X[self.birthdate_column], errors="coerce")
            invalid_birthdates = birthdates.isnull().sum()
            if invalid_birthdates > 0:
                warnings.append(f"Found {invalid_birthdates} invalid birthdates")

        # Check account created column if provided
        if self.account_created_column and self.account_created_column in X.columns:
            account_dates = pd.to_datetime(X[self.account_created_column], errors="coerce")
            invalid_account_dates = account_dates.isnull().sum()
            if invalid_account_dates > 0:
                warnings.append(f"Found {invalid_account_dates} invalid account creation dates")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class MerchantTransformer(BaseFeatureTransformer):
    """
    Transformer for merchant-specific features.

    Creates:
    - Merchant fraud rate
    - Merchant transaction volume
    - Merchant average amount
    - Merchant category statistics
    """

    def __init__(
        self,
        merchant_id_column: str = "merchant_id",
        timestamp_column: str = "timestamp",
        amount_column: str = "amount",
        fraud_column: str = "is_fraud",
        merchant_category_column: str = None,
        **kwargs,
    ):

        dependencies = [merchant_id_column, timestamp_column, amount_column, fraud_column]
        if merchant_category_column:
            dependencies.append(merchant_category_column)

        super().__init__(
            name="merchant_transformer",
            version="1.0.0",
            description="Merchant-specific risk and volume features",
            dependencies=dependencies,
            merchant_id_column=merchant_id_column,
            timestamp_column=timestamp_column,
            amount_column=amount_column,
            fraud_column=fraud_column,
            merchant_category_column=merchant_category_column,
            **kwargs,
        )
        self.merchant_id_column = merchant_id_column
        self.timestamp_column = timestamp_column
        self.amount_column = amount_column
        self.fraud_column = fraud_column
        self.merchant_category_column = merchant_category_column

        # Fit parameters
        self.merchant_stats_ = {}
        self.category_stats_ = {}

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "MerchantTransformer":
        """Fit the transformer by computing merchant statistics."""
        self._validate_input(X)

        with self.logger.stage_context("fitting_merchant_transformer"):
            # Compute merchant-level statistics
            if pd.notna(X[self.merchant_id_column]).any():
                merchant_groups = X.groupby(self.merchant_id_column)

                for merchant_id, group in merchant_groups:
                    if pd.notna(merchant_id):  # Skip NaN merchant IDs
                        stats = self._compute_merchant_stats(group)
                        self.merchant_stats_[merchant_id] = stats

            # Compute category-level statistics if available
            if (
                self.merchant_category_column
                and self.merchant_category_column in X.columns
                and pd.notna(X[self.merchant_category_column]).any()
            ):

                category_groups = X.groupby(self.merchant_category_column)

                for category, group in category_groups:
                    if pd.notna(category):  # Skip NaN categories
                        stats = self._compute_merchant_stats(group)
                        self.category_stats_[category] = stats

            # Compute global statistics
            self.fit_statistics = {
                "n_merchants": len(self.merchant_stats_),
                "n_categories": len(self.category_stats_),
                "avg_fraud_rate": (
                    np.mean([stats["fraud_rate"] for stats in self.merchant_stats_.values()])
                    if self.merchant_stats_
                    else 0
                ),
                "avg_transaction_volume": (
                    np.mean([stats["transaction_count"] for stats in self.merchant_stats_.values()])
                    if self.merchant_stats_
                    else 0
                ),
            }

            # Update state
            self.is_fitted = True

            self.logger.info(
                f"Merchant transformer fitted for {len(self.merchant_stats_)} merchants"
            )

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform data to create merchant features."""
        self._check_fitted()
        self._validate_input(X)

        result = X.copy()

        with self.logger.stage_context("transforming_merchant_features"):
            # Initialize feature arrays
            n_rows = len(X)
            merchant_fraud_rates = np.zeros(n_rows)
            merchant_volumes = np.zeros(n_rows)
            merchant_avg_amounts = np.zeros(n_rows)
            merchant_total_amounts = np.zeros(n_rows)
            category_fraud_rates = np.zeros(n_rows)
            category_volumes = np.zeros(n_rows)

            # Process each row
            for idx, row in X.iterrows():
                merchant_id = row[self.merchant_id_column]
                current_time = pd.to_datetime(row[self.timestamp_column])
                row_idx = X.index.get_loc(idx)

                # Merchant features
                if pd.notna(merchant_id) and merchant_id in self.merchant_stats_:
                    merchant_stats = self.merchant_stats_[merchant_id]
                else:
                    # Compute stats from available data (excluding current transaction)
                    merchant_history = X[
                        (X[self.merchant_id_column] == merchant_id)
                        & (pd.to_datetime(X[self.timestamp_column]) < current_time)
                    ]

                    if len(merchant_history) > 0:
                        merchant_stats = self._compute_merchant_stats(merchant_history)
                    else:
                        merchant_stats = self._get_default_merchant_stats()

                merchant_fraud_rates[row_idx] = merchant_stats["fraud_rate"]
                merchant_volumes[row_idx] = merchant_stats["transaction_count"]
                merchant_avg_amounts[row_idx] = merchant_stats["avg_amount"]
                merchant_total_amounts[row_idx] = merchant_stats["total_amount"]

                # Category features (if available)
                if self.merchant_category_column and self.merchant_category_column in X.columns:

                    category = row[self.merchant_category_column]

                    if pd.notna(category) and category in self.category_stats_:
                        category_stats = self.category_stats_[category]
                        category_fraud_rates[row_idx] = category_stats["fraud_rate"]
                        category_volumes[row_idx] = category_stats["transaction_count"]

            # Create feature columns
            result["merchant_fraud_rate"] = merchant_fraud_rates
            result["merchant_volume"] = merchant_volumes
            result["merchant_avg_amount"] = merchant_avg_amounts
            result["merchant_total_amount"] = merchant_total_amounts

            if self.merchant_category_column and self.merchant_category_column in X.columns:
                result["category_fraud_rate"] = category_fraud_rates
                result["category_volume"] = category_volumes

            # Derived features
            result["is_new_merchant"] = (result["merchant_volume"] == 0).astype(int)
            result["is_high_risk_merchant"] = (
                result["merchant_fraud_rate"] > result["merchant_fraud_rate"].quantile(0.9)
            ).astype(int)
            result["is_high_volume_merchant"] = (
                result["merchant_volume"] > result["merchant_volume"].quantile(0.8)
            ).astype(int)

            # Amount deviation from merchant average
            result["amount_vs_merchant_avg"] = np.where(
                result["merchant_avg_amount"] > 0,
                result[self.amount_column] / result["merchant_avg_amount"],
                1.0,
            )

            # Update feature names
            feature_columns = [col for col in result.columns if col not in X.columns]
            self._feature_names_out = feature_columns

            self.logger.info(f"Generated {len(self._feature_names_out)} merchant features")

        # Update metadata
        self._update_metadata(X, result)

        return result

    def _compute_merchant_stats(self, merchant_data: pd.DataFrame) -> dict[str, float]:
        """Compute statistics for a single merchant."""
        if len(merchant_data) == 0:
            return self._get_default_merchant_stats()

        amounts = merchant_data[self.amount_column]
        fraud_flags = (
            merchant_data[self.fraud_column]
            if self.fraud_column in merchant_data.columns
            else pd.Series([0] * len(merchant_data))
        )

        transaction_count = len(merchant_data)
        fraud_count = fraud_flags.sum()
        fraud_rate = fraud_count / transaction_count if transaction_count > 0 else 0.0
        total_amount = amounts.sum()
        avg_amount = amounts.mean() if transaction_count > 0 else 0.0

        return {
            "transaction_count": transaction_count,
            "fraud_count": fraud_count,
            "fraud_rate": fraud_rate,
            "total_amount": total_amount,
            "avg_amount": avg_amount,
        }

    def _get_default_merchant_stats(self) -> dict[str, float]:
        """Get default statistics for new merchants."""
        return {
            "transaction_count": 0,
            "fraud_count": 0,
            "fraud_rate": 0.0,
            "total_amount": 0.0,
            "avg_amount": 0.0,
        }

    def _custom_validation(self, X: pd.DataFrame) -> ValidationResult:
        """Custom validation for merchant transformer."""
        errors = []
        warnings = []

        # Check for missing merchant IDs
        missing_merchants = X[self.merchant_id_column].isnull().sum()
        total_rows = len(X)

        if missing_merchants == total_rows:
            errors.append("All merchant IDs are missing")
        elif missing_merchants > 0:
            warnings.append(f"Found {missing_merchants} rows with missing merchant IDs")

        # Check merchant category column if provided
        if self.merchant_category_column and self.merchant_category_column in X.columns:
            missing_categories = X[self.merchant_category_column].isnull().sum()
            if missing_categories > 0:
                warnings.append(f"Found {missing_categories} rows with missing merchant categories")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
