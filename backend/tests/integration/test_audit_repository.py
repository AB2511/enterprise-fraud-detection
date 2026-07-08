"""Integration tests for AuditRepositoryImpl."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.audit_log import AuditLog
from src.infrastructure.database.repositories.audit_repository_impl import AuditRepositoryImpl


@pytest.fixture
def audit_repository(async_session: AsyncSession) -> AuditRepositoryImpl:
    """Create audit repository instance."""
    return AuditRepositoryImpl(async_session)


@pytest.fixture
def sample_audit_log() -> AuditLog:
    """Create sample audit log for testing."""
    return AuditLog.for_creation(
        entity_type="transaction",
        entity_id=uuid4(),
        user_id=uuid4(),
        username="test_user",
        new_value={"amount": 100.0, "merchant": "Test Store"},
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        description="Created transaction",
    )


class TestAuditRepositoryCreate:
    """Test audit log creation operations."""

    async def test_create_audit_log_success(
        self,
        audit_repository: AuditRepositoryImpl,
        sample_audit_log: AuditLog,
        async_session: AsyncSession,
    ):
        """Test successful audit log creation."""
        result = await audit_repository.create(sample_audit_log)
        await async_session.commit()

        assert result.audit_id == sample_audit_log.audit_id
        assert result.entity_type == sample_audit_log.entity_type
        assert result.entity_id == sample_audit_log.entity_id
        assert result.action == sample_audit_log.action
        assert result.user_id == sample_audit_log.user_id

    async def test_create_audit_log_for_creation(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test audit log creation for CREATE action."""
        entity_id = uuid4()
        user_id = uuid4()

        audit_log = AuditLog.for_creation(
            entity_type="customer",
            entity_id=entity_id,
            user_id=user_id,
            username="admin",
            new_value={"name": "John Doe", "email": "john@example.com"},
            ip_address="10.0.0.1",
            user_agent="Chrome/91.0",
            description="New customer registration",
        )

        result = await audit_repository.create(audit_log)
        await async_session.commit()

        assert result.action == "CREATE"
        assert result.old_value is None
        assert result.new_value is not None
        assert result.new_value["name"] == "John Doe"

    async def test_create_audit_log_for_update(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test audit log creation for UPDATE action."""
        entity_id = uuid4()
        user_id = uuid4()

        audit_log = AuditLog.for_update(
            entity_type="merchant",
            entity_id=entity_id,
            old_value={"status": "pending", "risk_score": 50},
            new_value={"status": "active", "risk_score": 75},
            user_id=user_id,
            username="analyst",
            ip_address="172.16.0.1",
            user_agent="Firefox/89.0",
            description="Updated merchant status",
        )

        result = await audit_repository.create(audit_log)
        await async_session.commit()

        assert result.action == "UPDATE"
        assert result.old_value is not None
        assert result.new_value is not None
        assert result.old_value["status"] == "pending"
        assert result.new_value["status"] == "active"

    async def test_create_audit_log_for_deletion(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test audit log creation for DELETE action."""
        entity_id = uuid4()
        user_id = uuid4()

        audit_log = AuditLog.for_deletion(
            entity_type="alert",
            entity_id=entity_id,
            old_value={"status": "open", "severity": "high"},
            user_id=user_id,
            username="supervisor",
            ip_address="192.168.0.100",
            user_agent="Safari/14.0",
            description="Deleted false alert",
        )

        result = await audit_repository.create(audit_log)
        await async_session.commit()

        assert result.action == "DELETE"
        assert result.old_value is not None
        assert result.new_value is None
        assert result.old_value["status"] == "open"

    async def test_create_audit_log_for_read(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test audit log creation for READ action."""
        entity_id = uuid4()
        user_id = uuid4()

        audit_log = AuditLog.for_read(
            entity_type="customer",
            entity_id=entity_id,
            user_id=user_id,
            username="viewer",
            ip_address="203.0.113.1",
            user_agent="Edge/91.0",
            description="Accessed customer profile",
        )

        result = await audit_repository.create(audit_log)
        await async_session.commit()

        assert result.action == "READ"
        assert result.old_value is None
        assert result.new_value is None

    async def test_create_audit_log_for_export(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test audit log creation for EXPORT action."""
        entity_id = uuid4()
        user_id = uuid4()

        audit_log = AuditLog.for_export(
            entity_type="transaction",
            entity_id=entity_id,
            user_id=user_id,
            username="compliance_officer",
            ip_address="198.51.100.1",
            user_agent="Chrome/92.0",
            description="Exported transaction data for audit",
        )

        result = await audit_repository.create(audit_log)
        await async_session.commit()

        assert result.action == "EXPORT"
        assert result.old_value is None
        assert result.new_value is None


class TestAuditRepositoryRead:
    """Test audit log retrieval operations."""

    async def test_get_by_id_success(
        self,
        audit_repository: AuditRepositoryImpl,
        sample_audit_log: AuditLog,
        async_session: AsyncSession,
    ):
        """Test successful audit log retrieval by ID."""
        created = await audit_repository.create(sample_audit_log)
        await async_session.commit()

        result = await audit_repository.get_by_id(created.audit_id)

        assert result is not None
        assert result.audit_id == sample_audit_log.audit_id
        assert result.entity_type == sample_audit_log.entity_type

    async def test_get_by_id_not_found(self, audit_repository: AuditRepositoryImpl):
        """Test audit log retrieval with non-existent ID."""
        result = await audit_repository.get_by_id(uuid4())
        assert result is None


class TestAuditRepositoryListing:
    """Test audit log listing operations."""

    @pytest.fixture
    async def multiple_audit_logs(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ) -> list[AuditLog]:
        """Create multiple audit logs for listing tests."""
        entity_id = uuid4()
        user1_id = uuid4()
        user2_id = uuid4()

        audit_logs = [
            # Transaction creation
            AuditLog.for_creation(
                entity_type="transaction",
                entity_id=entity_id,
                user_id=user1_id,
                username="customer",
                new_value={"amount": 500.0, "merchant": "Online Store"},
                ip_address="192.168.1.100",
                user_agent="Chrome/91.0",
                description="Customer initiated transaction",
            ),
            # Transaction update (fraud review)
            AuditLog.for_update(
                entity_type="transaction",
                entity_id=entity_id,
                old_value={"status": "pending", "risk_score": 45},
                new_value={"status": "under_review", "risk_score": 85},
                user_id=user2_id,
                username="fraud_analyst",
                ip_address="10.0.0.50",
                user_agent="Firefox/89.0",
                description="Flagged transaction for manual review",
            ),
            # Customer read access
            AuditLog.for_read(
                entity_type="customer",
                entity_id=uuid4(),
                user_id=user2_id,
                username="fraud_analyst",
                ip_address="10.0.0.50",
                user_agent="Firefox/89.0",
                description="Accessed customer profile during investigation",
            ),
            # Data export
            AuditLog.for_export(
                entity_type="transaction",
                entity_id=uuid4(),
                user_id=uuid4(),
                username="compliance_officer",
                ip_address="172.16.1.1",
                user_agent="Safari/14.0",
                description="Exported transaction data for regulatory report",
            ),
            # Alert deletion
            AuditLog.for_deletion(
                entity_type="alert",
                entity_id=uuid4(),
                old_value={"status": "resolved", "resolution": "false_positive"},
                user_id=user1_id,
                username="supervisor",
                ip_address="192.168.1.200",
                user_agent="Edge/91.0",
                description="Removed obsolete alert",
            ),
        ]

        created_logs = []
        for audit_log in audit_logs:
            created = await audit_repository.create(audit_log)
            created_logs.append(created)

        await async_session.commit()
        return created_logs

    async def test_list_by_entity(
        self,
        audit_repository: AuditRepositoryImpl,
        multiple_audit_logs: list[AuditLog],
    ):
        """Test listing audit logs for specific entity."""
        # Find a transaction entity that has multiple logs
        transaction_logs = [log for log in multiple_audit_logs if log.entity_type == "transaction"]
        if transaction_logs:
            entity_id = transaction_logs[0].entity_id
            result = await audit_repository.list_by_entity("transaction", entity_id)

            # Should find at least one log for this transaction
            assert len(result) >= 1
            for log in result:
                assert log.entity_type == "transaction"
                assert log.entity_id == entity_id

    async def test_list_by_user(
        self,
        audit_repository: AuditRepositoryImpl,
        multiple_audit_logs: list[AuditLog],
    ):
        """Test listing audit logs by user."""
        # Get a user who has audit logs
        user_log = next(log for log in multiple_audit_logs if log.user_id is not None)
        user_id = user_log.user_id

        result = await audit_repository.list_by_user(user_id)

        # Should find at least one log for this user
        assert len(result) >= 1
        for log in result:
            assert log.user_id == user_id

    async def test_list_by_action(
        self,
        audit_repository: AuditRepositoryImpl,
        multiple_audit_logs: list[AuditLog],
    ):
        """Test listing audit logs by action type."""
        create_logs = await audit_repository.list_by_action("CREATE")
        update_logs = await audit_repository.list_by_action("UPDATE")
        delete_logs = await audit_repository.list_by_action("DELETE")
        read_logs = await audit_repository.list_by_action("READ")
        export_logs = await audit_repository.list_by_action("EXPORT")

        assert len(create_logs) >= 1
        assert len(update_logs) >= 1
        assert len(delete_logs) >= 1
        assert len(read_logs) >= 1
        assert len(export_logs) >= 1

        # Verify action types
        for log in create_logs:
            assert log.action == "CREATE"
        for log in update_logs:
            assert log.action == "UPDATE"

    async def test_list_by_date_range(
        self,
        audit_repository: AuditRepositoryImpl,
        multiple_audit_logs: list[AuditLog],
    ):
        """Test listing audit logs within date range."""
        start_date = datetime.now(UTC) - timedelta(hours=1)
        end_date = datetime.now(UTC) + timedelta(hours=1)

        result = await audit_repository.list_by_date_range(start_date, end_date)

        # Should find all created logs within range
        assert len(result) >= len(multiple_audit_logs)
        for log in result:
            assert start_date <= log.created_at <= end_date


class TestAuditRepositorySearch:
    """Test audit log search operations."""

    @pytest.fixture
    async def multiple_audit_logs(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ) -> list[AuditLog]:
        """Create multiple audit logs for search tests."""
        entity_id = uuid4()
        user1_id = uuid4()
        user2_id = uuid4()

        audit_logs = [
            # Transaction creation
            AuditLog.for_creation(
                entity_type="transaction",
                entity_id=entity_id,
                user_id=user1_id,
                username="customer",
                new_value={"amount": 500.0, "merchant": "Online Store"},
                ip_address="192.168.1.100",
                user_agent="Chrome/91.0",
                description="Customer initiated transaction",
            ),
            # Transaction update (fraud review)
            AuditLog.for_update(
                entity_type="transaction",
                entity_id=entity_id,
                old_value={"status": "pending", "risk_score": 45},
                new_value={"status": "under_review", "risk_score": 85},
                user_id=user2_id,
                username="fraud_analyst",
                ip_address="10.0.0.50",
                user_agent="Firefox/89.0",
                description="Flagged transaction for manual review",
            ),
            # Customer read access
            AuditLog.for_read(
                entity_type="customer",
                entity_id=uuid4(),
                user_id=user2_id,
                username="fraud_analyst",
                ip_address="10.0.0.50",
                user_agent="Firefox/89.0",
                description="Accessed customer profile during investigation",
            ),
        ]

        created_logs = []
        for audit_log in audit_logs:
            created = await audit_repository.create(audit_log)
            created_logs.append(created)

        await async_session.commit()
        return created_logs

    async def test_search_comprehensive(
        self,
        audit_repository: AuditRepositoryImpl,
        multiple_audit_logs: list[AuditLog],
    ):
        """Test comprehensive search with multiple filters."""
        # Search for transaction updates
        result = await audit_repository.search(entity_type="transaction", action="UPDATE")

        assert len(result) >= 1
        for log in result:
            assert log.entity_type == "transaction"
            assert log.action == "UPDATE"

    async def test_search_by_user_and_date(
        self,
        audit_repository: AuditRepositoryImpl,
        multiple_audit_logs: list[AuditLog],
    ):
        """Test search by user and date range."""
        user_log = next(log for log in multiple_audit_logs if log.user_id is not None)
        user_id = user_log.user_id

        start_date = datetime.now(UTC) - timedelta(hours=1)
        end_date = datetime.now(UTC) + timedelta(hours=1)

        result = await audit_repository.search(
            user_id=user_id, start_date=start_date, end_date=end_date
        )

        assert len(result) >= 1
        for log in result:
            assert log.user_id == user_id
            assert start_date <= log.created_at <= end_date

    async def test_search_no_filters(
        self,
        audit_repository: AuditRepositoryImpl,
        multiple_audit_logs: list[AuditLog],
    ):
        """Test search without filters (returns all)."""
        result = await audit_repository.search()

        # Should return all audit logs
        assert len(result) >= len(multiple_audit_logs)

    async def test_search_no_results(
        self,
        audit_repository: AuditRepositoryImpl,
    ):
        """Test search with filters that return no results."""
        result = await audit_repository.search(
            entity_type="nonexistent_type", action="INVALID_ACTION"
        )

        assert len(result) == 0


class TestAuditRepositoryCount:
    """Test audit log counting operations."""

    @pytest.fixture
    async def multiple_audit_logs(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ) -> list[AuditLog]:
        """Create multiple audit logs for count tests."""
        entity_id = uuid4()
        user1_id = uuid4()

        audit_logs = [
            # Transaction creation
            AuditLog.for_creation(
                entity_type="transaction",
                entity_id=entity_id,
                user_id=user1_id,
                username="customer",
                new_value={"amount": 500.0, "merchant": "Online Store"},
                ip_address="192.168.1.100",
                user_agent="Chrome/91.0",
                description="Customer initiated transaction",
            ),
            # Transaction update
            AuditLog.for_update(
                entity_type="transaction",
                entity_id=entity_id,
                old_value={"status": "pending", "risk_score": 45},
                new_value={"status": "under_review", "risk_score": 85},
                user_id=user1_id,
                username="fraud_analyst",
                ip_address="10.0.0.50",
                user_agent="Firefox/89.0",
                description="Flagged transaction for manual review",
            ),
        ]

        created_logs = []
        for audit_log in audit_logs:
            created = await audit_repository.create(audit_log)
            created_logs.append(created)

        await async_session.commit()
        return created_logs

    async def test_count_by_entity(
        self,
        audit_repository: AuditRepositoryImpl,
        multiple_audit_logs: list[AuditLog],
    ):
        """Test counting audit logs for specific entity."""
        # Find an entity with logs
        transaction_logs = [log for log in multiple_audit_logs if log.entity_type == "transaction"]
        if transaction_logs:
            entity_id = transaction_logs[0].entity_id
            count = await audit_repository.count_by_entity("transaction", entity_id)

            # Should count at least one log for this entity
            assert count >= 1

    async def test_count_by_entity_no_results(
        self,
        audit_repository: AuditRepositoryImpl,
    ):
        """Test counting audit logs for non-existent entity."""
        count = await audit_repository.count_by_entity("nonexistent", uuid4())
        assert count == 0


class TestAuditRepositoryAnalytics:
    """Test audit analytics and statistics operations."""

    @pytest.fixture
    async def multiple_audit_logs(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ) -> list[AuditLog]:
        """Create multiple audit logs for analytics tests."""
        entity_id = uuid4()
        user1_id = uuid4()
        user2_id = uuid4()

        audit_logs = [
            # Transaction creation
            AuditLog.for_creation(
                entity_type="transaction",
                entity_id=entity_id,
                user_id=user1_id,
                username="customer",
                new_value={"amount": 500.0, "merchant": "Online Store"},
                ip_address="192.168.1.100",
                user_agent="Chrome/91.0",
                description="Customer initiated transaction",
            ),
            # Transaction update
            AuditLog.for_update(
                entity_type="transaction",
                entity_id=entity_id,
                old_value={"status": "pending", "risk_score": 45},
                new_value={"status": "under_review", "risk_score": 85},
                user_id=user2_id,
                username="fraud_analyst",
                ip_address="10.0.0.50",
                user_agent="Firefox/89.0",
                description="Flagged transaction for manual review",
            ),
            # Customer read access
            AuditLog.for_read(
                entity_type="customer",
                entity_id=uuid4(),
                user_id=user1_id,
                username="customer_service",
                ip_address="192.168.1.200",
                user_agent="Chrome/92.0",
                description="Customer service accessed profile",
            ),
        ]

        created_logs = []
        for audit_log in audit_logs:
            created = await audit_repository.create(audit_log)
            created_logs.append(created)

        await async_session.commit()
        return created_logs

    async def test_get_audit_trail_summary(
        self,
        audit_repository: AuditRepositoryImpl,
        multiple_audit_logs: list[AuditLog],
    ):
        """Test getting audit trail summary for an entity."""
        # Find an entity with multiple operations
        transaction_logs = [log for log in multiple_audit_logs if log.entity_type == "transaction"]
        if transaction_logs:
            entity_id = transaction_logs[0].entity_id

            summary = await audit_repository.get_audit_trail_summary("transaction", entity_id)

            assert summary["total_events"] >= 1
            assert summary["unique_users"] >= 1
            assert summary["first_event"] is not None
            assert summary["last_event"] is not None
            assert isinstance(summary["create_count"], int)
            assert isinstance(summary["update_count"], int)
            assert isinstance(summary["delete_count"], int)
            assert isinstance(summary["read_count"], int)

    async def test_get_audit_trail_summary_no_data(
        self,
        audit_repository: AuditRepositoryImpl,
    ):
        """Test audit trail summary with no data."""
        summary = await audit_repository.get_audit_trail_summary("nonexistent", uuid4())

        assert summary["total_events"] == 0
        assert summary["unique_users"] == 0
        assert summary["first_event"] is None
        assert summary["last_event"] is None
        assert summary["create_count"] == 0

    async def test_get_user_activity_summary(
        self,
        audit_repository: AuditRepositoryImpl,
        multiple_audit_logs: list[AuditLog],
    ):
        """Test getting user activity summary."""
        user_log = next(log for log in multiple_audit_logs if log.user_id is not None)
        user_id = user_log.user_id

        summary = await audit_repository.get_user_activity_summary(user_id)

        assert summary["total_actions"] >= 1
        assert summary["entity_types"] >= 1
        assert isinstance(summary["create_count"], int)
        assert isinstance(summary["update_count"], int)
        assert isinstance(summary["delete_count"], int)
        assert isinstance(summary["read_count"], int)

    async def test_get_user_activity_summary_with_date_range(
        self,
        audit_repository: AuditRepositoryImpl,
        multiple_audit_logs: list[AuditLog],
    ):
        """Test user activity summary with date filtering."""
        user_log = next(log for log in multiple_audit_logs if log.user_id is not None)
        user_id = user_log.user_id

        start_date = datetime.now(UTC) - timedelta(hours=1)
        end_date = datetime.now(UTC) + timedelta(hours=1)

        summary = await audit_repository.get_user_activity_summary(
            user_id, start_date=start_date, end_date=end_date
        )

        assert summary["total_actions"] >= 1

    async def test_get_user_activity_summary_no_data(
        self,
        audit_repository: AuditRepositoryImpl,
    ):
        """Test user activity summary with no data."""
        summary = await audit_repository.get_user_activity_summary(uuid4())

        assert summary["total_actions"] == 0
        assert summary["entity_types"] == 0
        assert summary["create_count"] == 0


class TestAuditRepositoryPagination:
    """Test audit log pagination operations."""

    async def test_pagination_offset_limit(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test pagination with offset and limit."""
        # Create multiple audit logs
        for i in range(5):
            audit_log = AuditLog.for_creation(
                entity_type="test_entity",
                entity_id=uuid4(),
                user_id=uuid4(),
                username=f"user_{i}",
                new_value={"sequence": i},
                ip_address=f"192.168.1.{i+1}",
                user_agent="TestAgent/1.0",
                description=f"Test log entry {i}",
            )
            await audit_repository.create(audit_log)

        await async_session.commit()

        # Test pagination
        page1 = await audit_repository.list_by_action("CREATE", limit=2, offset=0)
        page2 = await audit_repository.list_by_action("CREATE", limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2

        # Verify no overlap
        page1_ids = {log.audit_id for log in page1}
        page2_ids = {log.audit_id for log in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestAuditRepositoryEdgeCases:
    """Test audit repository edge cases."""

    async def test_audit_log_with_minimal_data(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test audit log creation with minimal required data."""
        audit_log = AuditLog(
            audit_id=uuid4(),
            entity_type="minimal_entity",
            entity_id=uuid4(),
            action="CREATE",
            user_id=None,
            username=None,
            old_value=None,
            new_value={},
            ip_address=None,
            user_agent=None,
            description=None,
            created_at=datetime.now(UTC),
        )

        result = await audit_repository.create(audit_log)
        await async_session.commit()

        assert result.entity_type == "minimal_entity"
        assert result.action == "CREATE"
        assert result.user_id is None

    async def test_audit_log_with_large_values(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test audit log creation with large JSON values."""
        large_data = {"field_" + str(i): f"value_{i}" * 100 for i in range(10)}

        audit_log = AuditLog.for_update(
            entity_type="large_entity",
            entity_id=uuid4(),
            old_value=large_data,
            new_value={**large_data, "updated": True},
            user_id=uuid4(),
            username="test_user",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
            description="Update with large data",
        )

        result = await audit_repository.create(audit_log)
        await async_session.commit()

        assert result.old_value is not None
        assert result.new_value is not None
        assert len(result.old_value) == 10
        assert result.new_value["updated"] is True

    async def test_audit_log_ordering(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test that audit logs are properly ordered by creation time (descending)."""
        # Create audit logs with different timestamps for the same entity
        entity_id = uuid4()
        entity_type_unique = f"ordering_test_{uuid4().hex[:8]}"
        audit_logs = []

        for i in range(3):
            audit_log = AuditLog(
                audit_id=uuid4(),
                entity_type=entity_type_unique,
                entity_id=entity_id,  # Use same entity_id for all logs
                action="CREATE",
                user_id=uuid4(),
                username="test_user",
                old_value=None,
                new_value={"sequence": i},
                ip_address="192.168.1.1",
                user_agent="TestAgent/1.0",
                description=f"Test log {i}",
                created_at=datetime.now(UTC) - timedelta(minutes=i),
            )
            created = await audit_repository.create(audit_log)
            audit_logs.append(created)
            # Flush after each create to ensure they're written
            await async_session.flush()

        await async_session.commit()

        # Get audit logs by entity specifically (more targeted query)
        result = await audit_repository.list_by_entity(entity_type_unique, entity_id)

        # Should find exactly 3 logs for our specific entity
        assert len(result) == 3

        # Verify ordering (most recent first - created_at desc)
        assert result[0].new_value["sequence"] == 0  # Most recent (created_at - 0 minutes)
        assert result[1].new_value["sequence"] == 1  # Middle (created_at - 1 minute)
        assert result[2].new_value["sequence"] == 2  # Oldest (created_at - 2 minutes)

    async def test_audit_log_all_entity_types(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test audit logs for all common entity types."""
        entity_types = [
            "transaction",
            "customer",
            "merchant",
            "alert",
            "prediction",
            "user",
            "model",
            "rule",
        ]

        audit_logs = []
        for entity_type in entity_types:
            audit_log = AuditLog.for_creation(
                entity_type=entity_type,
                entity_id=uuid4(),
                user_id=uuid4(),
                username="system",
                new_value={"type": entity_type},
                ip_address="127.0.0.1",
                user_agent="System/1.0",
                description=f"Created {entity_type}",
            )
            created = await audit_repository.create(audit_log)
            audit_logs.append(created)

        await async_session.commit()

        # Verify all entity types were stored correctly
        for i, entity_type in enumerate(entity_types):
            assert audit_logs[i].entity_type == entity_type
            assert audit_logs[i].new_value["type"] == entity_type

    async def test_audit_log_immutability(
        self,
        audit_repository: AuditRepositoryImpl,
        sample_audit_log: AuditLog,
        async_session: AsyncSession,
    ):
        """Test that audit logs are truly immutable (no update method)."""
        # Create audit log
        created = await audit_repository.create(sample_audit_log)
        await async_session.commit()

        # Verify repository doesn't have update method
        assert not hasattr(audit_repository, "update")

        # Verify audit log entity is frozen (immutable dataclass)
        with pytest.raises(
            (AttributeError, TypeError)
        ):  # Should raise FrozenInstanceError or similar
            created.action = "MODIFIED"  # This should fail

    async def test_audit_log_factory_methods_validation(
        self,
        audit_repository: AuditRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test validation in audit log factory methods."""
        entity_id = uuid4()
        user_id = uuid4()

        # Test CREATE validation (should not have old_value)
        create_log = AuditLog.for_creation(
            entity_type="test", entity_id=entity_id, user_id=user_id, username="test_user"
        )
        assert create_log.old_value is None
        assert create_log.action == "CREATE"

        # Test UPDATE validation (should have both old and new values)
        update_log = AuditLog.for_update(
            entity_type="test",
            entity_id=entity_id,
            old_value={"status": "old"},
            new_value={"status": "new"},
            user_id=user_id,
            username="test_user",
        )
        assert update_log.old_value is not None
        assert update_log.new_value is not None
        assert update_log.action == "UPDATE"

        # Test DELETE validation (should not have new_value)
        delete_log = AuditLog.for_deletion(
            entity_type="test",
            entity_id=entity_id,
            old_value={"status": "deleted"},
            user_id=user_id,
            username="test_user",
        )
        assert delete_log.old_value is not None
        assert delete_log.new_value is None
        assert delete_log.action == "DELETE"

        # Create all logs to verify they work
        await audit_repository.create(create_log)
        await audit_repository.create(update_log)
        await audit_repository.create(delete_log)
        await async_session.commit()

        # Verify all were created successfully
        created_create = await audit_repository.get_by_id(create_log.audit_id)
        created_update = await audit_repository.get_by_id(update_log.audit_id)
        created_delete = await audit_repository.get_by_id(delete_log.audit_id)

        assert created_create is not None
        assert created_update is not None
        assert created_delete is not None
