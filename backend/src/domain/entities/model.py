"""Model Entity - Aggregate Root."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class Model:
    """Model aggregate root representing an ML model version.

    Tracks model metadata, metrics, and deployment status.

    Attributes:
        model_id: Unique identifier for this model
        version: Semantic version (e.g., "1.2.3")
        model_type: Type of model (xgboost, isolation_forest)
        artifact_path: S3 URI or filesystem path to model file
        metadata: Training metadata (hyperparameters, dataset info)
        metrics: Performance metrics (PR-AUC, F1, etc.)
        training_date: When model was trained
        status: Current deployment status
        created_by: User who trained the model
        created_at: When model record was created
    """

    model_id: UUID = field(default_factory=uuid4)
    version: str = "0.0.0"
    model_type: str = ""
    artifact_path: str = ""
    metadata: dict[str, object] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    training_date: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "training"
    created_by: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate model business rules."""
        if not self.version:
            raise ValueError("Model version is required")

        if not self.model_type:
            raise ValueError("Model type is required")

        if not self.artifact_path:
            raise ValueError("Artifact path is required")

        valid_statuses = ["training", "staging", "production", "archived"]
        if self.status not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")

    def promote_to_staging(self) -> None:
        """Promote model from training to staging."""
        if self.status != "training":
            raise ValueError("Can only promote from training status")
        self.status = "staging"

    def promote_to_production(self) -> None:
        """Promote model from staging to production."""
        if self.status != "staging":
            raise ValueError("Can only promote from staging status")
        self.status = "production"

    def archive(self) -> None:
        """Archive this model (no longer in use)."""
        self.status = "archived"

    @property
    def is_production(self) -> bool:
        """Check if model is in production."""
        return self.status == "production"

    @property
    def is_archived(self) -> bool:
        """Check if model is archived."""
        return self.status == "archived"

    def get_metric(self, metric_name: str) -> float | None:
        """Get a specific metric value."""
        return self.metrics.get(metric_name)
