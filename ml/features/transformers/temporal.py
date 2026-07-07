"""
Temporal Feature Transformers

Transformers for creating time-based features from transaction timestamps,
including cyclical encodings, business hours, holidays, and other temporal patterns.
"""

import numpy as np
import pandas as pd

from ml.features.transformers.base import BaseFeatureTransformer, ValidationResult


class TemporalTransformer(BaseFeatureTransformer):
    """
    Transformer for basic temporal features.

    Creates:
    - hour, minute
    - day, weekday, month
    - weekend flag
    - business hours flag
    - night transaction flag
    """

    def __init__(
        self,
        timestamp_column: str = "timestamp",
        business_start_hour: int = 9,
        business_end_hour: int = 17,
        night_start_hour: int = 22,
        night_end_hour: int = 6,
        **kwargs,
    ):
        super().__init__(
            name="temporal_transformer",
            version="1.0.0",
            description="Basic temporal features from transaction timestamps",
            dependencies=[timestamp_column],
            timestamp_column=timestamp_column,
            business_start_hour=business_start_hour,
            business_end_hour=business_end_hour,
            night_start_hour=night_start_hour,
            night_end_hour=night_end_hour,
            **kwargs,
        )
        self.timestamp_column = timestamp_column
        self.business_start_hour = business_start_hour
        self.business_end_hour = business_end_hour
        self.night_start_hour = night_start_hour
        self.night_end_hour = night_end_hour

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "TemporalTransformer":
        """Fit the transformer (no parameters to learn for basic temporal features)."""
        self._validate_input(X)

        with self.logger.stage_context("fitting_temporal_transformer"):
            # Convert to datetime if needed
            timestamps = pd.to_datetime(X[self.timestamp_column])

            # Compute fit statistics
            self.fit_statistics = {
                "date_range_start": timestamps.min().isoformat(),
                "date_range_end": timestamps.max().isoformat(),
                "n_unique_dates": timestamps.dt.date.nunique(),
                "n_unique_hours": timestamps.dt.hour.nunique(),
                "weekend_ratio": ((timestamps.dt.dayofweek >= 5).mean()),
                "business_hours_ratio": self._compute_business_hours_ratio(timestamps),
                "night_ratio": self._compute_night_ratio(timestamps),
            }

            # Update state
            self.is_fitted = True

            self.logger.info(
                f"Temporal transformer fitted - date range: {self.fit_statistics['date_range_start'][:10]} to {self.fit_statistics['date_range_end'][:10]}"
            )

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform timestamps into temporal features."""
        self._check_fitted()
        self._validate_input(X)

        result = X.copy()

        with self.logger.stage_context("transforming_temporal_features"):
            # Convert to datetime if needed
            timestamps = pd.to_datetime(X[self.timestamp_column])

            # Basic time components
            result["hour"] = timestamps.dt.hour
            result["minute"] = timestamps.dt.minute
            result["day"] = timestamps.dt.day
            result["weekday"] = timestamps.dt.dayofweek  # 0=Monday, 6=Sunday
            result["month"] = timestamps.dt.month

            # Derived flags
            result["is_weekend"] = (timestamps.dt.dayofweek >= 5).astype(int)
            result["is_business_hours"] = self._is_business_hours(timestamps).astype(int)
            result["is_night_transaction"] = self._is_night_transaction(timestamps).astype(int)

            # Cyclical encodings (sine/cosine for cyclical nature)
            result["hour_sin"] = np.sin(2 * np.pi * timestamps.dt.hour / 24)
            result["hour_cos"] = np.cos(2 * np.pi * timestamps.dt.hour / 24)
            result["day_sin"] = np.sin(2 * np.pi * timestamps.dt.day / 31)  # Approximate
            result["day_cos"] = np.cos(2 * np.pi * timestamps.dt.day / 31)
            result["month_sin"] = np.sin(2 * np.pi * timestamps.dt.month / 12)
            result["month_cos"] = np.cos(2 * np.pi * timestamps.dt.month / 12)
            result["weekday_sin"] = np.sin(2 * np.pi * timestamps.dt.dayofweek / 7)
            result["weekday_cos"] = np.cos(2 * np.pi * timestamps.dt.dayofweek / 7)

            # Update feature names
            self._feature_names_out = [
                "hour",
                "minute",
                "day",
                "weekday",
                "month",
                "is_weekend",
                "is_business_hours",
                "is_night_transaction",
                "hour_sin",
                "hour_cos",
                "day_sin",
                "day_cos",
                "month_sin",
                "month_cos",
                "weekday_sin",
                "weekday_cos",
            ]

            self.logger.info(f"Generated {len(self._feature_names_out)} temporal features")

        # Update metadata
        self._update_metadata(X, result)

        return result

    def _is_business_hours(self, timestamps: pd.Series) -> pd.Series:
        """Check if timestamps fall within business hours."""
        hour = timestamps.dt.hour
        weekday = timestamps.dt.dayofweek

        # Business hours: weekdays between business_start_hour and business_end_hour
        is_weekday = weekday < 5
        is_business_hour = (hour >= self.business_start_hour) & (hour < self.business_end_hour)

        return is_weekday & is_business_hour

    def _is_night_transaction(self, timestamps: pd.Series) -> pd.Series:
        """Check if timestamps fall during night hours."""
        hour = timestamps.dt.hour

        # Night hours: either >= night_start_hour OR <= night_end_hour
        if self.night_start_hour > self.night_end_hour:
            return (hour >= self.night_start_hour) | (hour <= self.night_end_hour)
        else:
            return (hour >= self.night_start_hour) & (hour <= self.night_end_hour)

    def _compute_business_hours_ratio(self, timestamps: pd.Series) -> float:
        """Compute ratio of transactions during business hours."""
        return self._is_business_hours(timestamps).mean()

    def _compute_night_ratio(self, timestamps: pd.Series) -> float:
        """Compute ratio of transactions during night hours."""
        return self._is_night_transaction(timestamps).mean()

    def _custom_validation(self, X: pd.DataFrame) -> ValidationResult:
        """Custom validation for temporal transformer."""
        errors = []
        warnings = []

        try:
            timestamps = pd.to_datetime(X[self.timestamp_column])
        except Exception as e:
            errors.append(f"Cannot convert {self.timestamp_column} to datetime: {e}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Check for null timestamps
        null_count = timestamps.isnull().sum()
        if null_count > 0:
            warnings.append(f"Found {null_count} null timestamps")

        # Check for future timestamps (potential data issue)
        future_count = (timestamps > pd.Timestamp.now()).sum()
        if future_count > 0:
            warnings.append(f"Found {future_count} future timestamps")

        # Check for extremely old timestamps
        very_old = timestamps < pd.Timestamp("2000-01-01")
        if very_old.sum() > 0:
            warnings.append(f"Found {very_old.sum()} timestamps before 2000")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class HolidayTransformer(BaseFeatureTransformer):
    """
    Transformer for holiday features.

    Creates binary flags for holidays (placeholder implementation).
    """

    def __init__(
        self,
        timestamp_column: str = "timestamp",
        country_code: str = "US",
        include_observed: bool = True,
        custom_holidays: list[str] = None,
        **kwargs,
    ):
        super().__init__(
            name="holiday_transformer",
            version="1.0.0",
            description="Holiday features from transaction timestamps",
            dependencies=[timestamp_column],
            timestamp_column=timestamp_column,
            country_code=country_code,
            include_observed=include_observed,
            custom_holidays=custom_holidays or [],
            **kwargs,
        )
        self.timestamp_column = timestamp_column
        self.country_code = country_code
        self.include_observed = include_observed
        self.custom_holidays = custom_holidays or []

        # Fit parameters (placeholder - would integrate with holidays library)
        self.holiday_dates_: set[str] = set()

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "HolidayTransformer":
        """Fit the transformer by identifying holiday dates in the dataset."""
        self._validate_input(X)

        with self.logger.stage_context("fitting_holiday_transformer"):
            timestamps = pd.to_datetime(X[self.timestamp_column])
            date_range = pd.date_range(timestamps.min(), timestamps.max(), freq="D")

            # Placeholder holiday logic (would use holidays library in production)
            # For now, just identify some common US holidays
            placeholder_holidays = self._get_placeholder_holidays(date_range)
            self.holiday_dates_ = set(placeholder_holidays)

            # Add custom holidays
            for holiday_date in self.custom_holidays:
                try:
                    parsed_date = pd.to_datetime(holiday_date).strftime("%Y-%m-%d")
                    self.holiday_dates_.add(parsed_date)
                except Exception as e:
                    self.logger.warning(
                        f"Could not parse custom holiday date '{holiday_date}': {e}"
                    )

            # Update state
            self.is_fitted = True
            self.fit_statistics = {
                "n_holidays_in_range": len(self.holiday_dates_),
                "holiday_dates": sorted(list(self.holiday_dates_)),
                "country_code": self.country_code,
            }

            self.logger.info(f"Holiday transformer fitted with {len(self.holiday_dates_)} holidays")

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform timestamps into holiday features."""
        self._check_fitted()
        self._validate_input(X)

        result = X.copy()

        with self.logger.stage_context("transforming_holiday_features"):
            timestamps = pd.to_datetime(X[self.timestamp_column])
            dates = timestamps.dt.strftime("%Y-%m-%d")

            # Holiday flag
            result["is_holiday"] = dates.isin(self.holiday_dates_).astype(int)

            # Day before/after holiday
            dates_series = pd.to_datetime(dates)
            day_before = (dates_series + pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
            day_after = (dates_series - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")

            result["is_day_before_holiday"] = day_before.isin(self.holiday_dates_).astype(int)
            result["is_day_after_holiday"] = day_after.isin(self.holiday_dates_).astype(int)

            # Holiday period (3-day window around holidays)
            result["is_holiday_period"] = (
                result["is_holiday"]
                | result["is_day_before_holiday"]
                | result["is_day_after_holiday"]
            ).astype(int)

            # Update feature names
            self._feature_names_out = [
                "is_holiday",
                "is_day_before_holiday",
                "is_day_after_holiday",
                "is_holiday_period",
            ]

            self.logger.info(f"Generated {len(self._feature_names_out)} holiday features")

        # Update metadata
        self._update_metadata(X, result)

        return result

    def _get_placeholder_holidays(self, date_range: pd.DatetimeIndex) -> list[str]:
        """
        Get placeholder holidays for the date range.

        This is a simplified implementation. In production, would use
        the 'holidays' library or similar for accurate holiday calculations.
        """
        holidays = []

        for date in date_range:
            year = date.year

            # New Year's Day
            if date.month == 1 and date.day == 1:
                holidays.append(date.strftime("%Y-%m-%d"))

            # Independence Day (US)
            elif date.month == 7 and date.day == 4:
                holidays.append(date.strftime("%Y-%m-%d"))

            # Christmas Day
            elif date.month == 12 and date.day == 25:
                holidays.append(date.strftime("%Y-%m-%d"))

            # Thanksgiving (4th Thursday in November - approximate)
            elif date.month == 11 and date.weekday() == 3 and 22 <= date.day <= 28:
                holidays.append(date.strftime("%Y-%m-%d"))

        return holidays
