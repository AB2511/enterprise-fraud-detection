"""Unit Tests for AuditLog Entity."""

from datetime import datetime
from uuid import uuid4

import pytest
from src.domain.entities.audit_log import AuditLog


class TestAuditLogCreation:
    """Test AuditLog entity creation."""

    def test_for_creation_factory_method(self):
        """Test creating audit log for entity creation."""
        entity_id = uuid4()
        user_id = uuid4()

        audit = AuditLog.for_creation(
            entity_type="customer",
            entity_id=entity_id,
            user_id=user_id,
            username="john.doe",
            new_value={"name": "John Doe", "email": "john@example.com"},
            ip_address="192.168.1.1",
        )

        assert audit.entity_type == "customer"
        assert audit.entity_id == entity_id
        assert audit.action == "CREATE"
        assert audit.user_id == user_id
        assert audit.username == "john.doe"
        assert audit.old_value is None
        assert audit.new_value == {"name": "John Doe", "email": "john@example.com"}
        assert audit.ip_address == "192.168.1.1"
        assert isinstance(audit.created_at, datetime)

    def test_for_update_factory_method(self):
        """Test creating audit log for entity update."""
        entity_id = uuid4()
        user_id = uuid4()

        audit = AuditLog.for_update(
            entity_type="customer",
            entity_id=entity_id,
            old_value={"name": "John Doe", "email": "john@example.com"},
            new_value={"name": "John Smith", "email": "john@example.com"},
            user_id=user_id,
            username="admin",
        )

        assert audit.entity_type == "customer"
        assert audit.action == "UPDATE"
        assert audit.old_value == {"name": "John Doe", "email": "john@example.com"}
        assert audit.new_value == {"name": "John Smith", "email": "john@example.com"}

    def test_for_deletion_factory_method(self):
        """Test creating audit log for entity deletion."""
        entity_id = uuid4()
        user_id = uuid4()

        audit = AuditLog.for_deletion(
            entity_type="customer",
            entity_id=entity_id,
            old_value={"name": "John Doe", "email": "john@example.com"},
            user_id=user_id,
            username="admin",
        )

        assert audit.entity_type == "customer"
        assert audit.action == "DELETE"
        assert audit.old_value == {"name": "John Doe", "email": "john@example.com"}
        assert audit.new_value is None

    def test_for_read_factory_method(self):
        """Test creating audit log for entity read."""
        entity_id = uuid4()
        user_id = uuid4()

        audit = AuditLog.for_read(
            entity_type="customer",
            entity_id=entity_id,
            user_id=user_id,
            username="analyst",
        )

        assert audit.entity_type == "customer"
        assert audit.action == "READ"
        assert audit.old_value is None
        assert audit.new_value is None

    def test_for_export_factory_method(self):
        """Test creating audit log for data export."""
        entity_id = uuid4()
        user_id = uuid4()

        audit = AuditLog.for_export(
            entity_type="customer",
            entity_id=entity_id,
            user_id=user_id,
            username="analyst",
            description="Exported customer data for compliance report",
        )

        assert audit.entity_type == "customer"
        assert audit.action == "EXPORT"
        assert audit.description == "Exported customer data for compliance report"


class TestAuditLogValidation:
    """Test AuditLog validation rules."""

    def test_entity_type_required(self):
        """Test that entity_type is required."""
        with pytest.raises(ValueError, match="Entity type is required"):
            AuditLog(
                entity_type="",
                entity_id=uuid4(),
                action="CREATE",
            )

    def test_action_required(self):
        """Test that action is required."""
        with pytest.raises(ValueError, match="Action is required"):
            AuditLog(
                entity_type="customer",
                entity_id=uuid4(),
                action="",
            )

    def test_invalid_action(self):
        """Test that invalid actions are rejected."""
        with pytest.raises(ValueError, match="Action must be one of"):
            AuditLog(
                entity_type="customer",
                entity_id=uuid4(),
                action="INVALID",
            )

    def test_create_cannot_have_old_value(self):
        """Test that CREATE action cannot have old_value."""
        with pytest.raises(ValueError, match="CREATE action cannot have old_value"):
            AuditLog(
                entity_type="customer",
                entity_id=uuid4(),
                action="CREATE",
                old_value={"name": "test"},
                new_value={"name": "test"},
            )

    def test_delete_cannot_have_new_value(self):
        """Test that DELETE action cannot have new_value."""
        with pytest.raises(ValueError, match="DELETE action cannot have new_value"):
            AuditLog(
                entity_type="customer",
                entity_id=uuid4(),
                action="DELETE",
                old_value={"name": "test"},
                new_value={"name": "test"},
            )

    def test_update_requires_both_values(self):
        """Test that UPDATE action requires both old_value and new_value."""
        with pytest.raises(ValueError, match="UPDATE action requires both old_value and new_value"):
            AuditLog(
                entity_type="customer",
                entity_id=uuid4(),
                action="UPDATE",
                old_value={"name": "test"},
                new_value=None,
            )


class TestAuditLogImmutability:
    """Test that AuditLog is immutable."""

    def test_audit_log_is_frozen(self):
        """Test that AuditLog cannot be modified after creation."""
        audit = AuditLog.for_creation(
            entity_type="customer",
            entity_id=uuid4(),
            new_value={"name": "John Doe"},
        )

        # Attempt to modify should raise FrozenInstanceError
        with pytest.raises(
            (AttributeError, TypeError)
        ):  # dataclasses.FrozenInstanceError in Python 3.11+
            audit.action = "UPDATE"

    def test_default_username_is_system(self):
        """Test that default username is 'system'."""
        audit = AuditLog.for_creation(
            entity_type="customer",
            entity_id=uuid4(),
            new_value={"name": "John Doe"},
        )

        assert audit.username == "system"

    def test_description_auto_generated(self):
        """Test that description is auto-generated if not provided."""
        entity_id = uuid4()
        audit = AuditLog.for_creation(
            entity_type="customer",
            entity_id=entity_id,
            new_value={"name": "John Doe"},
        )

        assert f"Created customer {entity_id}" in audit.description
