"""Model Type Enumeration."""

from enum import Enum


class ModelType(str, Enum):
    """Types of ML models supported by the platform."""

    XGBOOST = "xgboost"
    ISOLATION_FOREST = "isolation_forest"
    ENSEMBLE = "ensemble"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    @property
    def is_supervised(self) -> bool:
        """Check if model type requires labeled data."""
        return self in (ModelType.XGBOOST, ModelType.ENSEMBLE)

    @property
    def is_unsupervised(self) -> bool:
        """Check if model type works without labels."""
        return self == ModelType.ISOLATION_FOREST
