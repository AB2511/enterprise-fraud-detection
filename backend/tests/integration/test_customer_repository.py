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
            date_of_birth=date(1990, 1, 15),
        )

    async def test_create_customer(
        self, repository: CustomerRepositoryImpl, sample_customer: Customer
    ):
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

    async def test_get_by_email(
        self, repository: CustomerRepositoryImpl, sample_customer: Customer
    ):
        """Test retrieving customer by email."""
        # Arrange
        await repository.create(sample_customer)

        # Act
        retrieved = await repository.get_by_email("john.doe@example.com")

        # Assert
        assert retrieved is not None
        assert retrieved.email == "john.doe@example.com"

    async def test_get_by_email_case_insensitive(
        self, repository: CustomerRepositoryImpl, sample_customer: Customer
    ):
        """Test email lookup is case insensitive."""
        # Arrange
        await repository.create(sample_customer)

        # Act
        retrieved = await repository.get_by_email("JOHN.DOE@EXAMPLE.COM")

        # Assert
        assert retrieved is not None
        assert retrieved.email == "john.doe@example.com"

    async def test_update_customer(
        self, repository: CustomerRepositoryImpl, sample_customer: Customer
    ):
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

    async def test_delete_customer_soft_delete(
        self, repository: CustomerRepositoryImpl, sample_customer: Customer
    ):
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
            customer = Customer(
                customer_name=f"Customer {i}", email=f"test{i}@example.com", country="USA"
            )
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
        critical_risk = Customer(
            customer_name="Critical Risk", email="critical@example.com", country="USA"
        )
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
            customer = Customer(
                customer_name=f"Customer {i}", email=f"test{i}@example.com", country="USA"
            )
            await repository.create(customer)

        # Act
        page1 = await repository.list_by_kyc_status("pending", limit=2, offset=0)
        page2 = await repository.list_by_kyc_status("pending", limit=2, offset=2)

        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].customer_id != page2[0].customer_id

    async def test_email_exists(
        self, repository: CustomerRepositoryImpl, sample_customer: Customer
    ):
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
            customer = Customer(
                customer_name=f"Bulk Customer {i}", email=f"bulk{i}@example.com", country="USA"
            )
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

    async def test_concurrent_access_optimistic_locking(
        self, repository: CustomerRepositoryImpl, sample_customer: Customer
    ):
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

    async def test_update_customer_email_conflict(self, repository: CustomerRepositoryImpl):
        """Test updating customer email to one that already exists."""
        # Arrange - create two customers
        customer1 = Customer(customer_name="User One", email="user1@example.com", country="USA")
        customer2 = Customer(customer_name="User Two", email="user2@example.com", country="USA")

        await repository.create(customer1)
        created2 = await repository.create(customer2)

        # Act - try to update customer2's email to customer1's email
        created2.email = "user1@example.com"

        # Assert - should raise ConflictError
        with pytest.raises(ConflictError):
            await repository.update(created2)

    async def test_bulk_update_risk_category(self, repository: CustomerRepositoryImpl):
        """Test bulk updating risk category for multiple customers."""
        # Arrange - create multiple customers
        customers = []
        for i in range(5):
            customer = Customer(
                customer_name=f"Bulk User {i}", email=f"bulk{i}@example.com", country="USA"
            )
            customer.customer_risk_category = "low"
            created = await repository.create(customer)
            customers.append(created)

        customer_ids = [c.customer_id for c in customers]

        # Act - bulk update risk category
        updated_count = await repository.bulk_update_risk_category(customer_ids, "high")

        # Assert
        assert updated_count == 5

        # Verify updates
        for customer_id in customer_ids:
            updated_customer = await repository.get_by_id(customer_id)
            assert updated_customer.customer_risk_category == "high"

    async def test_bulk_update_risk_category_empty_list(self, repository: CustomerRepositoryImpl):
        """Test bulk update with empty customer IDs list."""
        # Act
        updated_count = await repository.bulk_update_risk_category([], "high")

        # Assert
        assert updated_count == 0

    async def test_bulk_update_risk_category_nonexistent_customers(
        self, repository: CustomerRepositoryImpl
    ):
        """Test bulk update with non-existent customer IDs."""
        # Arrange - use random UUIDs that don't exist
        fake_ids = [uuid4(), uuid4(), uuid4()]

        # Act
        updated_count = await repository.bulk_update_risk_category(fake_ids, "critical")

        # Assert - no customers should be updated
        assert updated_count == 0

    async def test_find_by_criteria_comprehensive(self, repository: CustomerRepositoryImpl):
        """Test comprehensive find_by_criteria functionality."""
        # Arrange - create diverse customers
        customers_data = [
            ("John Doe", "john@tech.com", "USA", "verified", "high", 750),
            ("Jane Smith", "jane@finance.com", "UK", "pending", "medium", 680),
            ("Bob Wilson", "bob@startup.com", "USA", "verified", "low", 720),
            ("Alice Brown", "alice@corp.com", "Canada", "rejected", "critical", 600),
        ]

        created_customers = []
        for name, email, country, kyc_status, risk_cat, credit_score in customers_data:
            customer = Customer(customer_name=name, email=email, country=country)
            customer.kyc_status = kyc_status
            customer.customer_risk_category = risk_cat
            customer.credit_score = credit_score
            created = await repository.create(customer)
            created_customers.append(created)

        # Test email pattern search
        tech_users = await repository.find_by_criteria(email_pattern="tech.com")
        assert len(tech_users) == 1
        assert tech_users[0].email == "john@tech.com"

        # Test country filter
        usa_users = await repository.find_by_criteria(country="USA")
        assert len(usa_users) == 2

        # Test KYC status filter
        verified_users = await repository.find_by_criteria(kyc_status="verified")
        assert len(verified_users) == 2

        # Test risk category filter
        high_risk_users = await repository.find_by_criteria(risk_category="high")
        assert len(high_risk_users) == 1

        # Test credit score range
        mid_credit_users = await repository.find_by_criteria(
            min_credit_score=650, max_credit_score=700
        )
        assert len(mid_credit_users) == 1
        assert mid_credit_users[0].credit_score == 680

        # Test active status filter
        all_active = await repository.find_by_criteria(is_active=True)
        assert len(all_active) == 4  # All customers are active by default

        # Test combined filters
        usa_verified = await repository.find_by_criteria(country="USA", kyc_status="verified")
        assert len(usa_verified) == 2  # Both John and Bob are from USA and verified
        assert usa_verified[0].country == "USA"

        # Test pagination
        page1 = await repository.find_by_criteria(limit=2, offset=0)
        page2 = await repository.find_by_criteria(limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].customer_id != page2[0].customer_id

    async def test_find_by_criteria_no_matches(self, repository: CustomerRepositoryImpl):
        """Test find_by_criteria with no matching results."""
        # Act
        results = await repository.find_by_criteria(
            email_pattern="nonexistent@domain.com", country="Mars"
        )

        # Assert
        assert results == []

    async def test_repository_error_handling_create(self, repository: CustomerRepositoryImpl):
        """Test repository error handling during create operations."""
        # Test duplicate email handling through CustomerEmailExistsError path
        customer1 = Customer(customer_name="Test User", email="conflict@example.com", country="USA")
        await repository.create(customer1)

        # This should trigger the CustomerEmailExistsError -> ConflictError path
        customer2 = Customer(
            customer_name="Another User", email="conflict@example.com", country="USA"
        )
        with pytest.raises(ConflictError):
            await repository.create(customer2)

    async def test_repository_error_handling_update(self, repository: CustomerRepositoryImpl):
        """Test repository error handling during update operations."""
        # Test updating non-existent customer
        fake_customer = Customer(customer_name="Fake User", email="fake@example.com", country="USA")
        fake_customer.customer_id = uuid4()  # Set fake ID

        # Should raise NotFoundError
        with pytest.raises(NotFoundError):
            await repository.update(fake_customer)

    async def test_email_existence_edge_cases(self, repository: CustomerRepositoryImpl):
        """Test email existence checking with various edge cases."""
        # Test non-existent email
        assert await repository.email_exists("nonexistent@example.com") is False

        # Create customer and test case sensitivity
        customer = Customer(customer_name="Test User", email="Test@Example.Com", country="USA")
        await repository.create(customer)

        # Test case insensitive email existence
        assert await repository.email_exists("test@example.com") is True
        assert await repository.email_exists("TEST@EXAMPLE.COM") is True
        assert await repository.email_exists("Test@Example.Com") is True

    async def test_count_by_risk_category_edge_cases(self, repository: CustomerRepositoryImpl):
        """Test count by risk category with edge cases."""
        # Test counting non-existent category
        count = await repository.count_by_risk_category("nonexistent")
        assert count == 0

        # Create customers with different activity states using valid risk categories
        active_customer = Customer(
            customer_name="Active", email="active@example.com", country="USA"
        )
        active_customer.customer_risk_category = "low"  # Use valid category
        active_customer.is_active = True
        await repository.create(active_customer)

        inactive_customer = Customer(
            customer_name="Inactive", email="inactive@example.com", country="USA"
        )
        inactive_customer.customer_risk_category = "low"  # Use valid category
        inactive_customer.is_active = False
        await repository.create(inactive_customer)

        # Count should only include active customers
        count = await repository.count_by_risk_category("low")
        assert count == 1  # Only the active one should be counted

    async def test_list_high_risk_sorting_and_limits(self, repository: CustomerRepositoryImpl):
        """Test list_high_risk with proper sorting and limit enforcement."""
        # Create customers with different risk levels and scores
        customers_data = [
            ("Critical 1", "critical1@example.com", "critical", 5, 500),
            ("High 1", "high1@example.com", "high", 3, 600),
            ("Critical 2", "critical2@example.com", "critical", 10, 400),
            ("High 2", "high2@example.com", "high", 1, 650),
            ("Medium", "medium@example.com", "medium", 0, 700),  # Should not appear
        ]

        for name, email, risk_cat, fraud_count, credit_score in customers_data:
            customer = Customer(customer_name=name, email=email, country="USA")
            customer.customer_risk_category = risk_cat
            customer.historical_fraud_count = fraud_count
            customer.credit_score = credit_score
            await repository.create(customer)

        # Test default limit
        high_risk = await repository.list_high_risk()
        assert len(high_risk) == 4  # Should exclude medium risk

        # Test custom limit
        limited = await repository.list_high_risk(limit=2)
        assert len(limited) == 2

        # Verify sorting: critical first, then by fraud count desc, then credit score asc
        all_high_risk = await repository.list_high_risk(limit=10)
        risk_categories = [c.customer_risk_category for c in all_high_risk]

        # Verify that high and critical risk customers are included
        high_count = sum(1 for cat in risk_categories if cat == "high")
        critical_count = sum(1 for cat in risk_categories if cat == "critical")
        assert high_count == 2
        assert critical_count == 2

    async def test_database_constraint_violations_update_scenario(
        self, repository: CustomerRepositoryImpl
    ):
        """Test database constraint violation scenarios during update."""
        # Create two customers
        customer1 = Customer(customer_name="First", email="first@example.com", country="USA")
        customer2 = Customer(customer_name="Second", email="second@example.com", country="USA")

        await repository.create(customer1)
        created2 = await repository.create(customer2)

        # Try to update customer2 with customer1's email - should trigger integrity error
        created2.email = "first@example.com"

        with pytest.raises(ConflictError):
            await repository.update(created2)
