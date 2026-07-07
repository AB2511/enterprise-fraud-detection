"""Integration Tests for Customer API Endpoints.

Tests the full API stack including routes, use cases, services, and repositories.
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from src.presentation.api.dependencies import get_db
from src.presentation.main import create_application


@pytest.fixture
async def test_app(test_db_engine):
    """Create test FastAPI application."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    app = create_application()

    # Override database dependency to create fresh session per request
    async def override_get_db():
        async_session = sessionmaker(
            test_db_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    return app


@pytest.fixture
async def async_client(test_app):
    """Create async HTTP client for testing."""
    from httpx import ASGITransport

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        yield client


class TestCreateCustomerAPI:
    """Test POST /v1/customers endpoint."""

    @pytest.mark.asyncio
    async def test_create_customer_success(self, async_client: AsyncClient):
        """Test creating a customer successfully."""
        # Arrange
        payload = {
            "customer_name": "Alice Johnson",
            "email": "alice.johnson@example.com",
            "country": "USA",
            "date_of_birth": "1992-08-15",
        }

        # Act
        response = await async_client.post("/v1/customers", json=payload)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["success"] is True
        assert data["message"] == "Customer created successfully"
        assert data["data"]["customer_name"] == "Alice Johnson"
        assert data["data"]["email"] == "alice.johnson@example.com"
        assert data["data"]["country"] == "USA"
        assert data["data"]["kyc_status"] == "pending"
        assert data["data"]["is_active"] is True
        assert "customer_id" in data["data"]
        assert "metadata" in data
        assert "request_id" in data["metadata"]

    @pytest.mark.asyncio
    async def test_create_customer_without_dob(self, async_client: AsyncClient):
        """Test creating customer without date of birth."""
        # Arrange
        payload = {
            "customer_name": "Bob Smith",
            "email": "bob.smith@example.com",
            "country": "CAN",
        }

        # Act
        response = await async_client.post("/v1/customers", json=payload)

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_create_customer_duplicate_email(self, async_client: AsyncClient):
        """Test creating customer with duplicate email."""
        # Arrange
        payload = {
            "customer_name": "Charlie Brown",
            "email": "charlie@example.com",
            "country": "USA",
        }

        # Create first customer
        await async_client.post("/v1/customers", json=payload)

        # Act - Try to create duplicate
        response = await async_client.post("/v1/customers", json=payload)

        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert data["type"] == "conflict"
        assert "email" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_customer_invalid_email(self, async_client: AsyncClient):
        """Test creating customer with invalid email."""
        # Arrange
        payload = {
            "customer_name": "David Lee",
            "email": "invalid-email",
            "country": "USA",
        }

        # Act
        response = await async_client.post("/v1/customers", json=payload)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_customer_missing_required_fields(self, async_client: AsyncClient):
        """Test creating customer with missing required fields."""
        # Arrange
        payload = {
            "customer_name": "Eve Wilson",
            # Missing email and country
        }

        # Act
        response = await async_client.post("/v1/customers", json=payload)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_customer_invalid_country_code(self, async_client: AsyncClient):
        """Test creating customer with invalid country code."""
        # Arrange
        payload = {
            "customer_name": "Frank Miller",
            "email": "frank@example.com",
            "country": "X",  # Too short
        }

        # Act
        response = await async_client.post("/v1/customers", json=payload)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetCustomerAPI:
    """Test GET /v1/customers/{customer_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_customer_success(self, async_client: AsyncClient):
        """Test retrieving existing customer."""
        # Arrange - Create customer first
        create_payload = {
            "customer_name": "Grace Hopper",
            "email": "grace@example.com",
            "country": "USA",
        }
        create_response = await async_client.post("/v1/customers", json=create_payload)
        customer_id = create_response.json()["data"]["customer_id"]

        # Act
        response = await async_client.get(f"/v1/customers/{customer_id}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["data"]["customer_id"] == customer_id
        assert data["data"]["customer_name"] == "Grace Hopper"
        assert data["data"]["email"] == "grace@example.com"

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, async_client: AsyncClient):
        """Test retrieving non-existent customer."""
        # Arrange
        nonexistent_id = str(uuid4())

        # Act
        response = await async_client.get(f"/v1/customers/{nonexistent_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["type"] == "entity-not-found"

    @pytest.mark.asyncio
    async def test_get_customer_invalid_uuid(self, async_client: AsyncClient):
        """Test retrieving customer with invalid UUID."""
        # Act
        response = await async_client.get("/v1/customers/invalid-uuid")

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUpdateCustomerAPI:
    """Test PUT /v1/customers/{customer_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_customer_success(self, async_client: AsyncClient):
        """Test updating customer successfully."""
        # Arrange - Create customer first
        create_payload = {
            "customer_name": "Henry Ford",
            "email": "henry@example.com",
            "country": "USA",
        }
        create_response = await async_client.post("/v1/customers", json=create_payload)
        customer_id = create_response.json()["data"]["customer_id"]

        # Act
        update_payload = {
            "customer_name": "Henry Ford Jr",
            "credit_score": 800,
        }
        response = await async_client.put(f"/v1/customers/{customer_id}", json=update_payload)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert data["data"]["customer_name"] == "Henry Ford Jr"
        assert data["data"]["credit_score"] == 800

    @pytest.mark.asyncio
    async def test_update_customer_partial(self, async_client: AsyncClient):
        """Test partial customer update."""
        # Arrange - Create customer
        create_payload = {
            "customer_name": "Irene Curie",
            "email": "irene@example.com",
            "country": "FRA",
        }
        create_response = await async_client.post("/v1/customers", json=create_payload)
        customer_id = create_response.json()["data"]["customer_id"]

        # Act - Update only credit score
        update_payload = {"credit_score": 720}
        response = await async_client.put(f"/v1/customers/{customer_id}", json=update_payload)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["credit_score"] == 720
        assert data["data"]["customer_name"] == "Irene Curie"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_customer_not_found(self, async_client: AsyncClient):
        """Test updating non-existent customer."""
        # Arrange
        nonexistent_id = str(uuid4())
        update_payload = {"credit_score": 750}

        # Act
        response = await async_client.put(f"/v1/customers/{nonexistent_id}", json=update_payload)

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_customer_invalid_credit_score(self, async_client: AsyncClient):
        """Test updating with invalid credit score."""
        # Arrange - Create customer
        create_payload = {
            "customer_name": "Jack London",
            "email": "jack@example.com",
            "country": "USA",
        }
        create_response = await async_client.post("/v1/customers", json=create_payload)
        customer_id = create_response.json()["data"]["customer_id"]

        # Act - Invalid credit score (out of range)
        update_payload = {"credit_score": 1000}  # Max is 850
        response = await async_client.put(f"/v1/customers/{customer_id}", json=update_payload)

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDeleteCustomerAPI:
    """Test DELETE /v1/customers/{customer_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_customer_success(self, async_client: AsyncClient):
        """Test deleting customer successfully."""
        # Arrange - Create customer
        create_payload = {
            "customer_name": "Karen White",
            "email": "karen@example.com",
            "country": "GBR",
        }
        create_response = await async_client.post("/v1/customers", json=create_payload)
        customer_id = create_response.json()["data"]["customer_id"]

        # Act
        response = await async_client.delete(f"/v1/customers/{customer_id}")

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify customer is deleted
        get_response = await async_client.get(f"/v1/customers/{customer_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_customer_with_reason(self, async_client: AsyncClient):
        """Test deleting customer with custom reason."""
        # Arrange - Create customer
        create_payload = {
            "customer_name": "Laura Palmer",
            "email": "laura@example.com",
            "country": "USA",
        }
        create_response = await async_client.post("/v1/customers", json=create_payload)
        customer_id = create_response.json()["data"]["customer_id"]

        # Act
        response = await async_client.delete(
            f"/v1/customers/{customer_id}",
            params={"reason": "Compliance violation"},
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_customer_not_found(self, async_client: AsyncClient):
        """Test deleting non-existent customer."""
        # Arrange
        nonexistent_id = str(uuid4())

        # Act
        response = await async_client.delete(f"/v1/customers/{nonexistent_id}")

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCustomerAPIEndToEnd:
    """End-to-end tests for customer workflow."""

    @pytest.mark.asyncio
    async def test_complete_customer_lifecycle(self, async_client: AsyncClient):
        """Test complete CRUD lifecycle for a customer."""
        # Create
        create_payload = {
            "customer_name": "Michael Jordan",
            "email": "mj@example.com",
            "country": "USA",
            "date_of_birth": "1963-02-17",
        }
        create_response = await async_client.post("/v1/customers", json=create_payload)
        assert create_response.status_code == status.HTTP_201_CREATED
        customer_id = create_response.json()["data"]["customer_id"]

        # Read
        get_response = await async_client.get(f"/v1/customers/{customer_id}")
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["data"]["email"] == "mj@example.com"

        # Update
        update_payload = {"customer_name": "Michael Jeffrey Jordan", "credit_score": 850}
        update_response = await async_client.put(
            f"/v1/customers/{customer_id}", json=update_payload
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["data"]["customer_name"] == "Michael Jeffrey Jordan"
        assert update_response.json()["data"]["credit_score"] == 850

        # Delete
        delete_response = await async_client.delete(f"/v1/customers/{customer_id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deleted
        verify_response = await async_client.get(f"/v1/customers/{customer_id}")
        assert verify_response.status_code == status.HTTP_404_NOT_FOUND
