"""AuditLog Entity - Immutable audit trail for all system changes."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class AuditLog:
    """Immutable audit log entry for tracking system changes.

    AuditLog records all create, update, and delete operations for regulatory
    compliance and forensic analysis. Entries are immutable and append-only.

    Attributes:
        audit_id: Unique identifier
        entity_type: Type of entity being audited (e.g., "customer", "transaction")
        entity_id: ID of the entity being audited
        action: Action performed (CREATE, UPDATE, DELETE)
        user_id: ID of user who performed the action
        username: Username for display purposes
        old_value: Previous state (None for CREATE)
        new_value: New state (None for DELETE)
        ip_address: IP address of the requestor
        user_agent: User agent string
        description: Human-readable description
        created_at: Timestamp of the audit event
    """

    audit_id: UUID = field(default_factory=uuid4)
    entity_type: str = field(default="")
    entity_id: UUID = field(default_factory=uuid4)
    action: str = field(default="")
    user_id: UUID | None = field(default=None)
    username: str | None = field(default=None)
    old_value: dict[str, Any] | None = field(default=None)
    new_value: dict[str, Any] | None = field(default=None)
    ip_address: str | None = field(default=None)
    user_agent: str | None = field(default=None)
    description: str | None = field(default=None)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate audit log business rules."""
        if not self.entity_type:
            raise ValueError("Entity type is required")

        if not self.action:
            raise ValueError("Action is required")

        valid_actions = ["CREATE", "UPDATE", "DELETE", "READ", "EXPORT"]
        if self.action not in valid_actions:
            raise ValueError(f"Action must be one of: {valid_actions}")

        # Validate action-specific requirements
        if self.action == "CREATE" and self.old_value is not None:
            raise ValueError("CREATE action cannot have old_value")

        if self.action == "DELETE" and self.new_value is not None:
            raise ValueError("DELETE action cannot have new_value")

        if self.action == "UPDATE":
            if self.old_value is None or self.new_value is None:
                raise ValueError("UPDATE action requires both old_value and new_value")

    @classmethod
    def for_creation(
        cls,
        entity_type: str,
        entity_id: UUID,
        user_id: UUID | None = None,
        username: str | None = None,
        new_value: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        description: str | None = None,
    ) -> "AuditLog":
        """Create an audit log entry for entity creation.

        Args:
            entity_type: Type of entity (e.g., "customer", "transaction")
            entity_id: ID of the created entity
            user_id: ID of user who created the entity
            username: Username for display
            new_value: New entity state
            ip_address: Client IP address
            user_agent: Client user agent
            description: Optional description

        Returns:
            AuditLog instance for creation event
        """
        return cls(
            entity_type=entity_type,
            entity_id=entity_id,
            action="CREATE",
            user_id=user_id,
            username=username or "system",
            old_value=None,
            new_value=new_value or {},
            ip_address=ip_address,
            user_agent=user_agent,
            description=description or f"Created {entity_type} {entity_id}",
        )

    @classmethod
    def for_update(
        cls,
        entity_type: str,
        entity_id: UUID,
        old_value: dict[str, Any],
        new_value: dict[str, Any],
        user_id: UUID | None = None,
        username: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        description: str | None = None,
    ) -> "AuditLog":
        """Create an audit log entry for entity update.

        Args:
            entity_type: Type of entity (e.g., "customer", "transaction")
            entity_id: ID of the updated entity
            old_value: Previous entity state
            new_value: New entity state
            user_id: ID of user who updated the entity
            username: Username for display
            ip_address: Client IP address
            user_agent: Client user agent
            description: Optional description

        Returns:
            AuditLog instance for update event
        """
        return cls(
            entity_type=entity_type,
            entity_id=entity_id,
            action="UPDATE",
            user_id=user_id,
            username=username or "system",
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description or f"Updated {entity_type} {entity_id}",
        )

    @classmethod
    def for_deletion(
        cls,
        entity_type: str,
        entity_id: UUID,
        old_value: dict[str, Any],
        user_id: UUID | None = None,
        username: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        description: str | None = None,
    ) -> "AuditLog":
        """Create an audit log entry for entity deletion.

        Args:
            entity_type: Type of entity (e.g., "customer", "transaction")
            entity_id: ID of the deleted entity
            old_value: Previous entity state
            user_id: ID of user who deleted the entity
            username: Username for display
            ip_address: Client IP address
            user_agent: Client user agent
            description: Optional description

        Returns:
            AuditLog instance for deletion event
        """
        return cls(
            entity_type=entity_type,
            entity_id=entity_id,
            action="DELETE",
            user_id=user_id,
            username=username or "system",
            old_value=old_value,
            new_value=None,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description or f"Deleted {entity_type} {entity_id}",
        )

    @classmethod
    def for_read(
        cls,
        entity_type: str,
        entity_id: UUID,
        user_id: UUID | None = None,
        username: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        description: str | None = None,
    ) -> "AuditLog":
        """Create an audit log entry for sensitive entity read operations.

        Args:
            entity_type: Type of entity (e.g., "customer", "transaction")
            entity_id: ID of the read entity
            user_id: ID of user who read the entity
            username: Username for display
            ip_address: Client IP address
            user_agent: Client user agent
            description: Optional description

        Returns:
            AuditLog instance for read event
        """
        return cls(
            entity_type=entity_type,
            entity_id=entity_id,
            action="READ",
            user_id=user_id,
            username=username or "system",
            old_value=None,
            new_value=None,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description or f"Read {entity_type} {entity_id}",
        )

    @classmethod
    def for_export(
        cls,
        entity_type: str,
        entity_id: UUID,
        user_id: UUID | None = None,
        username: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        description: str | None = None,
    ) -> "AuditLog":
        """Create an audit log entry for data export operations.

        Args:
            entity_type: Type of entity (e.g., "customer", "transaction")
            entity_id: ID referencing the export operation
            user_id: ID of user who performed the export
            username: Username for display
            ip_address: Client IP address
            user_agent: Client user agent
            description: Optional description

        Returns:
            AuditLog instance for export event
        """
        return cls(
            entity_type=entity_type,
            entity_id=entity_id,
            action="EXPORT",
            user_id=user_id,
            username=username or "system",
            old_value=None,
            new_value=None,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description or f"Exported {entity_type} data",
        )
