"""Customer Status Enumeration."""

from enum import Enum


class CustomerStatus(str, Enum):
    """Status of a customer account.

    Attributes:
        ACTIVE: Account is active and operational
        INACTIVE: Account temporarily inactive
        SUSPENDED: Account suspended due to fraud or compliance
        CLOSED: Account permanently closed
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CLOSED = "closed"

    def can_transact(self) -> bool:
        """Check if customer can make transactions.

        Returns:
            True if customer can transact
        """
        return self == CustomerStatus.ACTIVE

    def is_operational(self) -> bool:
        """Check if account is operational.

        Returns:
            True if account can be used
        """
        return self in {CustomerStatus.ACTIVE, CustomerStatus.INACTIVE}
