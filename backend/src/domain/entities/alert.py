"""Alert Entity - Fraud alert for analyst review."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass
class Alert:
    """Alert entity representing a fraud alert requiring investigation.

    Alerts are generated when predictions exceed thresholds and require
    manual analyst review.

    Attributes:
        alert_id: Unique identifier
        prediction_id: Associated prediction
        transaction_id: Associated transaction
        severity: Alert severity (low, medium, high, critical)
        alert_type: Type of alert (rule_based, ml_based, anomaly, velocity)
        assigned_analyst_id: Analyst assigned to review
        status: Alert status (open, in_review, resolved, false_positive, confirmed_fraud)
        resolution: Resolution outcome
        resolution_notes: Notes from analyst
        created_at: Alert creation timestamp
        assigned_at: When alert was assigned
        resolved_at: When alert was resolved
        updated_at: Last update timestamp
    """

    alert_id: UUID = field(default_factory=uuid4)
    prediction_id: UUID = field(default_factory=uuid4)
    transaction_id: UUID = field(default_factory=uuid4)
    severity: str = "medium"
    alert_type: str = "ml_based"
    assigned_analyst_id: UUID | None = None
    status: str = "open"
    resolution: str | None = None
    resolution_notes: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    assigned_at: datetime | None = None
    resolved_at: datetime | None = None
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate alert business rules."""
        valid_severities = ["low", "medium", "high", "critical"]
        if self.severity not in valid_severities:
            raise ValueError(f"Severity must be one of: {valid_severities}")

        valid_types = ["rule_based", "ml_based", "anomaly", "velocity", "manual"]
        if self.alert_type not in valid_types:
            raise ValueError(f"Alert type must be one of: {valid_types}")

        valid_statuses = ["open", "in_review", "resolved", "false_positive", "confirmed_fraud"]
        if self.status not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")

    def assign_to_analyst(self, analyst_id: UUID) -> None:
        """Assign alert to an analyst.

        Args:
            analyst_id: ID of analyst to assign

        Raises:
            ValueError: If alert is already resolved
        """
        if self.is_resolved:
            raise ValueError("Cannot assign resolved alert")

        self.assigned_analyst_id = analyst_id
        self.assigned_at = datetime.utcnow()
        self.status = "in_review"
        self.updated_at = datetime.utcnow()

    def resolve_as_fraud(self, analyst_id: UUID, notes: str | None = None) -> None:
        """Resolve alert as confirmed fraud.

        Args:
            analyst_id: ID of analyst resolving
            notes: Resolution notes

        Raises:
            ValueError: If alert is not assigned or already resolved
        """
        if self.is_resolved:
            raise ValueError("Alert is already resolved")

        if self.assigned_analyst_id != analyst_id:
            raise ValueError("Alert can only be resolved by assigned analyst")

        self.status = "confirmed_fraud"
        self.resolution = "fraud"
        self.resolution_notes = notes
        self.resolved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def resolve_as_false_positive(self, analyst_id: UUID, notes: str | None = None) -> None:
        """Resolve alert as false positive.

        Args:
            analyst_id: ID of analyst resolving
            notes: Resolution notes

        Raises:
            ValueError: If alert is not assigned or already resolved
        """
        if self.is_resolved:
            raise ValueError("Alert is already resolved")

        if self.assigned_analyst_id != analyst_id:
            raise ValueError("Alert can only be resolved by assigned analyst")

        self.status = "false_positive"
        self.resolution = "false_positive"
        self.resolution_notes = notes
        self.resolved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def escalate(self, new_severity: str) -> None:
        """Escalate alert to higher severity.

        Args:
            new_severity: New severity level

        Raises:
            ValueError: If new severity is not higher
        """
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}

        if new_severity not in severity_order:
            raise ValueError(f"Invalid severity: {new_severity}")

        if severity_order[new_severity] <= severity_order[self.severity]:
            raise ValueError("Can only escalate to higher severity")

        self.severity = new_severity
        self.updated_at = datetime.utcnow()

    @property
    def is_resolved(self) -> bool:
        """Check if alert is resolved."""
        return self.status in ["resolved", "false_positive", "confirmed_fraud"]

    @property
    def is_critical(self) -> bool:
        """Check if alert is critical severity."""
        return self.severity == "critical"

    @property
    def is_assigned(self) -> bool:
        """Check if alert is assigned to an analyst."""
        return self.assigned_analyst_id is not None

    @property
    def resolution_time_hours(self) -> float | None:
        """Calculate resolution time in hours."""
        if not self.resolved_at:
            return None

        delta = self.resolved_at - self.created_at
        return delta.total_seconds() / 3600

    @property
    def is_overdue(self, sla_hours: int = 24) -> bool:
        """Check if alert is overdue based on SLA.

        Args:
            sla_hours: SLA in hours

        Returns:
            True if alert is overdue
        """
        if self.is_resolved:
            return False

        age_hours = (datetime.utcnow() - self.created_at).total_seconds() / 3600
        return age_hours > sla_hours
