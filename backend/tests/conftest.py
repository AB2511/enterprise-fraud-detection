"""Test configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
from src.domain.entities.prediction import Prediction
from src.infrastructure.database.models import Base

# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture
async def async_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
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
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
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
