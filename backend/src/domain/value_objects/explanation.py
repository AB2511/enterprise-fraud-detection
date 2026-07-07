"""Explanation Value Object - SHAP explanation data."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FeatureContribution:
    """Individual feature contribution to prediction.

    Attributes:
        feature_name: Name of the feature
        feature_value: Actual value of the feature for this prediction
        shap_value: SHAP value indicating contribution to prediction
    """

    feature_name: str
    feature_value: Any
    shap_value: float

    def __post_init__(self) -> None:
        """Validate feature contribution."""
        if not self.feature_name:
            raise ValueError("Feature name cannot be empty")


@dataclass(frozen=True)
class Explanation:
    """Explanation value object containing SHAP values.

    Immutable object representing model explanation for a single prediction.

    Attributes:
        top_features: Top N feature contributions (sorted by absolute SHAP value)
        base_value: Base value (expected value over training data)
    """

    top_features: tuple[FeatureContribution, ...]
    base_value: float

    def __post_init__(self) -> None:
        """Validate explanation."""
        if not self.top_features:
            raise ValueError("Explanation must have at least one feature")

        if len(self.top_features) > 10:
            raise ValueError("Maximum 10 top features allowed")

    @property
    def feature_count(self) -> int:
        """Get number of features in explanation."""
        return len(self.top_features)

    def get_feature_contribution(self, feature_name: str) -> float:
        """Get SHAP value for a specific feature.

        Args:
            feature_name: Name of the feature

        Returns:
            SHAP value if feature exists, 0.0 otherwise
        """
        for contrib in self.top_features:
            if contrib.feature_name == feature_name:
                return contrib.shap_value
        return 0.0

    @property
    def total_contribution(self) -> float:
        """Calculate total contribution from all features."""
        return sum(contrib.shap_value for contrib in self.top_features)
