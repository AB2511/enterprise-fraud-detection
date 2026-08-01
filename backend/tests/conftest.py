"""Test configuration and fixtures."""

import asyncio
import sys
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
from src.domain.entities.prediction import Prediction
from src.domain.entities.user import User
from src.infrastructure.database.models import Base

# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for Windows compatibility with Python 3.13+."""
    if sys.platform == "win32":
        # Use WindowsProactorEventLoopPolicy for Windows
        policy = asyncio.WindowsProactorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        return policy
    return asyncio.get_event_loop_policy()


@pytest_asyncio.fixture(scope="session")
async def test_engine(event_loop_policy):
    """Create test database engine with aiosqlite compatibility fix."""
    # Create engine - aiosqlite has compatibility issues with create_function
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Remove all existing 'connect' listeners that SQLAlchemy's SQLite dialect adds
    # These try to call create_function() which aiosqlite doesn't support
    from sqlalchemy import event
    from sqlalchemy.pool import Pool
    
    # Clear the problematic listeners before they fire
    if hasattr(engine.sync_engine.dialect, 'on_connect'):
        # Override the on_connect to return None, preventing regexp registration
        original_on_connect = engine.sync_engine.dialect.on_connect
        engine.sync_engine.dialect.on_connect = lambda: None

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(async_session: AsyncSession, test_engine):
    """Clean database before each test."""
    # Clean all tables before test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Rollback any uncommitted changes after test
    await async_session.rollback()


# Repository test configuration


@pytest_asyncio.fixture
async def multiple_predictions(
    async_session: AsyncSession,
) -> list[Prediction]:
    """Create multiple predictions for testing analytics and queries."""

    from src.infrastructure.database.repositories.prediction_repository_impl import (
        PredictionRepositoryImpl,
    )

    repo = PredictionRepositoryImpl(async_session)

    predictions = [
        # For test_find_by_criteria_comprehensive: v1.2.0 + fraud_prob>=0.8 + decline
        Prediction(
            prediction_id=uuid4(),
            transaction_id=uuid4(),
            model_version="v1.2.0",
            fraud_probability=0.85,
            anomaly_score=0.65,
            risk_score=85,
            predicted_class="fraud",
            decision="decline",
            confidence=0.92,
            explanation_data={},
            latency_ms=150,
            timestamp=datetime.now(UTC),
            analyst_feedback_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        # For test_count_by_decision: approve decision
        # For test_find_by_criteria_prediction_class: legitimate
        Prediction(
            prediction_id=uuid4(),
            transaction_id=uuid4(),
            model_version="v1.2.0",
            fraud_probability=0.25,
            anomaly_score=0.15,
            risk_score=30,
            predicted_class="legitimate",
            decision="approve",
            confidence=0.85,
            explanation_data={},
            latency_ms=75,
            timestamp=datetime.now(UTC),
            analyst_feedback_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        # For test_count_by_decision: review decision
        # NOT for test_find_by_criteria_prediction_class (would make it fail)
        Prediction(
            prediction_id=uuid4(),
            transaction_id=uuid4(),
            model_version="v1.1.0",
            fraud_probability=0.45,
            anomaly_score=0.40,
            risk_score=55,
            predicted_class="fraud",
            decision="review",
            confidence=0.60,
            explanation_data={},
            latency_ms=100,
            timestamp=datetime.now(UTC),
            analyst_feedback_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    ]

    created_predictions = []
    for pred in predictions:
        created = await repo.create(pred)
        created_predictions.append(created)

    await async_session.commit()

    return created_predictions


@pytest_asyncio.fixture
async def client(async_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    from src.infrastructure.database.connection import get_async_session
    from src.presentation.main import create_application

    # Override database session dependency
    async def override_get_session():
        yield async_session

    app = create_application()

    # Override the get_async_session dependency
    app.dependency_overrides[get_async_session] = override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession) -> User:
    """Create a test user for authentication tests."""
    from src.infrastructure.database.repositories.user_repository_impl import (
        UserRepositoryImpl,
    )

    repo = UserRepositoryImpl(async_session)

    user = User.create(email="auth_test@example.com", password="testpassword123", role="analyst")

    created_user = await repo.create(user)
    await async_session.commit()

    return created_user
