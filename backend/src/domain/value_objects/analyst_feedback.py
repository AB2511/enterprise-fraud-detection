"""Analyst Feedback Value Object."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class AnalystFeedback:
    """Analyst Feedback value object for prediction review.

    Immutable record of analyst's review of a prediction.

    Attributes:
        feedback_id: Unique identifier for this feedback
        prediction_id: ID of prediction being reviewed
        analyst_id: ID of analyst providing feedback
        confirmed_fraud: Whether analyst confirms prediction as fraud
        confidence: Analyst's confidence level (1-5)
        notes: Optional investigation notes
        timestamp: When feedback was provided
    """

    feedback_id: UUID = field(default_factory=uuid4)
    prediction_id: UUID = field(default_factory=uuid4)
    analyst_id: str = ""
    confirmed_fraud: bool = False
    confidence: int = 3
    notes: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate analyst feedback."""
        if not self.analyst_id:
            raise ValueError("Analyst ID is required")

        if not (1 <= self.confidence <= 5):
            raise ValueError("Confidence must be between 1 and 5")

    @property
    def is_high_confidence(self) -> bool:
        """Check if analyst has high confidence (4-5)."""
        return self.confidence >= 4

    @property
    def has_notes(self) -> bool:
        """Check if analyst provided investigation notes."""
        return self.notes is not None and len(self.notes.strip()) > 0
