"""Debug test for delete functionality."""

import pytest
from httpx import AsyncClient
from fastapi import status

from src.infrastructure.database.models import CustomerModel
from src.presentation.api.dependencies import get_db
from src.presentation.main import create_application


@pytest.fixture
async def test_app(test_db_engine):
    """Create test FastAPI application."""
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.asyncio import AsyncSession
    
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
    
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test"
    ) as client:
        yield client


class TestDeleteDebug:
    """Debug delete behavior."""

    @pytest.mark.asyncio
    async def test_delete_debug(self, async_client: AsyncClient, test_db_engine):
        """Debug what happens during delete."""
        from sqlalchemy import select, text
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.ext.asyncio import AsyncSession
        from src.infrastructure.database.models import CustomerModel
        
        # Create customer
        create_payload = {
            "customer_name": "Debug User",
            "email": "debug@example.com",
            "country": "USA",
        }
        create_response = await async_client.post("/v1/customers", json=create_payload)
        assert create_response.status_code == status.HTTP_201_CREATED
        customer_id_str = create_response.json()["data"]["customer_id"]
        
        from uuid import UUID
        customer_id = UUID(customer_id_str)
        
        # Create a fresh session for direct DB queries
        async_session = sessionmaker(
            test_db_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Check database before delete
        async with async_session() as session:
            stmt = select(CustomerModel).where(CustomerModel.id == customer_id)
            result = await session.execute(stmt)
            before_delete = result.scalar_one_or_none()
            print(f"\nBEFORE DELETE: deleted_at = {before_delete.deleted_at if before_delete else 'NOT FOUND'}")
        
        # Delete
        delete_response = await async_client.delete(f"/v1/customers/{customer_id_str}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        
        # Check database after delete - use fresh session
        async with async_session() as session:
            stmt2 = select(CustomerModel).where(CustomerModel.id == customer_id)
            result2 = await session.execute(stmt2)
            after_delete = result2.scalar_one_or_none()
            print(f"AFTER DELETE: deleted_at = {after_delete.deleted_at if after_delete else 'NOT FOUND'}")
        
        # Try to get via API
        get_response = await async_client.get(f"/v1/customers/{customer_id_str}")
        print(f"GET STATUS: {get_response.status_code}")
        if get_response.status_code == 200:
            print(f"GET DATA: {get_response.json()['data']}")
