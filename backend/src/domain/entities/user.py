"""User Entity - System user (analyst, admin, etc.)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from passlib.hash import bcrypt


@dataclass
class User:
    """User entity representing a system user (analyst, data scientist, admin).

    Users authenticate to the system and perform fraud analysis activities.

    Attributes:
        user_id: Unique identifier
        email: User email address (unique)
        hashed_password: Bcrypt hashed password
        role: User role (admin, analyst, data_scientist, auditor)
        status: Account status (active, inactive, locked)
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        last_login: Last login timestamp
    """

    user_id: UUID = field(default_factory=uuid4)
    email: str = ""
    hashed_password: str = ""
    role: str = "analyst"
    status: str = "active"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_login: datetime | None = None

    def __post_init__(self) -> None:
        """Validate user business rules."""
        if not self.email or "@" not in self.email:
            raise ValueError("Valid email address is required")

        valid_roles = ["admin", "analyst", "data_scientist", "auditor"]
        if self.role not in valid_roles:
            raise ValueError(f"Role must be one of: {valid_roles}")

        valid_statuses = ["active", "inactive", "locked"]
        if self.status not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")

    @classmethod
    def create(cls, email: str, password: str, role: str = "analyst") -> "User":
        """Create new user with hashed password.

        Args:
            email: User email
            password: Plain text password
            role: User role

        Returns:
            New User instance
        """
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        hashed = bcrypt.hash(password)
        return cls(email=email, hashed_password=hashed, role=role)

    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash.

        Args:
            password: Plain text password to verify

        Returns:
            True if password matches, False otherwise
        """
        if not self.hashed_password:
            return False
        return bcrypt.verify(password, self.hashed_password)

    def change_password(self, old_password: str, new_password: str) -> None:
        """Change user password.

        Args:
            old_password: Current password
            new_password: New password

        Raises:
            ValueError: If old password is incorrect or new password is invalid
        """
        if not self.verify_password(old_password):
            raise ValueError("Current password is incorrect")

        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters")

        self.hashed_password = bcrypt.hash(new_password)
        self.updated_at = datetime.now(UTC)

    def activate(self) -> None:
        """Activate user account."""
        self.status = "active"
        self.updated_at = datetime.now(UTC)

    def deactivate(self) -> None:
        """Deactivate user account."""
        self.status = "inactive"
        self.updated_at = datetime.now(UTC)

    def lock(self) -> None:
        """Lock user account (due to security concerns)."""
        self.status = "locked"
        self.updated_at = datetime.now(UTC)

    def assign_role(self, new_role: str) -> None:
        """Assign new role to user.

        Args:
            new_role: New role to assign

        Raises:
            ValueError: If role is invalid
        """
        valid_roles = ["admin", "analyst", "data_scientist", "auditor"]
        if new_role not in valid_roles:
            raise ValueError(f"Role must be one of: {valid_roles}")

        self.role = new_role
        self.updated_at = datetime.now(UTC)

    def record_login(self) -> None:
        """Record successful login."""
        self.last_login = datetime.now(UTC)

    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == "active"

    @property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        return self.status == "locked"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"

    @property
    def can_review_alerts(self) -> bool:
        """Check if user can review fraud alerts."""
        return self.is_active and self.role in ["admin", "analyst"]

    @property
    def can_manage_models(self) -> bool:
        """Check if user can manage ML models."""
        return self.is_active and self.role in ["admin", "data_scientist"]
