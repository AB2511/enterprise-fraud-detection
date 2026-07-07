"""Alert Severity Enumeration."""

from enum import Enum


class AlertSeverity(str, Enum):
    """Severity level of a fraud alert.

    Attributes:
        LOW: Low risk, routine review
        MEDIUM: Moderate risk, standard priority
        HIGH: High risk, requires prompt attention
        CRITICAL: Critical risk, immediate action required
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def get_priority_score(self) -> int:
        """Get numeric priority score for sorting.

        Returns:
            Priority score (higher = more urgent)
        """
        priority_map = {
            AlertSeverity.LOW: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.HIGH: 3,
            AlertSeverity.CRITICAL: 4,
        }
        return priority_map[self]

    def get_sla_hours(self) -> int:
        """Get SLA response time in hours.

        Returns:
            Hours until SLA breach
        """
        sla_map = {
            AlertSeverity.CRITICAL: 1,
            AlertSeverity.HIGH: 4,
            AlertSeverity.MEDIUM: 24,
            AlertSeverity.LOW: 72,
        }
        return sla_map[self]
