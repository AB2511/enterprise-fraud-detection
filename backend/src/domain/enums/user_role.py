"""User Role Enumeration."""

from enum import Enum


class UserRole(str, Enum):
    """Role of a system user.

    Attributes:
        ADMIN: System administrator with full access
        ANALYST: Fraud analyst who reviews alerts
        DATA_SCIENTIST: Data scientist who trains models
        AUDITOR: Auditor with read-only access
        VIEWER: Read-only viewer
    """

    ADMIN = "admin"
    ANALYST = "analyst"
    DATA_SCIENTIST = "data_scientist"
    AUDITOR = "auditor"
    VIEWER = "viewer"

    def can_review_alerts(self) -> bool:
        """Check if role can review fraud alerts.

        Returns:
            True if can review alerts
        """
        return self in {UserRole.ADMIN, UserRole.ANALYST}

    def can_train_models(self) -> bool:
        """Check if role can train ML models.

        Returns:
            True if can train models
        """
        return self in {UserRole.ADMIN, UserRole.DATA_SCIENTIST}

    def can_manage_users(self) -> bool:
        """Check if role can manage other users.

        Returns:
            True if can manage users
        """
        return self == UserRole.ADMIN

    def get_permissions(self) -> set[str]:
        """Get list of permissions for role.

        Returns:
            Set of permission strings
        """
        permissions_map = {
            UserRole.ADMIN: {
                "read",
                "write",
                "delete",
                "manage_users",
                "review_alerts",
                "train_models",
                "audit",
            },
            UserRole.ANALYST: {"read", "review_alerts", "write_feedback"},
            UserRole.DATA_SCIENTIST: {"read", "train_models", "write_models"},
            UserRole.AUDITOR: {"read", "audit"},
            UserRole.VIEWER: {"read"},
        }
        return permissions_map[self]
