"""Integration tests for PredictionRepositoryImpl."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.repositories.prediction_repository_impl import (
    PredictionRepositoryImpl,
    PredictionNotFoundError,
)
from src.domain.entities.prediction import Prediction


@pytest.fixture
def prediction_repository(async_session: AsyncSession) -> PredictionRepositoryImpl:
    """Create prediction repository instance."""
    return PredictionRepositoryImpl(async_session)


@pytest.fixture
def sample_prediction() -> Prediction:
    """Create sample prediction for testing."""
    return Prediction(
        prediction_id=uuid4(),
        transaction_id=uuid4(),
        model_version="v1.2.0",
        fraud_probability=0.75,
        anomaly_score=0.65,
        risk_score=85,
        predicted_class="fraud",
        decision="decline",
        confidence=0.92,
        explanation_data={
            "top_features": ["amount", "velocity_1h", "merchant_risk"],
            "feature_scores": {"amount": 0.3, "velocity_1h": 0.25, "merchant_risk": 0.2}
        },
        latency_ms=150,
        timestamp=datetime.utcnow(),
        analyst_feedback_id=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestPredictionRepositoryCreate:
    """Test prediction creation operations."""

    async def test_create_prediction_success(
        self,
        prediction_repository: PredictionRepositoryImpl,
        sample_prediction: Prediction,
        async_session: AsyncSession,
    ):
        """Test successful prediction creation."""
        result = await prediction_repository.create(sample_prediction)
        await async_session.commit()

        assert result.prediction_id == sample_prediction.prediction_id
        assert result.transaction_id == sample_prediction.transaction_id
        assert result.model_version == sample_prediction.model_version
        assert result.fraud_probability == sample_prediction.fraud_probability
        assert result.predicted_class == sample_prediction.predicted_class

    async def test_create_prediction_with_explanation(
        self,
        prediction_repository: PredictionRepositoryImpl,
        sample_prediction: Prediction,
        async_session: AsyncSession,
    ):
        """Test prediction creation with explanation data."""
        result = await prediction_repository.create(sample_prediction)
        await async_session.commit()

        assert result.explanation_data is not None
        assert "top_features" in result.explanation_data
        assert "feature_scores" in result.explanation_data

    async def test_create_prediction_minimal_data(
        self,
        prediction_repository: PredictionRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test prediction creation with minimal required data."""
        prediction = Prediction(
            prediction_id=uuid4(),
            transaction_id=uuid4(),
            model_version="v1.0.0",
            fraud_probability=0.25,
            anomaly_score=0.15,
            risk_score=30,
            predicted_class="legitimate",
            decision="approve",
            confidence=0.85,
            explanation_data={},
            latency_ms=75,
            timestamp=datetime.utcnow(),
            analyst_feedback_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        result = await prediction_repository.create(prediction)
        await async_session.commit()

        assert result.predicted_class == "legitimate"
        assert result.decision == "approve"


class TestPredictionRepositoryRead:
    """Test prediction retrieval operations."""

    async def test_get_by_id_success(
        self,
        prediction_repository: PredictionRepositoryImpl,
        sample_prediction: Prediction,
        async_session: AsyncSession,
    ):
        """Test successful prediction retrieval by ID."""
        created = await prediction_repository.create(sample_prediction)
        await async_session.commit()

        result = await prediction_repository.get_by_id(created.prediction_id)

        assert result is not None
        assert result.prediction_id == sample_prediction.prediction_id
        assert result.fraud_probability == sample_prediction.fraud_probability

    async def test_get_by_id_not_found(self, prediction_repository: PredictionRepositoryImpl):
        """Test prediction retrieval with non-existent ID."""
        result = await prediction_repository.get_by_id(uuid4())
        assert result is None

    async def test_get_by_transaction_id_success(
        self,
        prediction_repository: PredictionRepositoryImpl,
        sample_prediction: Prediction,
        async_session: AsyncSession,
    ):
        """Test successful prediction retrieval by transaction ID."""
        await prediction_repository.create(sample_prediction)
        await async_session.commit()

        result = await prediction_repository.get_by_transaction_id(
            sample_prediction.transaction_id
        )

        assert result is not None
        assert result.transaction_id == sample_prediction.transaction_id

    async def test_get_by_transaction_id_not_found(
        self, prediction_repository: PredictionRepositoryImpl
    ):
        """Test prediction retrieval with non-existent transaction ID."""
        result = await prediction_repository.get_by_transaction_id(uuid4())
        assert result is None


class TestPredictionRepositoryUpdate:
    """Test prediction update operations."""

    async def test_update_prediction_success(
        self,
        prediction_repository: PredictionRepositoryImpl,
        sample_prediction: Prediction,
        async_session: AsyncSession,
    ):
        """Test successful prediction update."""
        created = await prediction_repository.create(sample_prediction)
        await async_session.commit()

        # Update prediction data
        created.decision = "review"
        created.explanation_data = {"updated": True, "reason": "analyst review"}

        result = await prediction_repository.update(created)
        await async_session.commit()

        assert result.decision == "review"
        assert result.explanation_data["updated"] is True

    async def test_update_prediction_not_found(
        self,
        prediction_repository: PredictionRepositoryImpl,
        sample_prediction: Prediction,
    ):
        """Test update of non-existent prediction."""
        sample_prediction.prediction_id = uuid4()  # Non-existent ID

        with pytest.raises(PredictionNotFoundError):
            await prediction_repository.update(sample_prediction)


class TestPredictionRepositoryDelete:
    """Test prediction deletion operations."""

    async def test_delete_prediction_success(
        self,
        prediction_repository: PredictionRepositoryImpl,
        sample_prediction: Prediction,
        async_session: AsyncSession,
    ):
        """Test successful prediction deletion."""
        created = await prediction_repository.create(sample_prediction)
        await async_session.commit()

        result = await prediction_repository.delete(created.prediction_id)
        await async_session.commit()

        assert result is True

        # Verify prediction is deleted
        retrieved = await prediction_repository.get_by_id(created.prediction_id)
        assert retrieved is None

    async def test_delete_prediction_not_found(
        self, prediction_repository: PredictionRepositoryImpl
    ):
        """Test deletion of non-existent prediction."""
        result = await prediction_repository.delete(uuid4())
        assert result is False


class TestPredictionRepositoryListing:
    """Test prediction listing operations."""

    @pytest.fixture
    async def multiple_predictions(
        self,
        prediction_repository: PredictionRepositoryImpl,
        async_session: AsyncSession,
    ) -> list[Prediction]:
        """Create multiple predictions for listing tests."""
        predictions = [
            # High-risk fraud prediction
            Prediction(
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                model_version="v1.2.0",
                fraud_probability=0.95,
                anomaly_score=0.85,
                risk_score=95,
                predicted_class="fraud",
                decision="decline",
                confidence=0.97,
                explanation_data={"high_risk": True},
                latency_ms=120,
                timestamp=datetime.utcnow(),
                analyst_feedback_id=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            # Low-risk legitimate prediction
            Prediction(
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                model_version="v1.2.0",
                fraud_probability=0.15,
                anomaly_score=0.25,
                risk_score=20,
                predicted_class="legitimate",
                decision="approve",
                confidence=0.88,
                explanation_data={"low_risk": True},
                latency_ms=95,
                timestamp=datetime.utcnow(),
                analyst_feedback_id=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            # Medium-risk review prediction
            Prediction(
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                model_version="v1.1.5",
                fraud_probability=0.55,
                anomaly_score=0.45,
                risk_score=60,
                predicted_class="suspicious",
                decision="review",
                confidence=0.72,
                explanation_data={"needs_review": True},
                latency_ms=180,
                timestamp=datetime.utcnow(),
                analyst_feedback_id=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
        ]

        created_predictions = []
        for prediction in predictions:
            created = await prediction_repository.create(prediction)
            created_predictions.append(created)
        
        await async_session.commit()
        return created_predictions

    async def test_list_by_model_version(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test listing predictions by model version."""
        result = await prediction_repository.list_by_model_version("v1.2.0")

        assert len(result) == 2
        for prediction in result:
            assert prediction.model_version == "v1.2.0"

    async def test_list_by_decision(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test listing predictions by decision."""
        decline_result = await prediction_repository.list_by_decision("decline")
        approve_result = await prediction_repository.list_by_decision("approve")
        review_result = await prediction_repository.list_by_decision("review")

        assert len(decline_result) == 1
        assert len(approve_result) == 1
        assert len(review_result) == 1

        assert decline_result[0].decision == "decline"
        assert approve_result[0].decision == "approve"
        assert review_result[0].decision == "review"

    async def test_list_high_risk(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test listing high-risk predictions."""
        result = await prediction_repository.list_high_risk(min_risk_score=80)

        assert len(result) == 1
        assert result[0].risk_score >= 80

    async def test_list_by_date_range(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test listing predictions by date range."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        tomorrow = datetime.utcnow() + timedelta(days=1)

        result = await prediction_repository.list_by_date_range(
            yesterday, tomorrow
        )

        assert len(result) == 3  # All predictions should be in range


class TestPredictionRepositoryAnalytics:
    """Test prediction analytics and statistics operations."""

    async def test_count_by_decision(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test counting predictions by decision."""
        decline_count = await prediction_repository.count_by_decision("decline")
        approve_count = await prediction_repository.count_by_decision("approve")
        review_count = await prediction_repository.count_by_decision("review")

        assert decline_count == 1
        assert approve_count == 1
        assert review_count == 1

    async def test_get_model_performance_stats(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test getting model performance statistics."""
        stats = await prediction_repository.get_model_performance_stats("v1.2.0")

        assert stats["total_predictions"] == 2
        assert stats["fraud_rate"] > 0
        assert stats["approval_rate"] > 0
        assert stats["avg_confidence"] > 0

    async def test_get_model_performance_stats_with_date_range(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test model performance stats with date filtering."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        tomorrow = datetime.utcnow() + timedelta(days=1)

        stats = await prediction_repository.get_model_performance_stats(
            "v1.2.0", start_date=yesterday, end_date=tomorrow
        )

        assert stats["total_predictions"] == 2

    async def test_get_model_performance_stats_no_data(
        self,
        prediction_repository: PredictionRepositoryImpl,
    ):
        """Test model performance stats with no data."""
        stats = await prediction_repository.get_model_performance_stats("v9.9.9")

        assert stats["total_predictions"] == 0
        assert stats["avg_fraud_probability"] == 0.0

    async def test_find_predictions_needing_feedback(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test finding predictions that need analyst feedback."""
        result = await prediction_repository.find_predictions_needing_feedback()

        # Should find predictions with "review" decision and risk_score >= 70
        # From our test data, none meet both criteria, so should be empty
        assert len(result) == 0


class TestPredictionRepositoryComplexQueries:
    """Test complex prediction query operations."""

    async def test_find_by_criteria_comprehensive(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test comprehensive criteria-based search."""
        result = await prediction_repository.find_by_criteria(
            model_version="v1.2.0",
            min_fraud_probability=0.8,
            max_fraud_probability=1.0,
            decision="decline"
        )

        assert len(result) == 1
        prediction = result[0]
        assert prediction.model_version == "v1.2.0"
        assert prediction.fraud_probability >= 0.8
        assert prediction.decision == "decline"

    async def test_find_by_criteria_risk_score_range(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test finding predictions by risk score range."""
        result = await prediction_repository.find_by_criteria(
            min_risk_score=50,
            max_risk_score=100
        )

        assert len(result) == 2  # High and medium risk predictions
        for prediction in result:
            assert 50 <= prediction.risk_score <= 100

    async def test_find_by_criteria_confidence_threshold(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test finding predictions by confidence threshold."""
        result = await prediction_repository.find_by_criteria(
            min_confidence=0.9
        )

        assert len(result) == 1  # Only high-confidence prediction
        assert result[0].confidence >= 0.9

    async def test_find_by_criteria_prediction_class(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test finding predictions by prediction class."""
        fraud_result = await prediction_repository.find_by_criteria(
            prediction_class="fraud"
        )
        
        legitimate_result = await prediction_repository.find_by_criteria(
            prediction_class="legitimate"
        )

        assert len(fraud_result) == 1
        assert len(legitimate_result) == 1

    async def test_find_by_criteria_sorting(
        self,
        prediction_repository: PredictionRepositoryImpl,
        multiple_predictions: list[Prediction],
    ):
        """Test finding predictions with custom sorting."""
        # Sort by risk score descending
        result_desc = await prediction_repository.find_by_criteria(
            sort_by="risk_score",
            sort_desc=True
        )

        # Sort by risk score ascending
        result_asc = await prediction_repository.find_by_criteria(
            sort_by="risk_score",
            sort_desc=False
        )

        assert len(result_desc) == 3
        assert len(result_asc) == 3

        # Verify sorting
        assert result_desc[0].risk_score >= result_desc[1].risk_score
        assert result_asc[0].risk_score <= result_asc[1].risk_score


class TestPredictionRepositoryPagination:
    """Test prediction pagination operations."""

    async def test_pagination_offset_limit(
        self,
        prediction_repository: PredictionRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test pagination with offset and limit."""
        # Create multiple predictions
        for i in range(5):
            prediction = Prediction(
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                model_version="v1.0.0",
                fraud_probability=0.1 + (i * 0.1),
                anomaly_score=0.1 + (i * 0.1),
                risk_score=10 + (i * 10),
                predicted_class="legitimate" if i < 3 else "fraud",
                decision="approve" if i < 3 else "decline",
                confidence=0.7 + (i * 0.05),
                explanation_data={"sequence": i},
                latency_ms=100 + i,
                timestamp=datetime.utcnow(),
                analyst_feedback_id=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await prediction_repository.create(prediction)

        await async_session.commit()

        # Test pagination
        page1 = await prediction_repository.find_by_criteria(
            limit=2, offset=0
        )
        page2 = await prediction_repository.find_by_criteria(
            limit=2, offset=2
        )

        assert len(page1) == 2
        assert len(page2) == 2
        
        # Verify no overlap
        page1_ids = {p.prediction_id for p in page1}
        page2_ids = {p.prediction_id for p in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestPredictionRepositoryEdgeCases:
    """Test prediction repository edge cases."""

    async def test_prediction_with_extreme_values(
        self,
        prediction_repository: PredictionRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test prediction creation with extreme values."""
        prediction = Prediction(
            prediction_id=uuid4(),
            transaction_id=uuid4(),
            model_version="v0.0.1",
            fraud_probability=1.0,  # Maximum probability
            anomaly_score=0.0,     # Minimum score
            risk_score=100,        # Maximum risk
            predicted_class="fraud",
            decision="decline",
            confidence=1.0,        # Maximum confidence
            explanation_data={
                "extreme_case": True,
                "confidence_factors": []
            },
            latency_ms=5000,       # High latency
            timestamp=datetime.utcnow(),
            analyst_feedback_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        result = await prediction_repository.create(prediction)
        await async_session.commit()

        assert result.fraud_probability == 1.0
        assert result.anomaly_score == 0.0
        assert result.risk_score == 100
        assert result.confidence == 1.0

    async def test_prediction_with_empty_explanation(
        self,
        prediction_repository: PredictionRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test prediction creation with empty explanation data."""
        prediction = Prediction(
            prediction_id=uuid4(),
            transaction_id=uuid4(),
            model_version="v1.0.0",
            fraud_probability=0.5,
            anomaly_score=0.3,
            risk_score=50,
            predicted_class="suspicious",
            decision="review",
            confidence=0.6,
            explanation_data={},  # Empty explanation
            latency_ms=100,
            timestamp=datetime.utcnow(),
            analyst_feedback_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        result = await prediction_repository.create(prediction)
        await async_session.commit()

        assert result.explanation_data == {}

    async def test_prediction_model_version_edge_cases(
        self,
        prediction_repository: PredictionRepositoryImpl,
        async_session: AsyncSession,
    ):
        """Test predictions with various model version formats."""
        versions = ["v1.0", "v2.10.15", "beta-0.1", "experimental"]
        
        predictions = []
        for version in versions:
            prediction = Prediction(
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                model_version=version,
                fraud_probability=0.4,
                anomaly_score=0.2,
                risk_score=40,
                predicted_class="legitimate",
                decision="approve",
                confidence=0.8,
                explanation_data={"version": version},
                latency_ms=100,
                timestamp=datetime.utcnow(),
                analyst_feedback_id=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            created = await prediction_repository.create(prediction)
            predictions.append(created)

        await async_session.commit()

        # Verify all versions were stored correctly
        for i, version in enumerate(versions):
            assert predictions[i].model_version == version

    async def test_repository_error_handling(
        self,
        prediction_repository: PredictionRepositoryImpl,
    ):
        """Test repository error handling."""
        with pytest.raises(PredictionNotFoundError):
            invalid_prediction = Prediction(
                prediction_id=uuid4(),
                transaction_id=uuid4(),
                model_version="v1.0.0",
                fraud_probability=0.5,
                anomaly_score=0.3,
                risk_score=50,
                predicted_class="suspicious",
                decision="review",
                confidence=0.6,
                explanation_data={},
                latency_ms=100,
                timestamp=datetime.utcnow(),
                analyst_feedback_id=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await prediction_repository.update(invalid_prediction)