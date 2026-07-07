"""Drift Report Entity - Aggregate Root."""

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid4


@dataclass
class DriftReport:
    """Drift Report aggregate root for monitoring model drift.

    Tracks feature drift, prediction drift, and performance degradation.

    Attributes:
        report_id: Unique identifier for this report
        model_version: Version of model being monitored
        report_date: Date of drift analysis
        feature_drift: Per-feature drift scores (KL divergence)
        prediction_drift: Overall prediction drift score (PSI)
        performance_metrics: Current performance metrics
        drift_detected: Whether significant drift was detected
        alert_triggered: Whether alert was sent
        created_at: When report was created
    """

    report_id: UUID = field(default_factory=uuid4)
    model_version: str = "0.0.0"
    report_date: date = field(default_factory=date.today)
    feature_drift: dict[str, float] = field(default_factory=dict)
    prediction_drift: float = 0.0
    performance_metrics: dict[str, float] = field(default_factory=dict)
    drift_detected: bool = False
    alert_triggered: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate drift report business rules."""
        if not self.model_version:
            raise ValueError("Model version is required")

        if self.prediction_drift < 0:
            raise ValueError("Prediction drift cannot be negative")

    def trigger_alert(self) -> None:
        """Mark that alert was triggered for this report."""
        self.alert_triggered = True

    def get_drifted_features(self, threshold: float = 0.1) -> list[str]:
        """Get list of features with drift above threshold.

        Args:
            threshold: KL divergence threshold for significant drift

        Returns:
            List of feature names with drift >= threshold
        """
        return [
            feature
            for feature, drift_score in self.feature_drift.items()
            if drift_score >= threshold
        ]

    @property
    def has_significant_drift(self) -> bool:
        """Check if report indicates significant drift."""
        return self.drift_detected

    @property
    def max_feature_drift(self) -> float:
        """Get maximum feature drift score."""
        return max(self.feature_drift.values()) if self.feature_drift else 0.0
