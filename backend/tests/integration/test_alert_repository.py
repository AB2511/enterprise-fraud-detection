"""Integration tests for AlertRepositoryImpl."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.alert import Alert
from src.infrastructure.database.repositories.alert_repository_impl import (
    AlertNotFoundError,
    AlertRepositoryImpl,
)


@pytest.fixture
def alert_repository(async_session: AsyncSession) -> AlertRepositoryImpl:
    """Create alert repository instance."""
    return AlertRepositoryImpl(async_session)


@pytest.fixture
def sample_alert() -> Alert:
    """Create sample alert for testing."""
    return Alert(
        alert_id=uuid4(),
        prediction_id=uuid4(),
        transaction_id=uuid4(),
        severity="high",
        alert_type="ml_based",
        assigned_analyst_id=None,
        status="open",
        resolution=None,
        resolution_notes=None,
        created_at=datetime.utcnow(),
        assigned_at=None,
        resolved_at=None,
        updated_at=datetime.utcnow(),
    )


class TestAlertRepositoryCreate:
    """Test alert creation operations."""

    async def test_create_alert_success(
        self,
        alert_repository: AlertRepositoryImpl,
        sample_alert: Alert,
        async_session: AsyncSession,
    ):
        """Test successful alert creation."""
        result = await alert_repository.create(sample_alert)
        await async_session.commit()

        assert result.alert_id == sample_alert.alert_id
        assert result.prediction_id == sample_alert.prediction_id
        assert result.transaction_id == sample_alert.transaction_id
        assert result.severity == sample_alert.severity
        assert result.status == sample_alert.status

    async def test_create_critical_alert(
        self,
        alert_repository: AlertRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test creation of critical severity alert with special SLA."""
        alert = Alert(
            alert_id=uuid4(),
            prediction_id=uuid4(),
            transaction_id=uuid4(),
            severity="critical",
            alert_type="rule_based",
            assigned_analyst_id=None,
            status="open",
            resolution=None,
            resolution_notes=None,
            created_at=datetime.utcnow(),
            assigned_at=None,
            resolved_at=None,
            updated_at=datetime.utcnow(),
        )

        result = await alert_repository.create(alert)
        await async_session.commit()

        assert result.severity == "critical"
        assert result.alert_type == "rule_based"

    async def test_create_alert_with_assignment(
        self,
        alert_repository: AlertRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test alert creation with immediate analyst assignment."""
        analyst_id = uuid4()
        alert = Alert(
            alert_id=uuid4(),
            prediction_id=uuid4(),
            transaction_id=uuid4(),
            severity="medium",
            alert_type="anomaly",
            assigned_analyst_id=analyst_id,
            status="in_review",
            resolution=None,
            resolution_notes=None,
            created_at=datetime.utcnow(),
            assigned_at=datetime.utcnow(),
            resolved_at=None,
            updated_at=datetime.utcnow(),
        )

        result = await alert_repository.create(alert)
        await async_session.commit()

        assert result.assigned_analyst_id == analyst_id
        assert result.status == "in_review"
        assert result.assigned_at is not None


class TestAlertRepositoryRead:
    """Test alert retrieval operations."""

    async def test_get_by_id_success(
        self,
        alert_repository: AlertRepositoryImpl,
        sample_alert: Alert,
        async_session: AsyncSession,
    ):
        """Test successful alert retrieval by ID."""
        created = await alert_repository.create(sample_alert)
        await async_session.commit()

        result = await alert_repository.get_by_id(created.alert_id)

        assert result is not None
        assert result.alert_id == sample_alert.alert_id
        assert result.severity == sample_alert.severity

    async def test_get_by_id_not_found(self, alert_repository: AlertRepositoryImpl):
        """Test alert retrieval with non-existent ID."""
        result = await alert_repository.get_by_id(uuid4())
        assert result is None

    async def test_get_alerts_for_transaction(
        self,
        alert_repository: AlertRepositoryImpl,
        sample_alert: Alert,
        async_session: AsyncSession,
    ):
        """Test getting all alerts for a specific transaction."""
        await alert_repository.create(sample_alert)
        await async_session.commit()

        result = await alert_repository.get_alerts_for_transaction(sample_alert.transaction_id)

        assert len(result) == 1
        assert result[0].transaction_id == sample_alert.transaction_id


class TestAlertRepositoryUpdate:
    """Test alert update operations."""

    async def test_update_alert_success(
        self,
        alert_repository: AlertRepositoryImpl,
        sample_alert: Alert,
        async_session: AsyncSession,
    ):
        """Test successful alert update."""
        created = await alert_repository.create(sample_alert)
        await async_session.commit()

        # Update alert data
        analyst_id = uuid4()
        created.status = "in_review"
        created.assigned_analyst_id = analyst_id
        created.assigned_at = datetime.utcnow()

        result = await alert_repository.update(created)
        await async_session.commit()

        assert result.status == "in_review"
        assert result.assigned_analyst_id == analyst_id
        assert result.assigned_at is not None

    async def test_update_alert_resolution(
        self,
        alert_repository: AlertRepositoryImpl,
        sample_alert: Alert,
        async_session: AsyncSession,
    ):
        """Test updating alert with resolution."""
        created = await alert_repository.create(sample_alert)
        await async_session.commit()

        # Resolve alert
        created.status = "resolved"
        created.resolution = "false_positive"
        created.resolved_at = datetime.utcnow()

        result = await alert_repository.update(created)
        await async_session.commit()

        assert result.status == "resolved"
        assert result.resolution == "false_positive"
        assert result.resolved_at is not None

    async def test_update_alert_not_found(
        self,
        alert_repository: AlertRepositoryImpl,
        sample_alert: Alert,
    ):
        """Test update of non-existent alert."""
        sample_alert.alert_id = uuid4()  # Non-existent ID

        with pytest.raises(AlertNotFoundError):
            await alert_repository.update(sample_alert)


class TestAlertRepositoryDelete:
    """Test alert deletion operations."""

    async def test_delete_alert_success(
        self,
        alert_repository: AlertRepositoryImpl,
        sample_alert: Alert,
        async_session: AsyncSession,
    ):
        """Test successful alert soft deletion."""
        created = await alert_repository.create(sample_alert)
        await async_session.commit()

        result = await alert_repository.delete(created.alert_id)
        await async_session.commit()

        assert result is True

        # Verify alert is soft deleted (not accessible via get_by_id)
        retrieved = await alert_repository.get_by_id(created.alert_id)
        assert retrieved is None

    async def test_delete_alert_not_found(self, alert_repository: AlertRepositoryImpl):
        """Test deletion of non-existent alert."""
        result = await alert_repository.delete(uuid4())
        assert result is False


class TestAlertRepositoryListing:
    """Test alert listing operations."""

    @pytest.fixture
    async def multiple_alerts(
        self,
        alert_repository: AlertRepositoryImpl,
        async_session: AsyncSession,
    ) -> list[Alert]:
        """Create multiple alerts for listing tests."""
        alerts = [
            # Critical alert - unassigned
            Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="critical",
                alert_type="rule_based",
                assigned_analyst_id=None,
                status="open",
                resolution=None,
                resolution_notes=None,
                created_at=datetime.utcnow(),
                assigned_at=None,
                resolved_at=None,
                updated_at=datetime.utcnow(),
            ),
            # High alert - assigned
            Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="high",
                alert_type="ml_based",
                assigned_analyst_id=uuid4(),
                status="in_review",
                resolution=None,
                resolution_notes=None,
                created_at=datetime.utcnow(),
                assigned_at=datetime.utcnow(),
                resolved_at=None,
                updated_at=datetime.utcnow(),
            ),
            # Medium alert - resolved
            Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="medium",
                alert_type="anomaly",
                assigned_analyst_id=uuid4(),
                status="resolved",
                resolution="false_positive",
                resolution_notes="Legitimate transaction",
                created_at=datetime.utcnow() - timedelta(hours=1),
                assigned_at=datetime.utcnow() - timedelta(hours=1),
                resolved_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            # Low alert - open
            Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="low",
                alert_type="velocity",
                assigned_analyst_id=None,
                status="open",
                resolution=None,
                resolution_notes=None,
                created_at=datetime.utcnow() - timedelta(minutes=30),
                assigned_at=None,
                resolved_at=None,
                updated_at=datetime.utcnow(),
            ),
        ]

        created_alerts = []
        for alert in alerts:
            created = await alert_repository.create(alert)
            created_alerts.append(created)

        await async_session.commit()
        return created_alerts

    async def test_list_by_status(
        self,
        alert_repository: AlertRepositoryImpl,
        multiple_alerts: list[Alert],
    ):
        """Test listing alerts by status."""
        open_alerts = await alert_repository.list_by_status("open")
        in_review_alerts = await alert_repository.list_by_status("in_review")
        resolved_alerts = await alert_repository.list_by_status("resolved")

        # Find our test alerts specifically
        test_alert_ids = {alert.alert_id for alert in multiple_alerts}

        open_test_alerts = [a for a in open_alerts if a.alert_id in test_alert_ids]
        in_review_test_alerts = [a for a in in_review_alerts if a.alert_id in test_alert_ids]
        resolved_test_alerts = [a for a in resolved_alerts if a.alert_id in test_alert_ids]

        assert len(open_test_alerts) == 2  # critical and low alerts
        assert len(in_review_test_alerts) == 1  # high alert
        assert len(resolved_test_alerts) == 1  # medium alert

    async def test_list_by_severity(
        self,
        alert_repository: AlertRepositoryImpl,
        multiple_alerts: list[Alert],
    ):
        """Test listing alerts by severity."""
        critical_alerts = await alert_repository.list_by_severity("critical")
        high_alerts = await alert_repository.list_by_severity("high")
        medium_alerts = await alert_repository.list_by_severity("medium")
        low_alerts = await alert_repository.list_by_severity("low")

        # Find our test alerts specifically
        test_alert_ids = {alert.alert_id for alert in multiple_alerts}

        critical_test_alerts = [a for a in critical_alerts if a.alert_id in test_alert_ids]
        high_test_alerts = [a for a in high_alerts if a.alert_id in test_alert_ids]
        medium_test_alerts = [a for a in medium_alerts if a.alert_id in test_alert_ids]
        low_test_alerts = [a for a in low_alerts if a.alert_id in test_alert_ids]

        assert len(critical_test_alerts) == 1
        assert len(high_test_alerts) == 1
        assert len(medium_test_alerts) == 1
        assert len(low_test_alerts) == 1

    async def test_list_by_analyst(
        self,
        alert_repository: AlertRepositoryImpl,
        multiple_alerts: list[Alert],
    ):
        """Test listing alerts assigned to specific analyst."""
        # Get analyst ID from the assigned alerts
        assigned_alert = next(alert for alert in multiple_alerts if alert.assigned_analyst_id)
        analyst_id = assigned_alert.assigned_analyst_id

        result = await alert_repository.list_by_analyst(analyst_id)

        # Should find at least one alert (could be more if multiple have same analyst)
        assert len(result) >= 1
        for alert in result:
            assert alert.assigned_analyst_id == analyst_id

    async def test_list_unassigned(
        self,
        alert_repository: AlertRepositoryImpl,
        multiple_alerts: list[Alert],
    ):
        """Test listing unassigned alerts."""
        result = await alert_repository.list_unassigned()

        # Find our test alerts specifically
        test_alert_ids = {alert.alert_id for alert in multiple_alerts}
        unassigned_test_alerts = [a for a in result if a.alert_id in test_alert_ids]

        # Should find open unassigned alerts (critical and low)
        assert len(unassigned_test_alerts) == 2
        for alert in unassigned_test_alerts:
            assert alert.assigned_analyst_id is None
            assert alert.status == "open"

    async def test_list_sla_breached(
        self,
        alert_repository: AlertRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test listing SLA-breached alerts."""
        # Create an old alert that would breach SLA
        old_time = datetime.utcnow() - timedelta(days=2)
        old_alert = Alert(
            alert_id=uuid4(),
            prediction_id=uuid4(),
            transaction_id=uuid4(),
            severity="high",
            alert_type="ml_based",
            assigned_analyst_id=None,
            status="open",
            resolution=None,
            resolution_notes=None,
            created_at=old_time,
            assigned_at=None,
            resolved_at=None,
            updated_at=old_time,
        )

        await alert_repository.create(old_alert)
        await async_session.commit()

        result = await alert_repository.list_sla_breached()

        # Should find the old alert
        assert len(result) >= 1
        found_old_alert = next((a for a in result if a.alert_id == old_alert.alert_id), None)
        assert found_old_alert is not None

    async def test_get_open_alerts_in_range(
        self,
        alert_repository: AlertRepositoryImpl,
        multiple_alerts: list[Alert],
    ):
        """Test getting open alerts within date range."""
        start_date = datetime.utcnow() - timedelta(hours=2)
        end_date = datetime.utcnow() + timedelta(hours=1)

        result = await alert_repository.get_open_alerts_in_range(start_date, end_date)

        # Should find open and in_review alerts within range
        assert len(result) >= 2  # At least the critical, high, and low alerts
        for alert in result:
            assert alert.status in ["open", "in_review"]
            assert start_date <= alert.created_at <= end_date


class TestAlertRepositoryCount:
    """Test alert counting operations."""

    @pytest.fixture
    async def multiple_alerts(
        self,
        alert_repository: AlertRepositoryImpl,
        async_session: AsyncSession,
    ) -> list[Alert]:
        """Create multiple alerts for count tests."""
        alerts = [
            # Critical alert - unassigned
            Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="critical",
                alert_type="rule_based",
                assigned_analyst_id=None,
                status="open",
                resolution=None,
                resolution_notes=None,
                created_at=datetime.utcnow(),
                assigned_at=None,
                resolved_at=None,
                updated_at=datetime.utcnow(),
            ),
            # High alert - assigned
            Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="high",
                alert_type="ml_based",
                assigned_analyst_id=uuid4(),
                status="in_review",
                resolution=None,
                resolution_notes=None,
                created_at=datetime.utcnow(),
                assigned_at=datetime.utcnow(),
                resolved_at=None,
                updated_at=datetime.utcnow(),
            ),
            # Medium alert - resolved
            Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="medium",
                alert_type="anomaly",
                assigned_analyst_id=uuid4(),
                status="resolved",
                resolution="false_positive",
                resolution_notes="Legitimate transaction",
                created_at=datetime.utcnow() - timedelta(hours=1),
                assigned_at=datetime.utcnow() - timedelta(hours=1),
                resolved_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            # Low alert - open
            Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="low",
                alert_type="velocity",
                assigned_analyst_id=None,
                status="open",
                resolution=None,
                resolution_notes=None,
                created_at=datetime.utcnow() - timedelta(minutes=30),
                assigned_at=None,
                resolved_at=None,
                updated_at=datetime.utcnow(),
            ),
        ]

        created_alerts = []
        for alert in alerts:
            created = await alert_repository.create(alert)
            created_alerts.append(created)

        await async_session.commit()
        return created_alerts

    async def test_count_by_status(
        self,
        alert_repository: AlertRepositoryImpl,
        multiple_alerts: list[Alert],
    ):
        """Test counting alerts by status."""
        # Count all alerts by status
        open_count = await alert_repository.count_by_status("open")
        in_review_count = await alert_repository.count_by_status("in_review")
        resolved_count = await alert_repository.count_by_status("resolved")

        # Count our specific test alerts by status
        test_open_count = sum(1 for a in multiple_alerts if a.status == "open")
        test_in_review_count = sum(1 for a in multiple_alerts if a.status == "in_review")
        test_resolved_count = sum(1 for a in multiple_alerts if a.status == "resolved")

        # Verify our test alerts are included in the counts
        assert open_count >= test_open_count
        assert in_review_count >= test_in_review_count
        assert resolved_count >= test_resolved_count

        # Verify the specific counts for our test data
        assert test_open_count == 2
        assert test_in_review_count == 1
        assert test_resolved_count == 1

    async def test_count_by_status_empty(self, alert_repository: AlertRepositoryImpl):
        """Test counting alerts by status with no results."""
        count = await alert_repository.count_by_status("non_existent_status")
        assert count == 0


class TestAlertRepositorySLA:
    """Test SLA-related operations."""

    async def test_update_sla_breach_status(
        self,
        alert_repository: AlertRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test updating SLA breach status for overdue alerts."""
        # Create an old alert
        old_time = datetime.utcnow() - timedelta(days=2)
        old_alert = Alert(
            alert_id=uuid4(),
            prediction_id=uuid4(),
            transaction_id=uuid4(),
            severity="medium",
            alert_type="ml_based",
            assigned_analyst_id=None,
            status="open",
            resolution=None,
            resolution_notes=None,
            created_at=old_time,
            assigned_at=None,
            resolved_at=None,
            updated_at=old_time,
        )

        # Create a recent alert
        recent_alert = Alert(
            alert_id=uuid4(),
            prediction_id=uuid4(),
            transaction_id=uuid4(),
            severity="high",
            alert_type="rule_based",
            assigned_analyst_id=None,
            status="open",
            resolution=None,
            resolution_notes=None,
            created_at=datetime.utcnow(),
            assigned_at=None,
            resolved_at=None,
            updated_at=datetime.utcnow(),
        )

        await alert_repository.create(old_alert)
        await alert_repository.create(recent_alert)
        await async_session.commit()

        # Update SLA breach status
        breach_count = await alert_repository.update_sla_breach_status()
        await async_session.commit()

        # Should mark at least the old alert as breached
        assert breach_count >= 1


class TestAlertRepositoryPagination:
    """Test alert pagination operations."""

    async def test_pagination_offset_limit(
        self,
        alert_repository: AlertRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test pagination with offset and limit."""
        # Create multiple alerts
        for i in range(5):
            alert = Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="medium" if i < 3 else "high",
                alert_type="ml_based",
                assigned_analyst_id=None,
                status="open",
                resolution=None,
                resolution_notes=None,
                created_at=datetime.utcnow() - timedelta(minutes=i),
                assigned_at=None,
                resolved_at=None,
                updated_at=datetime.utcnow(),
            )
            await alert_repository.create(alert)

        await async_session.commit()

        # Test pagination
        page1 = await alert_repository.list_by_status("open", limit=2, offset=0)
        page2 = await alert_repository.list_by_status("open", limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2

        # Verify no overlap
        page1_ids = {a.alert_id for a in page1}
        page2_ids = {a.alert_id for a in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestAlertRepositoryEdgeCases:
    """Test alert repository edge cases."""

    async def test_alert_with_all_severities(
        self,
        alert_repository: AlertRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test alerts with all possible severity levels."""
        severities = ["low", "medium", "high", "critical"]

        alerts = []
        for severity in severities:
            alert = Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity=severity,
                alert_type="ml_based",
                assigned_analyst_id=None,
                status="open",
                resolution=None,
                resolution_notes=None,
                created_at=datetime.utcnow(),
                assigned_at=None,
                resolved_at=None,
                updated_at=datetime.utcnow(),
            )
            created = await alert_repository.create(alert)
            alerts.append(created)

        await async_session.commit()

        # Verify all severities were stored correctly
        for i, severity in enumerate(severities):
            assert alerts[i].severity == severity

    async def test_alert_with_all_types(
        self,
        alert_repository: AlertRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test alerts with all possible alert types."""
        alert_types = ["rule_based", "ml_based", "anomaly", "velocity", "manual"]

        alerts = []
        for alert_type in alert_types:
            alert = Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="medium",
                alert_type=alert_type,
                assigned_analyst_id=None,
                status="open",
                resolution=None,
                resolution_notes=None,
                created_at=datetime.utcnow(),
                assigned_at=None,
                resolved_at=None,
                updated_at=datetime.utcnow(),
            )
            created = await alert_repository.create(alert)
            alerts.append(created)

        await async_session.commit()

        # Verify all types were stored correctly
        for i, alert_type in enumerate(alert_types):
            assert alerts[i].alert_type == alert_type

    async def test_alert_with_all_statuses(
        self,
        alert_repository: AlertRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test alerts with all possible statuses."""
        statuses = ["open", "in_review", "resolved", "false_positive", "confirmed_fraud"]

        alerts = []
        for status in statuses:
            alert = Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="medium",
                alert_type="ml_based",
                assigned_analyst_id=uuid4() if status != "open" else None,
                status=status,
                resolution=(
                    "fraud"
                    if status == "confirmed_fraud"
                    else ("false_positive" if status == "false_positive" else None)
                ),
                resolution_notes=None,
                created_at=datetime.utcnow(),
                assigned_at=datetime.utcnow() if status != "open" else None,
                resolved_at=(
                    datetime.utcnow()
                    if status in ["resolved", "false_positive", "confirmed_fraud"]
                    else None
                ),
                updated_at=datetime.utcnow(),
            )
            created = await alert_repository.create(alert)
            alerts.append(created)

        await async_session.commit()

        # Verify all statuses were stored correctly
        for i, status in enumerate(statuses):
            assert alerts[i].status == status

    async def test_repository_error_handling(
        self,
        alert_repository: AlertRepositoryImpl,
    ):
        """Test repository error handling."""
        with pytest.raises(AlertNotFoundError):
            invalid_alert = Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="medium",
                alert_type="ml_based",
                assigned_analyst_id=None,
                status="open",
                resolution=None,
                resolution_notes=None,
                created_at=datetime.utcnow(),
                assigned_at=None,
                resolved_at=None,
                updated_at=datetime.utcnow(),
            )
            await alert_repository.update(invalid_alert)

    async def test_alert_ordering(
        self,
        alert_repository: AlertRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test that alerts are properly ordered by creation time (descending)."""
        # Create alerts with different timestamps
        alerts = []
        for i in range(3):
            alert = Alert(
                alert_id=uuid4(),
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                severity="medium",
                alert_type="ml_based",
                assigned_analyst_id=None,
                status="open",
                resolution=None,
                resolution_notes=None,
                created_at=datetime.utcnow() - timedelta(minutes=i),
                assigned_at=None,
                resolved_at=None,
                updated_at=datetime.utcnow(),
            )
            created = await alert_repository.create(alert)
            alerts.append(created)

        await async_session.commit()

        # Get alerts by status (should be ordered by created_at desc)
        result = await alert_repository.list_by_status("open")

        # Verify ordering (newest first)
        assert len(result) >= 3
        for i in range(len(result) - 1):
            assert result[i].created_at >= result[i + 1].created_at
