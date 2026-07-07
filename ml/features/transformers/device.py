"""
Device and Geographic Feature Transformers

Transformers for creating device-based and location-based features
including device fingerprinting, geographic patterns, and risk indicators.
"""

from typing import Any

import numpy as np
import pandas as pd

from ml.features.transformers.base import BaseFeatureTransformer, ValidationResult


class DeviceTransformer(BaseFeatureTransformer):
    """
    Transformer for device-based features.

    Creates:
    - Device reuse patterns
    - Device diversity metrics
    - Browser/OS fingerprinting
    - Device risk indicators
    """

    def __init__(
        self,
        device_id_column: str = "device_id",
        customer_id_column: str = "customer_id",
        timestamp_column: str = "timestamp",
        browser_column: str = None,
        os_column: str = None,
        screen_resolution_column: str = None,
        **kwargs,
    ):

        dependencies = [device_id_column, customer_id_column, timestamp_column]
        for col in [browser_column, os_column, screen_resolution_column]:
            if col:
                dependencies.append(col)

        super().__init__(
            name="device_transformer",
            version="1.0.0",
            description="Device fingerprinting and reuse pattern features",
            dependencies=dependencies,
            device_id_column=device_id_column,
            customer_id_column=customer_id_column,
            timestamp_column=timestamp_column,
            browser_column=browser_column,
            os_column=os_column,
            screen_resolution_column=screen_resolution_column,
            **kwargs,
        )
        self.device_id_column = device_id_column
        self.customer_id_column = customer_id_column
        self.timestamp_column = timestamp_column
        self.browser_column = browser_column
        self.os_column = os_column
        self.screen_resolution_column = screen_resolution_column

        # Fit parameters
        self.device_stats_ = {}
        self.customer_device_stats_ = {}
        self.device_fingerprints_ = {}

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "DeviceTransformer":
        """Fit the transformer by computing device usage patterns."""
        self._validate_input(X)

        with self.logger.stage_context("fitting_device_transformer"):
            # Compute device-level statistics
            if pd.notna(X[self.device_id_column]).any():
                device_groups = X.groupby(self.device_id_column)

                for device_id, group in device_groups:
                    if pd.notna(device_id):
                        stats = self._compute_device_stats(group)
                        self.device_stats_[device_id] = stats

            # Compute customer-device relationship statistics
            if (
                pd.notna(X[self.customer_id_column]).any()
                and pd.notna(X[self.device_id_column]).any()
            ):

                customer_groups = X.groupby(self.customer_id_column)

                for customer_id, group in customer_groups:
                    if pd.notna(customer_id):
                        stats = self._compute_customer_device_stats(group)
                        self.customer_device_stats_[customer_id] = stats

            # Create device fingerprints
            self._create_device_fingerprints(X)

            # Compute global statistics
            self.fit_statistics = {
                "n_devices": len(self.device_stats_),
                "n_customers": len(self.customer_device_stats_),
                "avg_customers_per_device": (
                    np.mean([stats["unique_customers"] for stats in self.device_stats_.values()])
                    if self.device_stats_
                    else 0
                ),
                "avg_devices_per_customer": (
                    np.mean(
                        [stats["unique_devices"] for stats in self.customer_device_stats_.values()]
                    )
                    if self.customer_device_stats_
                    else 0
                ),
            }

            # Update state
            self.is_fitted = True

            self.logger.info(f"Device transformer fitted for {len(self.device_stats_)} devices")

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform data to create device features."""
        self._check_fitted()
        self._validate_input(X)

        result = X.copy()

        with self.logger.stage_context("transforming_device_features"):
            # Initialize feature arrays
            n_rows = len(X)
            device_reuse_counts = np.zeros(n_rows)
            device_customer_counts = np.zeros(n_rows)
            customer_device_counts = np.zeros(n_rows)
            device_ages = np.zeros(n_rows)
            device_diversity_scores = np.zeros(n_rows)
            browser_diversity_scores = np.zeros(n_rows)
            os_diversity_scores = np.zeros(n_rows)

            # Process each row
            for idx, row in X.iterrows():
                device_id = row[self.device_id_column]
                customer_id = row[self.customer_id_column]
                current_time = pd.to_datetime(row[self.timestamp_column])
                row_idx = X.index.get_loc(idx)

                # Device reuse patterns
                if pd.notna(device_id):
                    if device_id in self.device_stats_:
                        device_stats = self.device_stats_[device_id]
                        device_reuse_counts[row_idx] = device_stats["transaction_count"]
                        device_customer_counts[row_idx] = device_stats["unique_customers"]

                        # Calculate device age (days since first seen)
                        first_seen = pd.to_datetime(device_stats["first_seen"])
                        device_ages[row_idx] = (current_time - first_seen).days

                    # Compute current device diversity for this customer
                    if pd.notna(customer_id):
                        customer_history = X[
                            (X[self.customer_id_column] == customer_id)
                            & (pd.to_datetime(X[self.timestamp_column]) <= current_time)
                        ]

                        unique_devices = customer_history[self.device_id_column].nunique()
                        customer_device_counts[row_idx] = unique_devices

                        # Device diversity score (inverse of concentration)
                        device_diversity_scores[row_idx] = self._compute_diversity_score(
                            customer_history[self.device_id_column]
                        )

                # Browser/OS diversity
                if self.browser_column and self.browser_column in X.columns:
                    if pd.notna(customer_id):
                        customer_history = X[
                            (X[self.customer_id_column] == customer_id)
                            & (pd.to_datetime(X[self.timestamp_column]) <= current_time)
                        ]
                        browser_diversity_scores[row_idx] = self._compute_diversity_score(
                            customer_history[self.browser_column]
                        )

                if self.os_column and self.os_column in X.columns:
                    if pd.notna(customer_id):
                        customer_history = X[
                            (X[self.customer_id_column] == customer_id)
                            & (pd.to_datetime(X[self.timestamp_column]) <= current_time)
                        ]
                        os_diversity_scores[row_idx] = self._compute_diversity_score(
                            customer_history[self.os_column]
                        )

            # Create feature columns
            result["device_reuse_count"] = device_reuse_counts
            result["device_customer_count"] = device_customer_counts
            result["customer_device_count"] = customer_device_counts
            result["device_age_days"] = device_ages
            result["device_diversity_score"] = device_diversity_scores

            if self.browser_column and self.browser_column in X.columns:
                result["browser_diversity_score"] = browser_diversity_scores

            if self.os_column and self.os_column in X.columns:
                result["os_diversity_score"] = os_diversity_scores

            # Derived risk indicators
            result["is_shared_device"] = (result["device_customer_count"] > 1).astype(int)
            result["is_multi_device_customer"] = (result["customer_device_count"] > 1).astype(int)
            result["is_new_device"] = (result["device_age_days"] == 0).astype(int)
            result["is_high_reuse_device"] = (
                result["device_reuse_count"] > result["device_reuse_count"].quantile(0.9)
            ).astype(int)

            # Device fingerprint features
            if hasattr(self, "_fingerprint_features"):
                for feature_name, feature_values in self._fingerprint_features.items():
                    if len(feature_values) == len(result):
                        result[feature_name] = feature_values

            # Update feature names
            feature_columns = [col for col in result.columns if col not in X.columns]
            self._feature_names_out = feature_columns

            self.logger.info(f"Generated {len(self._feature_names_out)} device features")

        # Update metadata
        self._update_metadata(X, result)

        return result

    def _compute_device_stats(self, device_data: pd.DataFrame) -> dict[str, Any]:
        """Compute statistics for a single device."""
        if len(device_data) == 0:
            return {}

        timestamps = pd.to_datetime(device_data[self.timestamp_column])
        customers = device_data[self.customer_id_column]

        return {
            "transaction_count": len(device_data),
            "unique_customers": customers.nunique(),
            "first_seen": timestamps.min().isoformat(),
            "last_seen": timestamps.max().isoformat(),
            "usage_days": (timestamps.max() - timestamps.min()).days + 1,
        }

    def _compute_customer_device_stats(self, customer_data: pd.DataFrame) -> dict[str, Any]:
        """Compute device statistics for a single customer."""
        if len(customer_data) == 0:
            return {}

        devices = customer_data[self.device_id_column]

        return {
            "unique_devices": devices.nunique(),
            "device_diversity": self._compute_diversity_score(devices),
        }

    def _compute_diversity_score(self, series: pd.Series) -> float:
        """
        Compute diversity score using Shannon entropy.
        Higher values indicate more diverse usage patterns.
        """
        if len(series) == 0:
            return 0.0

        value_counts = series.value_counts(normalize=True)

        if len(value_counts) <= 1:
            return 0.0

        # Shannon entropy
        entropy = -np.sum(value_counts * np.log2(value_counts))

        # Normalize by maximum possible entropy
        max_entropy = np.log2(len(value_counts))

        return entropy / max_entropy if max_entropy > 0 else 0.0

    def _create_device_fingerprints(self, X: pd.DataFrame):
        """Create device fingerprints from available attributes."""
        fingerprint_columns = []

        if self.browser_column and self.browser_column in X.columns:
            fingerprint_columns.append(self.browser_column)

        if self.os_column and self.os_column in X.columns:
            fingerprint_columns.append(self.os_column)

        if self.screen_resolution_column and self.screen_resolution_column in X.columns:
            fingerprint_columns.append(self.screen_resolution_column)

        if fingerprint_columns:
            # Create composite fingerprints
            for col in fingerprint_columns:
                unique_values = X[col].nunique()
                self.device_fingerprints_[f"{col}_diversity"] = unique_values

    def _custom_validation(self, X: pd.DataFrame) -> ValidationResult:
        """Custom validation for device transformer."""
        errors = []
        warnings = []

        # Check for missing device IDs
        missing_devices = X[self.device_id_column].isnull().sum()
        total_rows = len(X)

        if missing_devices == total_rows:
            warnings.append("All device IDs are missing - device features will be limited")
        elif missing_devices > total_rows * 0.5:
            warnings.append(f"High rate of missing device IDs: {missing_devices/total_rows:.1%}")

        # Check for missing customer IDs
        missing_customers = X[self.customer_id_column].isnull().sum()
        if missing_customers > 0:
            warnings.append(f"Found {missing_customers} rows with missing customer IDs")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class GeographicTransformer(BaseFeatureTransformer):
    """
    Transformer for geographic and location-based features.

    Creates:
    - Country/region mismatch indicators
    - Location frequency patterns
    - Distance calculations (placeholder)
    - Geographic risk indicators
    """

    def __init__(
        self,
        country_column: str = "country",
        customer_id_column: str = "customer_id",
        timestamp_column: str = "timestamp",
        billing_country_column: str = None,
        shipping_country_column: str = None,
        ip_country_column: str = None,
        city_column: str = None,
        **kwargs,
    ):

        dependencies = [country_column, customer_id_column, timestamp_column]
        for col in [
            billing_country_column,
            shipping_country_column,
            ip_country_column,
            city_column,
        ]:
            if col:
                dependencies.append(col)

        super().__init__(
            name="geographic_transformer",
            version="1.0.0",
            description="Geographic location and mismatch features",
            dependencies=dependencies,
            country_column=country_column,
            customer_id_column=customer_id_column,
            timestamp_column=timestamp_column,
            billing_country_column=billing_country_column,
            shipping_country_column=shipping_country_column,
            ip_country_column=ip_country_column,
            city_column=city_column,
            **kwargs,
        )
        self.country_column = country_column
        self.customer_id_column = customer_id_column
        self.timestamp_column = timestamp_column
        self.billing_country_column = billing_country_column
        self.shipping_country_column = shipping_country_column
        self.ip_country_column = ip_country_column
        self.city_column = city_column

        # Fit parameters
        self.country_stats_ = {}
        self.customer_location_stats_ = {}
        self.high_risk_countries_ = set()

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "GeographicTransformer":
        """Fit the transformer by computing geographic patterns."""
        self._validate_input(X)

        with self.logger.stage_context("fitting_geographic_transformer"):
            # Compute country-level statistics
            if pd.notna(X[self.country_column]).any():
                country_groups = X.groupby(self.country_column)

                for country, group in country_groups:
                    if pd.notna(country):
                        stats = self._compute_country_stats(group)
                        self.country_stats_[country] = stats

            # Compute customer location patterns
            if (
                pd.notna(X[self.customer_id_column]).any()
                and pd.notna(X[self.country_column]).any()
            ):

                customer_groups = X.groupby(self.customer_id_column)

                for customer_id, group in customer_groups:
                    if pd.notna(customer_id):
                        stats = self._compute_customer_location_stats(group)
                        self.customer_location_stats_[customer_id] = stats

            # Identify high-risk countries (placeholder logic)
            if self.country_stats_:
                # Countries with high mismatch rates or low volume
                for country, stats in self.country_stats_.items():
                    mismatch_rate = stats.get("mismatch_rate", 0)
                    transaction_count = stats.get("transaction_count", 0)

                    if mismatch_rate > 0.1 or transaction_count < 10:  # Placeholder thresholds
                        self.high_risk_countries_.add(country)

            # Compute global statistics
            self.fit_statistics = {
                "n_countries": len(self.country_stats_),
                "n_high_risk_countries": len(self.high_risk_countries_),
                "avg_locations_per_customer": (
                    np.mean(
                        [
                            stats["unique_countries"]
                            for stats in self.customer_location_stats_.values()
                        ]
                    )
                    if self.customer_location_stats_
                    else 0
                ),
                "top_countries": sorted(
                    self.country_stats_.items(),
                    key=lambda x: x[1]["transaction_count"],
                    reverse=True,
                )[:5],
            }

            # Update state
            self.is_fitted = True

            self.logger.info(
                f"Geographic transformer fitted for {len(self.country_stats_)} countries"
            )

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform data to create geographic features."""
        self._check_fitted()
        self._validate_input(X)

        result = X.copy()

        with self.logger.stage_context("transforming_geographic_features"):
            # Initialize feature arrays
            n_rows = len(X)
            country_transaction_counts = np.zeros(n_rows)
            customer_location_counts = np.zeros(n_rows)
            location_diversity_scores = np.zeros(n_rows)

            # Mismatch indicators
            country_mismatches = np.zeros(n_rows, dtype=int)
            billing_mismatches = np.zeros(n_rows, dtype=int)
            shipping_mismatches = np.zeros(n_rows, dtype=int)
            ip_mismatches = np.zeros(n_rows, dtype=int)

            # Process each row
            for idx, row in X.iterrows():
                country = row[self.country_column]
                customer_id = row[self.customer_id_column]
                current_time = pd.to_datetime(row[self.timestamp_column])
                row_idx = X.index.get_loc(idx)

                # Country statistics
                if pd.notna(country) and country in self.country_stats_:
                    country_stats = self.country_stats_[country]
                    country_transaction_counts[row_idx] = country_stats["transaction_count"]

                # Customer location patterns
                if pd.notna(customer_id):
                    customer_history = X[
                        (X[self.customer_id_column] == customer_id)
                        & (pd.to_datetime(X[self.timestamp_column]) <= current_time)
                    ]

                    unique_countries = customer_history[self.country_column].nunique()
                    customer_location_counts[row_idx] = unique_countries

                    # Location diversity
                    location_diversity_scores[row_idx] = self._compute_diversity_score(
                        customer_history[self.country_column]
                    )

                # Mismatch detection
                if pd.notna(country):
                    # Billing country mismatch
                    if self.billing_country_column and self.billing_country_column in X.columns:
                        billing_country = row[self.billing_country_column]
                        if pd.notna(billing_country) and billing_country != country:
                            billing_mismatches[row_idx] = 1

                    # Shipping country mismatch
                    if self.shipping_country_column and self.shipping_country_column in X.columns:
                        shipping_country = row[self.shipping_country_column]
                        if pd.notna(shipping_country) and shipping_country != country:
                            shipping_mismatches[row_idx] = 1

                    # IP country mismatch
                    if self.ip_country_column and self.ip_country_column in X.columns:
                        ip_country = row[self.ip_country_column]
                        if pd.notna(ip_country) and ip_country != country:
                            ip_mismatches[row_idx] = 1

                    # Any country mismatch
                    if (
                        billing_mismatches[row_idx]
                        or shipping_mismatches[row_idx]
                        or ip_mismatches[row_idx]
                    ):
                        country_mismatches[row_idx] = 1

            # Create feature columns
            result["country_transaction_count"] = country_transaction_counts
            result["customer_location_count"] = customer_location_counts
            result["location_diversity_score"] = location_diversity_scores
            result["country_mismatch"] = country_mismatches

            if self.billing_country_column and self.billing_country_column in X.columns:
                result["billing_country_mismatch"] = billing_mismatches

            if self.shipping_country_column and self.shipping_country_column in X.columns:
                result["shipping_country_mismatch"] = shipping_mismatches

            if self.ip_country_column and self.ip_country_column in X.columns:
                result["ip_country_mismatch"] = ip_mismatches

            # Risk indicators
            result["is_high_risk_country"] = (
                X[self.country_column].isin(self.high_risk_countries_).astype(int)
            )
            result["is_foreign_transaction"] = (result["country_mismatch"] > 0).astype(int)
            result["is_multi_country_customer"] = (result["customer_location_count"] > 1).astype(
                int
            )

            # Distance placeholder (would require coordinate data)
            result["distance_from_home"] = 0.0  # Placeholder

            # Update feature names
            feature_columns = [col for col in result.columns if col not in X.columns]
            self._feature_names_out = feature_columns

            self.logger.info(f"Generated {len(self._feature_names_out)} geographic features")

        # Update metadata
        self._update_metadata(X, result)

        return result

    def _compute_country_stats(self, country_data: pd.DataFrame) -> dict[str, Any]:
        """Compute statistics for a single country."""
        if len(country_data) == 0:
            return {}

        transaction_count = len(country_data)

        # Calculate mismatch rate (placeholder)
        mismatch_count = 0
        if self.billing_country_column and self.billing_country_column in country_data.columns:
            mismatch_count += (
                country_data[self.country_column] != country_data[self.billing_country_column]
            ).sum()

        mismatch_rate = mismatch_count / transaction_count if transaction_count > 0 else 0

        return {
            "transaction_count": transaction_count,
            "unique_customers": country_data[self.customer_id_column].nunique(),
            "mismatch_rate": mismatch_rate,
        }

    def _compute_customer_location_stats(self, customer_data: pd.DataFrame) -> dict[str, Any]:
        """Compute location statistics for a single customer."""
        if len(customer_data) == 0:
            return {}

        countries = customer_data[self.country_column]

        return {
            "unique_countries": countries.nunique(),
            "location_diversity": self._compute_diversity_score(countries),
        }

    def _compute_diversity_score(self, series: pd.Series) -> float:
        """Compute diversity score using Shannon entropy."""
        if len(series) == 0:
            return 0.0

        value_counts = series.value_counts(normalize=True)

        if len(value_counts) <= 1:
            return 0.0

        # Shannon entropy
        entropy = -np.sum(value_counts * np.log2(value_counts))

        # Normalize by maximum possible entropy
        max_entropy = np.log2(len(value_counts))

        return entropy / max_entropy if max_entropy > 0 else 0.0

    def _custom_validation(self, X: pd.DataFrame) -> ValidationResult:
        """Custom validation for geographic transformer."""
        errors = []
        warnings = []

        # Check for missing country data
        missing_countries = X[self.country_column].isnull().sum()
        total_rows = len(X)

        if missing_countries == total_rows:
            warnings.append("All country data is missing - geographic features will be limited")
        elif missing_countries > total_rows * 0.3:
            warnings.append(
                f"High rate of missing country data: {missing_countries/total_rows:.1%}"
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
