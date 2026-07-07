"""Prediction Class Enumeration."""

from enum import Enum


class PredictionClass(str, Enum):
    """Binary classification result for fraud detection."""

    FRAUD = "fraud"
    LEGITIMATE = "legitimate"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    @classmethod
    def from_probability(cls, probability: float, threshold: float = 0.5) -> "PredictionClass":
        """Convert fraud probability to prediction class.

        Args:
            probability: Fraud probability [0, 1]
            threshold: Decision threshold

        Returns:
            PredictionClass based on threshold
        """
        return cls.FRAUD if probability >= threshold else cls.LEGITIMATE
