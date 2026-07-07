"""Alert Status Enumeration."""

from enum import StrEnum


class AlertStatus(StrEnum):
    """Status of a fraud alert.

    Attributes:
        OPEN: Alert created, awaiting review
        IN_REVIEW: Alert being investigated by analyst
        RESOLVED: Alert investigation completed
        FALSE_POSITIVE: Alert determined to be false positive
        CONFIRMED_FRAUD: Alert confirmed as actual fraud
        ESCALATED: Alert escalated to higher tier
    """

    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    CONFIRMED_FRAUD = "confirmed_fraud"
    ESCALATED = "escalated"

    def is_closed(self) -> bool:
        """Check if alert is closed.

        Returns:
            True if alert is in terminal state
        """
        return self in {
            AlertStatus.RESOLVED,
            AlertStatus.FALSE_POSITIVE,
            AlertStatus.CONFIRMED_FRAUD,
        }

    def requires_action(self) -> bool:
        """Check if alert requires action.

        Returns:
            True if alert needs analyst attention
        """
        return self in {
            AlertStatus.OPEN,
            AlertStatus.IN_REVIEW,
            AlertStatus.ESCALATED,
        }
