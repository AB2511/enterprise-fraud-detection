"""Model Status Enumeration."""

from enum import StrEnum


class ModelStatus(StrEnum):
    """Model deployment lifecycle status."""

    TRAINING = "training"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    @property
    def is_active(self) -> bool:
        """Check if model is in active use."""
        return self in (ModelStatus.STAGING, ModelStatus.PRODUCTION)

    @property
    def can_promote(self) -> bool:
        """Check if model can be promoted to next stage."""
        return self in (ModelStatus.TRAINING, ModelStatus.STAGING)
