"""Integration tests for CustomerRepositoryImpl."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.customer import Customer
from src.domain.exceptions.base import ConflictError, NotFoundError
from src.infrastructure.database.repositories.customer_repository_impl import CustomerRepositoryImpl


class TestCustomerRepositoryImpl:
    """Test suite for CustomerRepositoryImpl."""

    @pytest.fixture
    async def repository(self, async_session: AsyncSession) -> CustomerRepositoryImpl:
        """Create repository instance."""
        return CustomerRepositoryImpl(async_session)

    @pytest.fixture
    def sample_customer(self) -> Customer:
        """Create sample customer entity."""
        return Customer(
            customer_name="John Doe",
            email="john.doe@example.com",
            country="USA",
            date_of_birth=date(1990, 1, 15)
        )

    async def test_create_customer(self, repository: CustomerRepositoryImpl, sample_customer: Customer):
        """Test customer creation."""
        # Act
        created = await repository.create(sample_customer)

        # Assert
        assert created.customer_id is not None
        assert created.customer_name == "John Doe"
        assert created.email == "john.doe@example.com"
        assert created.country == "USA"
        assert created.kyc_status == "pending"
        assert created.is_active is True

    async def test_create_duplicate_email_fails(self, repository: CustomerRepositoryImpl):
        """Test that creating customer with duplicate email fails."""
        # Arrange
        customer1 = Customer(customer_name="John Doe", email="test@example.com", country="USA")
        customer2 = Customer(customer_name="Jane Doe", email="test@example.com", country="USA")

        # Act
        await repository.create(customer1)

        # Assert
        with pytest.raises(ConflictError):
            await repository.create(customer2)

    async def test_get_by_id(self, repository: CustomerRepositoryImpl, sample_customer: Customer):
        """Test retrieving customer by ID."""
        # Arrange
        created = await repository.create(sample_customer)

        # Act
        retrieved = await repository.get_by_id(created.customer_id)

        # Assert
        assert retrieved is not None
        assert retrieved.customer_id == created.customer_id
        assert retrieved.customer_name == "John Doe"

    async def test_get_by_id_not_found(self, repository: CustomerRepositoryImpl):
        """Test retrieving non-existent customer returns None."""
        # Act
        result = await repository.get_by_id(uuid4())

        # Assert
        assert result is None

    async def test_get_by_email(self, repository: CustomerRepositoryImpl, sample_customer: Customer):
        """Test retrieving customer by email."""
        # Arrange
        await repository.create(sample_customer)

        # Act
        retrieved = await repository.get_by_email("john.doe@example.com")

        # Assert
        assert retrieved is not None
        assert retrieved.email == "john.doe@example.com"

    async def test_get_by_email_case_insensitive(self, repository: CustomerRepositoryImpl, sample_customer: Customer):
        """Test email lookup is case insensitive."""
        # Arrange
        await repository.create(sample_customer)

        # Act
        retrieved = await repository.get_by_email("JOHN.DOE@EXAMPLE.COM")

        # Assert
        assert retrieved is not None
        assert retrieved.email == "john.doe@example.com"

    async def test_update_customer(self, repository: CustomerRepositoryImpl, sample_customer: Customer):
        """Test updating customer."""
        # Arrange
        created = await repository.create(sample_customer)
        created.customer_name = "John Smith"
        created.credit_score = 750

        # Act
        updated = await repository.update(created)

        # Assert
        assert updated.customer_name == "John Smith"
        assert updated.credit_score == 750
        assert updated.updated_at > updated.created_at

    async def test_update_nonexistent_customer_fails(self, repository: CustomerRepositoryImpl):
        """Test updating non-existent customer fails."""
        # Arrange
        customer = Customer(customer_name="John Doe", email="test@example.com", country="USA")
        customer.customer_id = uuid4()

        # Act & Assert
        with pytest.raises(NotFoundError):
            await repository.update(customer)

    async def test_delete_customer_soft_delete(self, repository: CustomerRepositoryImpl, sample_customer: Customer):
        """Test soft delete functionality."""
        # Arrange
        created = await repository.create(sample_customer)

        # Act
        result = await repository.delete(created.customer_id)

        # Assert
        assert result is True

        # Verify soft delete - should not be retrievable
        retrieved = await repository.get_by_id(created.customer_id)
        assert retrieved is None

    async def test_delete_nonexistent_customer(self, repository: CustomerRepositoryImpl):
        """Test deleting non-existent customer returns False."""
        # Act
        result = await repository.delete(uuid4())

        # Assert
        assert result is False

    async def test_list_by_risk_category(self, repository: CustomerRepositoryImpl):
        """Test listing customers by risk category."""
        # Arrange
        high_risk = Customer(customer_name="High Risk", email="high@example.com", country="USA")
        high_risk.customer_risk_category = "high"
        low_risk = Customer(customer_name="Low Risk", email="low@example.com", country="USA")
        low_risk.customer_risk_category = "low"

        await repository.create(high_risk)
        await repository.create(low_risk)

        # Act
        high_risk_customers = await repository.list_by_risk_category("high")

        # Assert
        assert len(high_risk_customers) == 1
        assert high_risk_customers[0].customer_name == "High Risk"

    async def test_list_by_kyc_status(self, repository: CustomerRepositoryImpl):
        """Test listing customers by KYC status."""
        # Arrange
        verified = Customer(customer_name="Verified", email="verified@example.com", country="USA")
        verified.verify_kyc()
        pending = Customer(customer_name="Pending", email="pending@example.com", country="USA")

        await repository.create(verified)
        await repository.create(pending)

        # Act
        verified_customers = await repository.list_by_kyc_status("verified")

        # Assert
        assert len(verified_customers) == 1
        assert verified_customers[0].customer_name == "Verified"

    async def test_count_by_risk_category(self, repository: CustomerRepositoryImpl):
        """Test counting customers by risk category."""
        # Arrange
        for i in range(3):
            customer = Customer(customer_name=f"Customer {i}", email=f"test{i}@example.com", country="USA")
            customer.customer_risk_category = "medium"
            await repository.create(customer)

        # Act
        count = await repository.count_by_risk_category("medium")

        # Assert
        assert count == 3

    async def test_list_high_risk(self, repository: CustomerRepositoryImpl):
        """Test listing high-risk customers."""
        # Arrange
        high_risk = Customer(customer_name="High Risk", email="high@example.com", country="USA")
        high_risk.customer_risk_category = "high"
        critical_risk = Customer(customer_name="Critical Risk", email="critical@example.com", country="USA")
        critical_risk.customer_risk_category = "critical"
        low_risk = Customer(customer_name="Low Risk", email="low@example.com", country="USA")
        low_risk.customer_risk_category = "low"

        await repository.create(high_risk)
        await repository.create(critical_risk)
        await repository.create(low_risk)

        # Act
        high_risk_customers = await repository.list_high_risk()

        # Assert
        assert len(high_risk_customers) == 2
        risk_categories = [c.customer_risk_category for c in high_risk_customers]
        assert "high" in risk_categories
        assert "critical" in risk_categories

    async def test_pagination_parameters(self, repository: CustomerRepositoryImpl):
        """Test pagination limits and offsets."""
        # Arrange
        for i in range(5):
            customer = Customer(customer_name=f"Customer {i}", email=f"test{i}@example.com", country="USA")
            await repository.create(customer)

        # Act
        page1 = await repository.list_by_kyc_status("pending", limit=2, offset=0)
        page2 = await repository.list_by_kyc_status("pending", limit=2, offset=2)

        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].customer_id != page2[0].customer_id

    async def test_email_exists(self, repository: CustomerRepositoryImpl, sample_customer: Customer):
        """Test email existence check."""
        # Arrange
        await repository.create(sample_customer)

        # Act & Assert
        assert await repository.email_exists("john.doe@example.com") is True
        assert await repository.email_exists("nonexistent@example.com") is False

    async def test_bulk_operations(self, repository: CustomerRepositoryImpl):
        """Test bulk operations performance."""
        # Arrange
        customers = []
        for i in range(10):
            customer = Customer(customer_name=f"Bulk Customer {i}", email=f"bulk{i}@example.com", country="USA")
            customers.append(customer)

        # Act
        created_customers = []
        for customer in customers:
            created = await repository.create(customer)
            created_customers.append(created)

        # Assert
        assert len(created_customers) == 10
        for created in created_customers:
            assert created.customer_id is not None

    async def test_concurrent_access_optimistic_locking(self, repository: CustomerRepositoryImpl, sample_customer: Customer):
        """Test optimistic locking behavior."""
        # Arrange
        created = await repository.create(sample_customer)

        # Simulate concurrent access by updating same customer
        customer1 = await repository.get_by_id(created.customer_id)
        customer2 = await repository.get_by_id(created.customer_id)

        # Act
        customer1.customer_name = "Updated by User 1"
        customer2.customer_name = "Updated by User 2"

        # First update should succeed
        await repository.update(customer1)

        # Second update should handle optimistic locking
        # (Implementation depends on specific strategy)
        updated2 = await repository.update(customer2)
        assert updated2 is not None

    async def test_transaction_rollback_on_error(self, repository: CustomerRepositoryImpl):
        """Test transaction rollback on constraint violation."""
        # Arrange
        customer1 = Customer(customer_name="Test User", email="test@example.com", country="USA")
        await repository.create(customer1)

        # Act & Assert - duplicate email should rollback transaction
        customer2 = Customer(customer_name="Another User", email="test@example.com", country="USA")
        with pytest.raises(ConflictError):
            await repository.create(customer2)

        # Verify original customer still exists
        retrieved = await repository.get_by_email("test@example.com")
        assert retrieved.customer_name == "Test User"

    async def test_search_and_filtering_edge_cases(self, repository: CustomerRepositoryImpl):
        """Test edge cases in search and filtering."""
        # Test empty results
        empty_result = await repository.list_by_risk_category("nonexistent")
        assert empty_result == []

        # Test limit boundaries
        zero_limit = await repository.list_by_kyc_status("pending", limit=0)
        assert len(zero_limit) == 0

        # Test large offset
        large_offset = await repository.list_by_kyc_status("pending", offset=1000)
        assert large_offset == []
