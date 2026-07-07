"""Integration Tests for CustomerRepository.

Tests the SQLAlchemy repository implementation against a real database.
"""

from uuid import uuid4

import pytest
from src.domain.entities.customer import Customer
from src.infrastructure.database.repositories.customer_repository_impl import CustomerRepositoryImpl


@pytest.fixture
def customer_repository(test_db_session):
    """Create customer repository instance."""
    return CustomerRepositoryImpl(test_db_session)


class TestCustomerRepositoryCreate:
    """Test customer creation."""

    @pytest.mark.asyncio
    async def test_create_customer_success(
        self,
        customer_repository,
        sample_customer,
    ):
        """Test creating a customer."""
        # Act
        result = await customer_repository.create(sample_customer)

        # Assert
        assert result.customer_id == sample_customer.customer_id
        assert result.customer_name == "Jane Smith"
        assert result.email == "jane.smith@example.com"
        assert result.country == "CAN"
        assert result.kyc_status == "verified"
        assert result.credit_score == 780

    @pytest.mark.asyncio
    async def test_create_customer_persists_to_database(
        self,
        test_db_session,
        customer_repository,
        sample_customer,
    ):
        """Test that created customer is persisted."""
        # Act
        created = await customer_repository.create(sample_customer)
        await test_db_session.commit()

        # Retrieve directly from database
        retrieved = await customer_repository.get_by_id(created.customer_id)

        # Assert
        assert retrieved is not None
        assert retrieved.customer_id == created.customer_id
        assert retrieved.email == created.email


class TestCustomerRepositoryRead:
    """Test customer retrieval."""

    @pytest.mark.asyncio
    async def test_get_by_id_existing_customer(
        self,
        customer_repository,
        sample_customer,
    ):
        """Test retrieving existing customer by ID."""
        # Arrange
        created = await customer_repository.create(sample_customer)

        # Act
        result = await customer_repository.get_by_id(created.customer_id)

        # Assert
        assert result is not None
        assert result.customer_id == created.customer_id
        assert result.email == created.email

    @pytest.mark.asyncio
    async def test_get_by_id_nonexistent_customer(
        self,
        customer_repository,
    ):
        """Test retrieving non-existent customer returns None."""
        # Act
        result = await customer_repository.get_by_id(uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email_existing_customer(
        self,
        customer_repository,
        sample_customer,
    ):
        """Test retrieving customer by email."""
        # Arrange
        await customer_repository.create(sample_customer)

        # Act
        result = await customer_repository.get_by_email(sample_customer.email)

        # Assert
        assert result is not None
        assert result.email == sample_customer.email

    @pytest.mark.asyncio
    async def test_get_by_email_nonexistent_customer(
        self,
        customer_repository,
    ):
        """Test retrieving customer by non-existent email."""
        # Act
        result = await customer_repository.get_by_email("nonexistent@example.com")

        # Assert
        assert result is None


class TestCustomerRepositoryUpdate:
    """Test customer updates."""

    @pytest.mark.asyncio
    async def test_update_customer_success(
        self,
        customer_repository,
        sample_customer,
    ):
        """Test updating a customer."""
        # Arrange
        created = await customer_repository.create(sample_customer)
        created.customer_name = "Jane Doe"
        created.credit_score = 800

        # Act
        result = await customer_repository.update(created)

        # Assert
        assert result.customer_name == "Jane Doe"
        assert result.credit_score == 800

    @pytest.mark.asyncio
    async def test_update_nonexistent_customer_raises_error(
        self,
        customer_repository,
        sample_customer,
    ):
        """Test updating non-existent customer raises error."""
        # Arrange
        sample_customer.customer_id = uuid4()  # Non-existent ID

        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await customer_repository.update(sample_customer)


class TestCustomerRepositoryDelete:
    """Test customer deletion."""

    @pytest.mark.asyncio
    async def test_delete_customer_success(
        self,
        customer_repository,
        sample_customer,
    ):
        """Test soft deleting a customer."""
        # Arrange
        created = await customer_repository.create(sample_customer)

        # Act
        result = await customer_repository.delete(created.customer_id)

        # Assert
        assert result is True

        # Verify customer is soft deleted
        retrieved = await customer_repository.get_by_id(created.customer_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_customer(
        self,
        customer_repository,
    ):
        """Test deleting non-existent customer returns False."""
        # Act
        result = await customer_repository.delete(uuid4())

        # Assert
        assert result is False


class TestCustomerRepositoryList:
    """Test customer listing."""

    @pytest.mark.asyncio
    async def test_list_by_risk_category(
        self,
        customer_repository,
    ):
        """Test listing customers by risk category."""
        # Arrange
        customers = [
            Customer(
                customer_name=f"Customer {i}",
                email=f"customer{i}@example.com",
                country="USA",
                customer_risk_category="high" if i % 2 == 0 else "low",
            )
            for i in range(5)
        ]

        for customer in customers:
            await customer_repository.create(customer)

        # Act
        high_risk = await customer_repository.list_by_risk_category("high")
        low_risk = await customer_repository.list_by_risk_category("low")

        # Assert
        assert len(high_risk) == 3  # 0, 2, 4
        assert len(low_risk) == 2  # 1, 3
        assert all(c.customer_risk_category == "high" for c in high_risk)
        assert all(c.customer_risk_category == "low" for c in low_risk)

    @pytest.mark.asyncio
    async def test_list_by_kyc_status(
        self,
        customer_repository,
    ):
        """Test listing customers by KYC status."""
        # Arrange
        customers = [
            Customer(
                customer_name=f"Customer {i}",
                email=f"customer{i}@example.com",
                country="USA",
                kyc_status="verified" if i < 3 else "pending",
            )
            for i in range(5)
        ]

        for customer in customers:
            await customer_repository.create(customer)

        # Act
        verified = await customer_repository.list_by_kyc_status("verified")
        pending = await customer_repository.list_by_kyc_status("pending")

        # Assert
        assert len(verified) == 3
        assert len(pending) == 2
        assert all(c.kyc_status == "verified" for c in verified)
        assert all(c.kyc_status == "pending" for c in pending)

    @pytest.mark.asyncio
    async def test_list_high_risk(
        self,
        customer_repository,
    ):
        """Test listing high-risk customers."""
        # Arrange
        customers = [
            Customer(
                customer_name=f"Customer {i}",
                email=f"customer{i}@example.com",
                country="USA",
                customer_risk_category=["low", "medium", "high", "critical", "high"][i],
            )
            for i in range(5)
        ]

        for customer in customers:
            await customer_repository.create(customer)

        # Act
        high_risk = await customer_repository.list_high_risk()

        # Assert
        assert len(high_risk) == 3  # high, critical, high
        assert all(c.customer_risk_category in ["high", "critical"] for c in high_risk)

    @pytest.mark.asyncio
    async def test_count_by_risk_category(
        self,
        customer_repository,
    ):
        """Test counting customers by risk category."""
        # Arrange
        customers = [
            Customer(
                customer_name=f"Customer {i}",
                email=f"customer{i}@example.com",
                country="USA",
                customer_risk_category="high",
            )
            for i in range(7)
        ]

        for customer in customers:
            await customer_repository.create(customer)

        # Act
        count = await customer_repository.count_by_risk_category("high")

        # Assert
        assert count == 7

    @pytest.mark.asyncio
    async def test_list_with_pagination(
        self,
        customer_repository,
    ):
        """Test listing with pagination."""
        # Arrange
        customers = [
            Customer(
                customer_name=f"Customer {i}",
                email=f"customer{i}@example.com",
                country="USA",
                customer_risk_category="medium",
            )
            for i in range(10)
        ]

        for customer in customers:
            await customer_repository.create(customer)

        # Act
        page1 = await customer_repository.list_by_risk_category("medium", limit=5, offset=0)
        page2 = await customer_repository.list_by_risk_category("medium", limit=5, offset=5)

        # Assert
        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0].customer_id != page2[0].customer_id
