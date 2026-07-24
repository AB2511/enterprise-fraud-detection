"""Integration tests for merchant API endpoints."""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from src.presentation.api.dependencies import get_db
from src.presentation.main import create_application


@pytest.fixture
async def test_app(test_engine):
    """Create a FastAPI app with a database session override for tests."""
    app = create_application()

    async def override_get_db():
        async_session = sessionmaker(
            test_engine,
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
    """Create an async HTTP client for the test app."""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_create_merchant_success(async_client: AsyncClient):
    """Creating a merchant through the API should return the wrapped payload."""
    payload = {
        "merchant_name": "Northwind Electronics",
        "merchant_category": "5732",
        "country": "USA",
        "contact_email": "ops@northwind.example",
    }

    response = await async_client.post("/v1/merchants", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Merchant created successfully"
    assert data["data"]["merchant_name"] == payload["merchant_name"]
    assert data["data"]["country"] == payload["country"]
