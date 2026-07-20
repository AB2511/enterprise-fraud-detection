"""Prediction Entity - Aggregate Root."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.enums.prediction_class import PredictionClass


@dataclass
class Prediction:
    """Prediction aggregate root representing a fraud prediction result.

    Stores the model's prediction, explanation, and performance metrics.
    Links to the transaction that was analyzed.

    Attributes:
        prediction_id: Unique identifier for this prediction
        transaction_id: ID of the transaction that was analyzed
        model_version: Version of model that made prediction
        fraud_probability: Predicted probability of fraud [0, 1]
        anomaly_score: Anomaly score from isolation forest [0, 1]
        risk_score: Converted risk score [0, 100]
        predicted_class: Binary classification result
        decision: Model decision (approve, review, decline)
        confidence: Model confidence [0, 1]
        explanation_data: Serialized explanation (SHAP values placeholder)
        latency_ms: Time taken for prediction in milliseconds
        timestamp: When prediction was made
        analyst_feedback_id: Optional ID of analyst feedback
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    prediction_id: UUID = field(default_factory=uuid4)
    transaction_id: UUID = field(default_factory=uuid4)
    model_version: str = "0.0.0"
    fraud_probability: float = 0.0
    anomaly_score: float = 0.0
    risk_score: int = 0
    predicted_class: str = "legitimate"
    decision: str = "approve"
    confidence: float = 0.0
    explanation_data: dict[str, object] = field(default_factory=dict)
    latency_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    analyst_feedback_id: UUID | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate prediction business rules."""
        if not (0.0 <= self.fraud_probability <= 1.0):
            raise ValueError("Fraud probability must be between 0 and 1")

        if not (0.0 <= self.anomaly_score <= 1.0):
            raise ValueError("Anomaly score must be between 0 and 1")

        if not (0 <= self.risk_score <= 100):
            raise ValueError("Risk score must be between 0 and 100")

        if self.predicted_class not in [
            PredictionClass.FRAUD.value,
            PredictionClass.LEGITIMATE.value,
        ]:
            raise ValueError("Predicted class must be 'fraud' or 'legitimate'")

        valid_decisions = ["approve", "review", "decline"]
        if self.decision not in valid_decisions:
            raise ValueError(f"Decision must be one of: {valid_decisions}")

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0 and 1")

        if self.latency_ms < 0:
            raise ValueError("Latency cannot be negative")

    def approve(self) -> None:
        """Override prediction decision to approve."""
        self.decision = "approve"
        self.updated_at = datetime.utcnow()

    def review(self) -> None:
        """Mark prediction for manual review."""
        self.decision = "review"
        self.updated_at = datetime.utcnow()

    def reject(self) -> None:
        """Override prediction decision to decline."""
        self.decision = "decline"
        self.updated_at = datetime.utcnow()

    def add_feedback(self, feedback_id: UUID) -> None:
        """Link analyst feedback to this prediction.

        Args:
            feedback_id: Analyst feedback ID
        """
        self.analyst_feedback_id = feedback_id
        self.updated_at = datetime.utcnow()

    @property
    def is_fraud(self) -> bool:
        """Check if prediction indicates fraud."""
        return self.predicted_class == "fraud"

    @property
    def is_high_risk(self) -> bool:
        """Check if prediction is high risk (score >= 80)."""
        return self.risk_score >= 80

    @property
    def is_medium_risk(self) -> bool:
        """Check if prediction is medium risk (score 50-79)."""
        return 50 <= self.risk_score < 80

    @property
    def is_low_risk(self) -> bool:
        """Check if prediction is low risk (score < 50)."""
        return self.risk_score < 50

    @property
    def has_feedback(self) -> bool:
        """Check if analyst has provided feedback."""
        return self.analyst_feedback_id is not None

    @property
    def requires_review(self) -> bool:
        """Check if prediction requires manual review."""
        return self.decision == "review"

    @property
    def is_approved(self) -> bool:
        """Check if prediction decision is approve."""
        return self.decision == "approve"

    @property
    def is_declined(self) -> bool:
        """Check if prediction decision is decline."""
        return self.decision == "decline"

    @property
    def is_high_confidence(self) -> bool:
        """Check if model has high confidence (>= 0.8)."""
        return self.confidence >= 0.8

    def get_risk_level(self) -> str:
        """Get risk level classification.

        Returns:
            Risk level (low, medium, high, critical)
        """
        if self.risk_score >= 90:
            return "critical"
        elif self.risk_score >= 70:
            return "high"
        elif self.risk_score >= 40:
            return "medium"
        else:
            return "low"
