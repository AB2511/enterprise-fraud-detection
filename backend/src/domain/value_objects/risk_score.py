"""Risk Score Value Object."""

from dataclasses import dataclass
from typing import Literal

RiskLevel = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True)
class RiskScore:
    """Value object representing a risk score (0-100).

    Risk scores quantify the likelihood of fraud. Higher scores indicate
    higher risk.

    Attributes:
        score: Risk score value (0-100)
    """

    score: float

    def __post_init__(self) -> None:
        """Validate risk score range."""
        if not isinstance(self.score, (int, float)):
            raise TypeError("Risk score must be numeric")

        if self.score < 0 or self.score > 100:
            raise ValueError("Risk score must be between 0 and 100")

    def get_level(self) -> RiskLevel:
        """Get risk level classification.

        Returns:
            Risk level (low, medium, high, critical)
        """
        if self.score >= 80:
            return "critical"
        elif self.score >= 60:
            return "high"
        elif self.score >= 40:
            return "medium"
        else:
            return "low"

    def is_high_risk(self) -> bool:
        """Check if risk score is high or critical.

        Returns:
            True if score >= 60
        """
        return self.score >= 60

    def is_critical(self) -> bool:
        """Check if risk score is critical.

        Returns:
            True if score >= 80
        """
        return self.score >= 80

    def is_acceptable(self, threshold: float = 50.0) -> bool:
        """Check if risk score is below threshold.

        Args:
            threshold: Maximum acceptable risk score

        Returns:
            True if score is below threshold
        """
        return self.score < threshold

    def add(self, increment: float) -> "RiskScore":
        """Add to risk score (capped at 100).

        Args:
            increment: Amount to add

        Returns:
            New RiskScore instance
        """
        new_score = min(100.0, self.score + increment)
        return RiskScore(score=new_score)

    def multiply(self, factor: float) -> "RiskScore":
        """Multiply risk score (capped at 100).

        Args:
            factor: Multiplication factor

        Returns:
            New RiskScore instance
        """
        new_score = min(100.0, self.score * factor)
        return RiskScore(score=new_score)

    def normalize(self) -> float:
        """Normalize score to 0-1 range.

        Returns:
            Normalized score (0.0 to 1.0)
        """
        return self.score / 100.0

    def to_int(self) -> int:
        """Convert to integer score.

        Returns:
            Integer risk score
        """
        return int(round(self.score))

    @classmethod
    def from_probability(cls, probability: float) -> "RiskScore":
        """Create risk score from probability (0-1).

        Args:
            probability: Fraud probability (0.0 to 1.0)

        Returns:
            New RiskScore instance
        """
        if probability < 0 or probability > 1:
            raise ValueError("Probability must be between 0 and 1")

        return cls(score=probability * 100)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.score:.1f}"

    def __float__(self) -> float:
        """Float conversion."""
        return self.score

    def __int__(self) -> int:
        """Integer conversion."""
        return self.to_int()

    def __lt__(self, other: object) -> bool:
        """Less than comparison."""
        if not isinstance(other, RiskScore):
            return NotImplemented
        return self.score < other.score

    def __le__(self, other: object) -> bool:
        """Less than or equal comparison."""
        if not isinstance(other, RiskScore):
            return NotImplemented
        return self.score <= other.score

    def __gt__(self, other: object) -> bool:
        """Greater than comparison."""
        if not isinstance(other, RiskScore):
            return NotImplemented
        return self.score > other.score

    def __ge__(self, other: object) -> bool:
        """Greater than or equal comparison."""
        if not isinstance(other, RiskScore):
            return NotImplemented
        return self.score >= other.score
