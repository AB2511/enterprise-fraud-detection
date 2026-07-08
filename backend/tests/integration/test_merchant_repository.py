"""Integration tests for MerchantRepositoryImpl."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.merchant import Merchant
from src.infrastructure.database.repositories.merchant_repository_impl import (
    MerchantNameExistsError,
    MerchantNotFoundError,
    MerchantRepositoryImpl,
)


@pytest.fixture
def merchant_repository(async_session: AsyncSession) -> MerchantRepositoryImpl:
    """Create merchant repository instance."""
    return MerchantRepositoryImpl(async_session)


@pytest.fixture
def sample_merchant() -> Merchant:
    """Create sample merchant for testing."""
    return Merchant(
        merchant_id=uuid4(),
        merchant_name=f"Test Merchant Ltd {uuid4().hex[:8]}",  # Make name unique
        mcc="5411",
        merchant_category="grocery",
        country="US",
        risk_rating=45,
        historical_fraud_rate=Decimal("0.025"),
        total_transactions=1000,
        total_volume=Decimal("50000.00"),
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestMerchantRepositoryCreate:
    """Test merchant creation operations."""

    async def test_create_merchant_success(
        self,
        merchant_repository: MerchantRepositoryImpl,
        sample_merchant: Merchant,
        async_session: AsyncSession,
    ):
        """Test successful merchant creation."""
        result = await merchant_repository.create(sample_merchant)
        await async_session.commit()

        assert result.merchant_id == sample_merchant.merchant_id
        assert result.merchant_name == sample_merchant.merchant_name
        assert result.mcc == sample_merchant.mcc
        assert result.risk_rating == sample_merchant.risk_rating

    async def test_create_merchant_duplicate_name(
        self,
        merchant_repository: MerchantRepositoryImpl,
        sample_merchant: Merchant,
        async_session: AsyncSession,
    ):
        """Test merchant creation with duplicate name."""
        await merchant_repository.create(sample_merchant)
        await async_session.commit()

        # Try to create another merchant with same name
        duplicate = Merchant(
            merchant_id=uuid4(),
            merchant_name=sample_merchant.merchant_name,
            mcc="5912",
            merchant_category="pharmacy",
            country="CA",
            risk_rating=30,
            historical_fraud_rate=Decimal("0.015"),
            total_transactions=500,
            total_volume=Decimal("25000.00"),
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with pytest.raises(MerchantNameExistsError):
            await merchant_repository.create(duplicate)

    async def test_create_merchant_with_special_characters(
        self,
        merchant_repository: MerchantRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test merchant creation with special characters in name."""
        merchant = Merchant(
            merchant_id=uuid4(),
            merchant_name="Café & Restaurant Spécialisé",
            mcc="5812",
            merchant_category="restaurant",
            country="FR",
            risk_rating=25,
            historical_fraud_rate=Decimal("0.010"),
            total_transactions=750,
            total_volume=Decimal("37500.00"),
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        result = await merchant_repository.create(merchant)
        await async_session.commit()

        assert result.merchant_name == merchant.merchant_name
        assert result.country == "FR"


class TestMerchantRepositoryRead:
    """Test merchant retrieval operations."""

    async def test_get_by_id_success(
        self,
        merchant_repository: MerchantRepositoryImpl,
        sample_merchant: Merchant,
        async_session: AsyncSession,
    ):
        """Test successful merchant retrieval by ID."""
        created = await merchant_repository.create(sample_merchant)
        await async_session.commit()

        result = await merchant_repository.get_by_id(created.merchant_id)

        assert result is not None
        assert result.merchant_id == sample_merchant.merchant_id
        assert result.merchant_name == sample_merchant.merchant_name

    async def test_get_by_id_not_found(self, merchant_repository: MerchantRepositoryImpl):
        """Test merchant retrieval with non-existent ID."""
        result = await merchant_repository.get_by_id(uuid4())
        assert result is None

    async def test_get_by_name_success(
        self,
        merchant_repository: MerchantRepositoryImpl,
        sample_merchant: Merchant,
        async_session: AsyncSession,
    ):
        """Test successful merchant retrieval by name."""
        await merchant_repository.create(sample_merchant)
        await async_session.commit()

        result = await merchant_repository.get_by_name(sample_merchant.merchant_name)

        assert result is not None
        assert result.merchant_name == sample_merchant.merchant_name
        assert result.merchant_id == sample_merchant.merchant_id

    async def test_get_by_name_not_found(self, merchant_repository: MerchantRepositoryImpl):
        """Test merchant retrieval with non-existent name."""
        result = await merchant_repository.get_by_name("Non-existent Merchant")
        assert result is None


class TestMerchantRepositoryUpdate:
    """Test merchant update operations."""

    async def test_update_merchant_success(
        self,
        merchant_repository: MerchantRepositoryImpl,
        sample_merchant: Merchant,
        async_session: AsyncSession,
    ):
        """Test successful merchant update."""
        created = await merchant_repository.create(sample_merchant)
        await async_session.commit()

        # Update merchant data
        created.risk_rating = 75
        created.merchant_category = "e-commerce"
        created.is_active = False

        result = await merchant_repository.update(created)
        await async_session.commit()

        assert result.risk_rating == 75
        assert result.merchant_category == "e-commerce"
        assert result.is_active is False

    async def test_update_merchant_not_found(
        self,
        merchant_repository: MerchantRepositoryImpl,
        sample_merchant: Merchant,
    ):
        """Test update of non-existent merchant."""
        sample_merchant.merchant_id = uuid4()  # Non-existent ID

        with pytest.raises(MerchantNotFoundError):
            await merchant_repository.update(sample_merchant)


class TestMerchantRepositoryDelete:
    """Test merchant deletion operations."""

    async def test_delete_merchant_success(
        self,
        merchant_repository: MerchantRepositoryImpl,
        sample_merchant: Merchant,
        async_session: AsyncSession,
    ):
        """Test successful merchant soft deletion."""
        created = await merchant_repository.create(sample_merchant)
        await async_session.commit()

        result = await merchant_repository.delete(created.merchant_id)
        await async_session.commit()

        assert result is True

        # Verify merchant is soft deleted (not retrievable)
        retrieved = await merchant_repository.get_by_id(created.merchant_id)
        assert retrieved is None

    async def test_delete_merchant_not_found(self, merchant_repository: MerchantRepositoryImpl):
        """Test deletion of non-existent merchant."""
        result = await merchant_repository.delete(uuid4())
        assert result is False


class TestMerchantRepositoryFiltering:
    """Test merchant filtering and search operations."""

    @pytest.fixture
    async def multiple_merchants(
        self,
        merchant_repository: MerchantRepositoryImpl,
        async_session: AsyncSession,
    ) -> list[Merchant]:
        """Create multiple merchants for filtering tests."""
        merchants = [
            Merchant(
                merchant_id=uuid4(),
                merchant_name="High Risk Merchant",
                mcc="7995",
                merchant_category="gambling",
                country="US",
                risk_rating=85,
                historical_fraud_rate=Decimal("0.08"),
                total_transactions=500,
                total_volume=Decimal("100000.00"),
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            Merchant(
                merchant_id=uuid4(),
                merchant_name="Low Risk Grocery",
                mcc="5411",
                merchant_category="grocery",
                country="CA",
                risk_rating=15,
                historical_fraud_rate=Decimal("0.005"),
                total_transactions=2000,
                total_volume=Decimal("75000.00"),
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            Merchant(
                merchant_id=uuid4(),
                merchant_name="Fashion Retailer",
                mcc="5651",
                merchant_category="retail",
                country="UK",
                risk_rating=45,
                historical_fraud_rate=Decimal("0.025"),
                total_transactions=1500,
                total_volume=Decimal("120000.00"),
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        ]

        created_merchants = []
        for merchant in merchants:
            created = await merchant_repository.create(merchant)
            created_merchants.append(created)

        await async_session.commit()
        return created_merchants

    async def test_list_by_category(
        self,
        merchant_repository: MerchantRepositoryImpl,
        multiple_merchants: list[Merchant],
    ):
        """Test listing merchants by category."""
        result = await merchant_repository.list_by_category("grocery")

        assert len(result) == 1
        assert result[0].merchant_category == "grocery"
        assert result[0].merchant_name == "Low Risk Grocery"

    async def test_list_by_mcc(
        self,
        merchant_repository: MerchantRepositoryImpl,
        multiple_merchants: list[Merchant],
    ):
        """Test listing merchants by MCC code."""
        result = await merchant_repository.list_by_mcc("5411")

        assert len(result) == 1
        assert result[0].mcc == "5411"

    async def test_list_by_country(
        self,
        merchant_repository: MerchantRepositoryImpl,
        multiple_merchants: list[Merchant],
    ):
        """Test listing merchants by country."""
        result = await merchant_repository.get_by_country("US")

        assert len(result) == 1
        assert result[0].country == "US"

    async def test_list_by_risk_level(
        self,
        merchant_repository: MerchantRepositoryImpl,
        multiple_merchants: list[Merchant],
    ):
        """Test listing merchants by risk level range."""
        result = await merchant_repository.list_by_risk_level(40, 90)

        assert len(result) == 2
        risk_ratings = [m.risk_rating for m in result]
        assert all(40 <= rating <= 90 for rating in risk_ratings)

    async def test_list_high_risk(
        self,
        merchant_repository: MerchantRepositoryImpl,
        multiple_merchants: list[Merchant],
    ):
        """Test listing high-risk merchants."""
        result = await merchant_repository.list_high_risk(min_risk_rating=80)

        assert len(result) == 1
        assert result[0].risk_rating >= 80

    async def test_count_by_risk_level(
        self,
        merchant_repository: MerchantRepositoryImpl,
        multiple_merchants: list[Merchant],
    ):
        """Test counting merchants by risk level."""
        count = await merchant_repository.count_by_risk_level(80)

        assert count == 1


class TestMerchantRepositoryComplexQueries:
    """Test complex merchant query operations."""

    async def test_find_by_criteria_comprehensive(
        self,
        merchant_repository: MerchantRepositoryImpl,
        sample_merchant: Merchant,
        async_session: AsyncSession,
    ):
        """Test comprehensive criteria-based search."""
        await merchant_repository.create(sample_merchant)
        await async_session.commit()

        result = await merchant_repository.find_by_criteria(
            country="US", min_risk_rating=30, max_risk_rating=60, is_active=True, limit=10
        )

        assert len(result) == 1
        assert result[0].merchant_id == sample_merchant.merchant_id

    async def test_find_by_criteria_name_pattern(
        self,
        merchant_repository: MerchantRepositoryImpl,
        sample_merchant: Merchant,
        async_session: AsyncSession,
    ):
        """Test name pattern search."""
        await merchant_repository.create(sample_merchant)
        await async_session.commit()

        result = await merchant_repository.find_by_criteria(name_pattern="Test Merchant", limit=10)

        assert len(result) == 1
        assert "Test Merchant" in result[0].merchant_name

    async def test_find_by_criteria_empty_result(
        self,
        merchant_repository: MerchantRepositoryImpl,
        sample_merchant: Merchant,
        async_session: AsyncSession,
    ):
        """Test criteria search with no matches."""
        await merchant_repository.create(sample_merchant)
        await async_session.commit()

        result = await merchant_repository.find_by_criteria(
            country="ZZ", limit=10  # Non-existent country
        )

        assert len(result) == 0


class TestMerchantRepositoryBulkOperations:
    """Test merchant bulk operations."""

    async def test_bulk_update_risk_rating(
        self,
        merchant_repository: MerchantRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test bulk risk rating update."""
        # Create multiple merchants
        merchants = []
        for i in range(3):
            merchant = Merchant(
                merchant_id=uuid4(),
                merchant_name=f"Merchant {i+1}",
                mcc="5411",
                merchant_category="grocery",
                country="US",
                risk_rating=30,
                historical_fraud_rate=Decimal("0.02"),
                total_transactions=1000,
                total_volume=Decimal("50000.00"),
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            created = await merchant_repository.create(merchant)
            merchants.append(created)

        await async_session.commit()

        # Bulk update risk ratings
        merchant_ids = [m.merchant_id for m in merchants]
        updated_count = await merchant_repository.bulk_update_risk_rating(merchant_ids, 75)
        await async_session.commit()

        assert updated_count == 3

        # Verify updates
        for merchant_id in merchant_ids:
            updated_merchant = await merchant_repository.get_by_id(merchant_id)
            assert updated_merchant.risk_rating == 75

    async def test_bulk_update_empty_list(self, merchant_repository: MerchantRepositoryImpl):
        """Test bulk update with empty ID list."""
        result = await merchant_repository.bulk_update_risk_rating([], 50)
        assert result == 0


class TestMerchantRepositoryStatistics:
    """Test merchant statistics operations."""

    async def test_get_statistics_by_category(
        self,
        merchant_repository: MerchantRepositoryImpl,
        sample_merchant: Merchant,
        async_session: AsyncSession,
    ):
        """Test getting merchant statistics by category."""
        await merchant_repository.create(sample_merchant)
        await async_session.commit()

        stats = await merchant_repository.get_statistics_by_category()

        assert "grocery" in stats
        category_stats = stats["grocery"]
        assert category_stats["merchant_count"] == 1
        assert category_stats["avg_risk_rating"] == 45.0
        assert category_stats["total_transactions"] == 1000


class TestMerchantRepositoryPagination:
    """Test merchant pagination operations."""

    async def test_pagination_offset_limit(
        self,
        merchant_repository: MerchantRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test pagination with offset and limit."""
        # Create multiple merchants
        for i in range(5):
            merchant = Merchant(
                merchant_id=uuid4(),
                merchant_name=f"Merchant {i+1}",
                mcc="5411",
                merchant_category="grocery",
                country="US",
                risk_rating=30 + i,
                historical_fraud_rate=Decimal("0.02"),
                total_transactions=1000,
                total_volume=Decimal("50000.00"),
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await merchant_repository.create(merchant)

        await async_session.commit()

        # Test pagination
        page1 = await merchant_repository.list_by_category("grocery", limit=2, offset=0)
        page2 = await merchant_repository.list_by_category("grocery", limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2

        # Verify no overlap
        page1_ids = {m.merchant_id for m in page1}
        page2_ids = {m.merchant_id for m in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestMerchantRepositoryEdgeCases:
    """Test merchant repository edge cases."""

    async def test_create_merchant_with_extreme_values(
        self,
        merchant_repository: MerchantRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test merchant creation with extreme values."""
        merchant = Merchant(
            merchant_id=uuid4(),
            merchant_name="Extreme Value Merchant",
            mcc="0000",
            merchant_category="test",
            country="XX",
            risk_rating=100,
            historical_fraud_rate=Decimal("1.0"),
            total_transactions=0,
            total_volume=Decimal("0.00"),
            is_active=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        result = await merchant_repository.create(merchant)
        await async_session.commit()

        assert result.risk_rating == 100
        assert result.historical_fraud_rate == Decimal("1.0")
        assert result.total_transactions == 0

    async def test_update_merchant_concurrency_safe(
        self,
        merchant_repository: MerchantRepositoryImpl,
        sample_merchant: Merchant,
        async_session: AsyncSession,
    ):
        """Test merchant update for concurrency safety."""
        created = await merchant_repository.create(sample_merchant)
        await async_session.commit()

        # Simulate concurrent update scenario
        created.risk_rating = 60
        result = await merchant_repository.update(created)
        await async_session.commit()

        # Verify update succeeded
        assert result.risk_rating == 60
        assert result.updated_at > result.created_at

    async def test_merchant_repository_error_handling(
        self,
        merchant_repository: MerchantRepositoryImpl,
    ):
        """Test repository error handling."""
        # Test with invalid UUID format would be caught by UUID validation
        # Test with None values would be caught by domain validation

        # These tests verify the repository handles domain-level errors properly
        with pytest.raises(MerchantNotFoundError):
            invalid_merchant = Merchant(
                merchant_id=uuid4(),
                merchant_name="Test",
                mcc="1234",
                merchant_category="test",
                country="US",
                risk_rating=50,
                historical_fraud_rate=Decimal("0.05"),
                total_transactions=100,
                total_volume=Decimal("1000.00"),
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await merchant_repository.update(invalid_merchant)
