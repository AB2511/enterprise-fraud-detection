"""Integration tests for TransactionRepositoryImpl."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.transaction import Transaction
from src.infrastructure.database.repositories.transaction_repository_impl import (
    TransactionNotFoundError,
    TransactionRepositoryImpl,
)


@pytest.fixture
def transaction_repository(async_session: AsyncSession) -> TransactionRepositoryImpl:
    """Create transaction repository instance."""
    return TransactionRepositoryImpl(async_session)


@pytest.fixture
def sample_transaction() -> Transaction:
    """Create sample transaction for testing."""
    return Transaction(
        transaction_id=uuid4(),
        customer_id=uuid4(),
        merchant_id=uuid4(),
        amount=Decimal("199.99"),
        currency="USD",
        timestamp=datetime.now(UTC),
        payment_channel="online",
        payment_method="card",
        device_id="device123",
        ip_address="192.168.1.1",
        latitude=40.7128,
        longitude=-74.0060,
        terminal_id="term456",
        merchant_category="retail",
        mcc="5411",
        card_type="visa",
        card_last_four="1234",
        status="approved",
        is_fraud=False,
        velocity_1h=1,
        velocity_24h=5,
        velocity_7d=20,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestTransactionRepositoryCreate:
    """Test transaction creation operations."""

    async def test_save_transaction_success(
        self,
        transaction_repository: TransactionRepositoryImpl,
        sample_transaction: Transaction,
        async_session: AsyncSession,
    ):
        """Test successful transaction creation."""
        result = await transaction_repository.save(sample_transaction)
        await async_session.commit()

        assert result.transaction_id == sample_transaction.transaction_id
        assert result.customer_id == sample_transaction.customer_id
        assert result.amount == sample_transaction.amount
        assert result.currency == sample_transaction.currency

    async def test_save_transaction_with_fraud_flag(
        self,
        transaction_repository: TransactionRepositoryImpl,
        sample_transaction: Transaction,
        async_session: AsyncSession,
    ):
        """Test transaction creation with fraud flag."""
        sample_transaction.is_fraud = True

        result = await transaction_repository.save(sample_transaction)
        await async_session.commit()

        assert result.is_fraud is True

    async def test_save_transaction_with_velocity_data(
        self,
        transaction_repository: TransactionRepositoryImpl,
        sample_transaction: Transaction,
        async_session: AsyncSession,
    ):
        """Test transaction creation with velocity features."""
        sample_transaction.velocity_1h = 3
        sample_transaction.velocity_24h = 15
        sample_transaction.velocity_7d = 45

        result = await transaction_repository.save(sample_transaction)
        await async_session.commit()

        assert result.velocity_1h == 3
        assert result.velocity_24h == 15
        assert result.velocity_7d == 45


class TestTransactionRepositoryRead:
    """Test transaction retrieval operations."""

    async def test_get_by_id_success(
        self,
        transaction_repository: TransactionRepositoryImpl,
        sample_transaction: Transaction,
        async_session: AsyncSession,
    ):
        """Test successful transaction retrieval by ID."""
        saved = await transaction_repository.save(sample_transaction)
        await async_session.commit()

        result = await transaction_repository.get_by_id(saved.transaction_id)

        assert result is not None
        assert result.transaction_id == sample_transaction.transaction_id
        assert result.amount == sample_transaction.amount

    async def test_get_by_id_not_found(self, transaction_repository: TransactionRepositoryImpl):
        """Test transaction retrieval with non-existent ID."""
        result = await transaction_repository.get_by_id(uuid4())
        assert result is None

    async def test_get_by_user_success(
        self,
        transaction_repository: TransactionRepositoryImpl,
        sample_transaction: Transaction,
        async_session: AsyncSession,
    ):
        """Test successful transaction retrieval by user."""
        await transaction_repository.save(sample_transaction)
        await async_session.commit()

        result = await transaction_repository.get_by_user(str(sample_transaction.customer_id))

        assert len(result) == 1
        assert result[0].customer_id == sample_transaction.customer_id

    async def test_get_by_user_with_date_filter(
        self,
        transaction_repository: TransactionRepositoryImpl,
        sample_transaction: Transaction,
        async_session: AsyncSession,
    ):
        """Test transaction retrieval by user with date filters."""
        await transaction_repository.save(sample_transaction)
        await async_session.commit()

        yesterday = datetime.now(UTC) - timedelta(days=1)
        tomorrow = datetime.now(UTC) + timedelta(days=1)

        result = await transaction_repository.get_by_user(
            str(sample_transaction.customer_id), start_date=yesterday, end_date=tomorrow
        )

        assert len(result) == 1

    async def test_get_by_user_no_results(self, transaction_repository: TransactionRepositoryImpl):
        """Test user transaction retrieval with no results."""
        result = await transaction_repository.get_by_user(str(uuid4()))
        assert len(result) == 0


class TestTransactionRepositoryUpdate:
    """Test transaction update operations."""

    async def test_update_transaction_success(
        self,
        transaction_repository: TransactionRepositoryImpl,
        sample_transaction: Transaction,
        async_session: AsyncSession,
    ):
        """Test successful transaction update."""
        saved = await transaction_repository.save(sample_transaction)
        await async_session.commit()

        # Update transaction data
        saved.status = "pending"
        saved.is_fraud = True
        saved.velocity_1h = 5

        result = await transaction_repository.update(saved)
        await async_session.commit()

        assert result.status == "pending"
        assert result.is_fraud is True
        assert result.velocity_1h == 5

    async def test_update_transaction_not_found(
        self,
        transaction_repository: TransactionRepositoryImpl,
        sample_transaction: Transaction,
    ):
        """Test update of non-existent transaction."""
        sample_transaction.transaction_id = uuid4()  # Non-existent ID

        with pytest.raises(TransactionNotFoundError):
            await transaction_repository.update(sample_transaction)


class TestTransactionRepositoryDelete:
    """Test transaction deletion operations."""

    async def test_delete_transaction_success(
        self,
        transaction_repository: TransactionRepositoryImpl,
        sample_transaction: Transaction,
        async_session: AsyncSession,
    ):
        """Test successful transaction soft deletion."""
        saved = await transaction_repository.save(sample_transaction)
        await async_session.commit()

        result = await transaction_repository.delete(saved.transaction_id)
        await async_session.commit()

        assert result is True

        # Verify transaction is soft deleted (not retrievable)
        retrieved = await transaction_repository.get_by_id(saved.transaction_id)
        assert retrieved is None

    async def test_delete_transaction_not_found(
        self, transaction_repository: TransactionRepositoryImpl
    ):
        """Test deletion of non-existent transaction."""
        result = await transaction_repository.delete(uuid4())
        assert result is False


class TestTransactionRepositoryVelocityCalculations:
    """Test transaction velocity calculation operations."""

    async def test_count_recent_transactions(
        self,
        transaction_repository: TransactionRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test counting recent transactions for velocity."""
        customer_id = uuid4()

        # Create transactions at different times
        now = datetime.now(UTC)
        transactions = []

        for i in range(3):
            transaction = Transaction(
                transaction_id=uuid4(),
                customer_id=customer_id,
                merchant_id=uuid4(),
                amount=Decimal("100.00"),
                currency="USD",
                timestamp=now - timedelta(minutes=i * 10),
                payment_channel="online",
                payment_method="card",
                device_id="device123",
                ip_address="192.168.1.1",
                latitude=40.7128,
                longitude=-74.0060,
                terminal_id="term456",
                merchant_category="retail",
                mcc="5411",
                status="approved",
                is_fraud=False,
                velocity_1h=0,
                velocity_24h=0,
                velocity_7d=0,
                created_at=now - timedelta(minutes=i * 10),
                updated_at=now - timedelta(minutes=i * 10),
            )
            transactions.append(transaction)
            await transaction_repository.save(transaction)

        await async_session.commit()

        # Count transactions in last 60 minutes
        count = await transaction_repository.count_recent_transactions(str(customer_id), 60)

        assert count == 3

        # Count transactions in last 15 minutes
        count_15min = await transaction_repository.count_recent_transactions(str(customer_id), 15)

        assert count_15min == 2  # Only first two transactions

    async def test_get_velocity_data(
        self,
        transaction_repository: TransactionRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test getting velocity data for a customer."""
        customer_id = uuid4()
        reference_time = datetime.now(UTC)

        # Create transactions at different times
        times = [
            reference_time - timedelta(minutes=30),  # 1h window
            reference_time - timedelta(hours=12),  # 24h window
            reference_time - timedelta(days=3),  # 7d window
            reference_time - timedelta(days=10),  # Outside 7d window
        ]

        for _i, timestamp in enumerate(times):
            transaction = Transaction(
                transaction_id=uuid4(),
                customer_id=customer_id,
                merchant_id=uuid4(),
                amount=Decimal("50.00"),
                currency="USD",
                timestamp=timestamp,
                payment_channel="online",
                payment_method="card",
                device_id="device123",
                ip_address="192.168.1.1",
                latitude=40.7128,
                longitude=-74.0060,
                terminal_id="term456",
                merchant_category="retail",
                mcc="5411",
                status="approved",
                is_fraud=False,
                velocity_1h=0,
                velocity_24h=0,
                velocity_7d=0,
                created_at=timestamp,
                updated_at=timestamp,
            )
            await transaction_repository.save(transaction)

        await async_session.commit()

        # Get velocity data
        velocity_data = await transaction_repository.get_velocity_data(customer_id, reference_time)

        assert velocity_data["velocity_1h"] == 1
        assert velocity_data["velocity_24h"] == 2
        assert velocity_data["velocity_7d"] == 3


class TestTransactionRepositoryFiltering:
    """Test transaction filtering and search operations."""

    @pytest.fixture
    async def multiple_transactions(
        self,
        transaction_repository: TransactionRepositoryImpl,
        async_session: AsyncSession,
    ) -> list[Transaction]:
        """Create multiple transactions for filtering tests."""
        customer_id = uuid4()
        merchant_id_1 = uuid4()
        merchant_id_2 = uuid4()

        transactions = [
            # High-value transaction
            Transaction(
                transaction_id=uuid4(),
                customer_id=customer_id,
                merchant_id=merchant_id_1,
                amount=Decimal("999.99"),
                currency="USD",
                timestamp=datetime.now(UTC),
                payment_channel="online",
                payment_method="card",
                device_id="device123",
                ip_address="192.168.1.1",
                latitude=40.7128,
                longitude=-74.0060,
                terminal_id="term456",
                merchant_category="electronics",
                mcc="5732",
                status="approved",
                is_fraud=True,
                velocity_1h=1,
                velocity_24h=5,
                velocity_7d=20,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            # Low-value transaction
            Transaction(
                transaction_id=uuid4(),
                customer_id=customer_id,
                merchant_id=merchant_id_2,
                amount=Decimal("25.50"),
                currency="USD",
                timestamp=datetime.now(UTC),
                payment_channel="pos",
                payment_method="card",
                device_id="device456",
                ip_address="192.168.1.2",
                latitude=40.7580,
                longitude=-73.9855,
                terminal_id="term789",
                merchant_category="grocery",
                mcc="5411",
                status="approved",
                is_fraud=False,
                velocity_1h=2,
                velocity_24h=8,
                velocity_7d=25,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            # Pending transaction
            Transaction(
                transaction_id=uuid4(),
                customer_id=uuid4(),  # Different customer
                merchant_id=merchant_id_1,
                amount=Decimal("150.00"),
                currency="EUR",
                timestamp=datetime.now(UTC),
                payment_channel="mobile",
                payment_method="wallet",
                device_id="device789",
                ip_address="10.0.0.1",
                latitude=51.5074,
                longitude=-0.1278,
                terminal_id=None,
                merchant_category="restaurant",
                mcc="5812",
                status="pending",
                is_fraud=False,
                velocity_1h=1,
                velocity_24h=3,
                velocity_7d=12,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        ]

        created_transactions = []
        for transaction in transactions:
            created = await transaction_repository.save(transaction)
            created_transactions.append(created)

        await async_session.commit()
        return created_transactions

    async def test_find_by_criteria_amount_range(
        self,
        transaction_repository: TransactionRepositoryImpl,
        multiple_transactions: list[Transaction],
    ):
        """Test finding transactions by amount range."""
        result = await transaction_repository.find_by_criteria(min_amount=100.0, max_amount=1000.0)

        assert len(result) >= 2
        for txn in result:
            assert Decimal("100.0") <= txn.amount <= Decimal("1000.0")

    async def test_find_by_criteria_payment_channel(
        self,
        transaction_repository: TransactionRepositoryImpl,
        multiple_transactions: list[Transaction],
    ):
        """Test finding transactions by payment channel."""
        result = await transaction_repository.find_by_criteria(payment_channel="online")

        assert len(result) >= 1
        for txn in result:
            assert txn.payment_channel == "online"

    async def test_find_by_criteria_fraud_status(
        self,
        transaction_repository: TransactionRepositoryImpl,
        multiple_transactions: list[Transaction],
    ):
        """Test finding transactions by fraud status."""
        fraud_result = await transaction_repository.find_by_criteria(is_fraud=True)

        legitimate_result = await transaction_repository.find_by_criteria(is_fraud=False)

        assert len(fraud_result) >= 1
        assert len(legitimate_result) >= 2

        for txn in fraud_result:
            assert txn.is_fraud is True

        for txn in legitimate_result:
            assert txn.is_fraud is False

    async def test_find_by_criteria_currency(
        self,
        transaction_repository: TransactionRepositoryImpl,
        multiple_transactions: list[Transaction],
    ):
        """Test finding transactions by currency."""
        usd_result = await transaction_repository.find_by_criteria(currency="USD")

        eur_result = await transaction_repository.find_by_criteria(currency="EUR")

        assert len(usd_result) >= 2
        assert len(eur_result) >= 1

    async def test_find_by_criteria_comprehensive(
        self,
        transaction_repository: TransactionRepositoryImpl,
        multiple_transactions: list[Transaction],
    ):
        """Test comprehensive criteria search."""
        result = await transaction_repository.find_by_criteria(
            currency="USD", min_amount=20.0, max_amount=500.0, is_fraud=False, status="approved"
        )

        assert len(result) >= 1
        for txn in result:
            assert txn.currency == "USD"
            assert Decimal("20.0") <= txn.amount <= Decimal("500.0")
            assert txn.is_fraud is False
            assert txn.status == "approved"


class TestTransactionRepositoryStatistics:
    """Test transaction statistics operations."""

    @pytest.fixture
    async def multiple_transactions(
        self,
        transaction_repository: TransactionRepositoryImpl,
        async_session: AsyncSession,
    ) -> list[Transaction]:
        """Create multiple transactions for statistics tests."""
        customer_id = uuid4()
        merchant_id = uuid4()

        transactions = []
        for i in range(5):
            transaction = Transaction(
                transaction_id=uuid4(),
                customer_id=customer_id,
                merchant_id=merchant_id,
                amount=Decimal(f"{100 + i * 50}.00"),
                currency="USD",
                timestamp=datetime.now(UTC) - timedelta(days=i),
                payment_channel="online",
                payment_method="card",
                device_id="device123",
                ip_address="192.168.1.1",
                latitude=40.7128,
                longitude=-74.0060,
                terminal_id="term456",
                merchant_category="retail",
                mcc="5411",
                status="approved",
                is_fraud=(i % 2 == 0),  # Alternating fraud status
                velocity_1h=1,
                velocity_24h=5,
                velocity_7d=20,
                created_at=datetime.now(UTC) - timedelta(days=i),
                updated_at=datetime.now(UTC) - timedelta(days=i),
            )
            transactions.append(transaction)
            await transaction_repository.save(transaction)

        await async_session.commit()
        return transactions

    async def test_get_fraud_statistics(
        self,
        transaction_repository: TransactionRepositoryImpl,
        multiple_transactions: list[Transaction],
    ):
        """Test getting fraud statistics."""
        yesterday = datetime.now(UTC) - timedelta(days=1)
        tomorrow = datetime.now(UTC) + timedelta(days=1)

        stats = await transaction_repository.get_fraud_statistics(
            start_date=yesterday, end_date=tomorrow, group_by="day"
        )

        assert len(stats) >= 1

        for stat in stats:
            assert "total_transactions" in stat
            assert "fraud_count" in stat
            assert "fraud_rate" in stat
            assert stat["fraud_rate"] >= 0.0


class TestTransactionRepositoryBulkOperations:
    """Test transaction bulk operations."""

    async def test_bulk_update_fraud_status(
        self,
        transaction_repository: TransactionRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test bulk fraud status update."""
        # Create multiple transactions
        transactions = []
        for _i in range(3):
            transaction = Transaction(
                transaction_id=uuid4(),
                customer_id=uuid4(),
                merchant_id=uuid4(),
                amount=Decimal("100.00"),
                currency="USD",
                timestamp=datetime.now(UTC),
                payment_channel="online",
                payment_method="card",
                device_id="device123",
                ip_address="192.168.1.1",
                latitude=40.7128,
                longitude=-74.0060,
                terminal_id="term456",
                merchant_category="retail",
                mcc="5411",
                status="approved",
                is_fraud=False,
                velocity_1h=1,
                velocity_24h=5,
                velocity_7d=20,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            created = await transaction_repository.save(transaction)
            transactions.append(created)

        await async_session.commit()

        # Bulk update fraud status
        transaction_ids = [t.transaction_id for t in transactions]
        updated_count = await transaction_repository.bulk_update_fraud_status(transaction_ids, True)
        await async_session.commit()

        assert updated_count == 3

        # Verify updates
        for transaction_id in transaction_ids:
            updated_transaction = await transaction_repository.get_by_id(transaction_id)
            assert updated_transaction.is_fraud is True

    async def test_bulk_update_empty_list(self, transaction_repository: TransactionRepositoryImpl):
        """Test bulk update with empty ID list."""
        result = await transaction_repository.bulk_update_fraud_status([], True)
        assert result == 0


class TestTransactionRepositoryPagination:
    """Test transaction pagination operations."""

    async def test_pagination_offset_limit(
        self,
        transaction_repository: TransactionRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test pagination with offset and limit."""
        customer_id = uuid4()

        # Create multiple transactions
        for i in range(5):
            transaction = Transaction(
                transaction_id=uuid4(),
                customer_id=customer_id,
                merchant_id=uuid4(),
                amount=Decimal(f"{100 + i}.00"),
                currency="USD",
                timestamp=datetime.now(UTC) - timedelta(minutes=i),
                payment_channel="online",
                payment_method="card",
                device_id="device123",
                ip_address="192.168.1.1",
                latitude=40.7128,
                longitude=-74.0060,
                terminal_id="term456",
                merchant_category="retail",
                mcc="5411",
                status="approved",
                is_fraud=False,
                velocity_1h=1,
                velocity_24h=5,
                velocity_7d=20,
                created_at=datetime.now(UTC) - timedelta(minutes=i),
                updated_at=datetime.now(UTC) - timedelta(minutes=i),
            )
            await transaction_repository.save(transaction)

        await async_session.commit()

        # Test pagination
        page1 = await transaction_repository.get_by_user(str(customer_id), limit=2)

        # Should get all since we don't have offset parameter in get_by_user
        # Let's use find_by_criteria instead
        page1 = await transaction_repository.find_by_criteria(
            customer_id=customer_id, limit=2, offset=0
        )
        page2 = await transaction_repository.find_by_criteria(
            customer_id=customer_id, limit=2, offset=2
        )

        assert len(page1) == 2
        assert len(page2) == 2

        # Verify no overlap
        page1_ids = {t.transaction_id for t in page1}
        page2_ids = {t.transaction_id for t in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestTransactionRepositoryEdgeCases:
    """Test transaction repository edge cases."""

    async def test_transaction_with_null_optional_fields(
        self,
        transaction_repository: TransactionRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test transaction creation with null optional fields."""
        transaction = Transaction(
            transaction_id=uuid4(),
            customer_id=uuid4(),
            merchant_id=uuid4(),
            amount=Decimal("50.00"),
            currency="USD",
            timestamp=datetime.now(UTC),
            payment_channel="online",
            payment_method="card",
            device_id=None,  # Optional field
            ip_address=None,  # Optional field
            latitude=None,  # Optional field
            longitude=None,  # Optional field
            terminal_id=None,  # Optional field
            merchant_category="",
            mcc="",
            status="approved",
            is_fraud=False,
            velocity_1h=0,
            velocity_24h=0,
            velocity_7d=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        result = await transaction_repository.save(transaction)
        await async_session.commit()

        assert result.device_id is None
        assert result.ip_address is None
        assert result.latitude is None

    async def test_transaction_with_extreme_amounts(
        self,
        transaction_repository: TransactionRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test transaction with very small and large amounts."""
        # Very small amount
        small_transaction = Transaction(
            transaction_id=uuid4(),
            customer_id=uuid4(),
            merchant_id=uuid4(),
            amount=Decimal("0.01"),
            currency="USD",
            timestamp=datetime.now(UTC),
            payment_channel="online",
            payment_method="card",
            device_id="device123",
            ip_address="192.168.1.1",
            latitude=40.7128,
            longitude=-74.0060,
            terminal_id="term456",
            merchant_category="retail",
            mcc="5411",
            status="approved",
            is_fraud=False,
            velocity_1h=1,
            velocity_24h=5,
            velocity_7d=20,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Large amount
        large_transaction = Transaction(
            transaction_id=uuid4(),
            customer_id=uuid4(),
            merchant_id=uuid4(),
            amount=Decimal("999999.99"),
            currency="USD",
            timestamp=datetime.now(UTC),
            payment_channel="online",
            payment_method="card",
            device_id="device123",
            ip_address="192.168.1.1",
            latitude=40.7128,
            longitude=-74.0060,
            terminal_id="term456",
            merchant_category="retail",
            mcc="5411",
            status="approved",
            is_fraud=False,
            velocity_1h=1,
            velocity_24h=5,
            velocity_7d=20,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        small_result = await transaction_repository.save(small_transaction)
        large_result = await transaction_repository.save(large_transaction)
        await async_session.commit()

        assert small_result.amount == Decimal("0.01")
        assert large_result.amount == Decimal("999999.99")

    async def test_repository_error_handling(
        self,
        transaction_repository: TransactionRepositoryImpl,
    ):
        """Test repository error handling."""
        with pytest.raises(TransactionNotFoundError):
            invalid_transaction = Transaction(
                transaction_id=uuid4(),
                customer_id=uuid4(),
                merchant_id=uuid4(),
                amount=Decimal("100.00"),
                currency="USD",
                timestamp=datetime.now(UTC),
                payment_channel="online",
                payment_method="card",
                device_id="device123",
                ip_address="192.168.1.1",
                latitude=40.7128,
                longitude=-74.0060,
                terminal_id="term456",
                merchant_category="retail",
                mcc="5411",
                status="approved",
                is_fraud=False,
                velocity_1h=1,
                velocity_24h=5,
                velocity_7d=20,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await transaction_repository.update(invalid_transaction)
