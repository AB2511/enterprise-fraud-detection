"""Prediction Use Cases (CQRS Pattern)."""

from datetime import datetime
from uuid import UUID

from src.application.dtos.common import PageRequest, PageResponse
from src.application.dtos.prediction_dtos import (
    CreatePredictionRequest,
    ModelPerformanceResponse,
    PredictionExplanationResponse,
    PredictionListRequest,
    PredictionResponse,
    UpdatePredictionRequest,
)
from src.application.services.prediction_service import PredictionService
from src.domain.entities.prediction import Prediction


class CreatePredictionUseCase:
    """Use case for creating a new prediction."""

    def __init__(self, prediction_service: PredictionService) -> None:
        """Initialize use case.

        Args:
            prediction_service: Prediction service instance
        """
        self._service = prediction_service

    async def execute(
        self,
        request: CreatePredictionRequest,
        user_id: UUID | None = None,
    ) -> PredictionResponse:
        """Execute create prediction use case.

        Args:
            request: Create prediction request DTO
            user_id: User performing the action

        Returns:
            Prediction response DTO

        Raises:
            ValidationException: If validation fails
            EntityNotFoundException: If transaction or model not found
        """
        prediction = await self._service.create_prediction(
            transaction_id=request.transaction_id,
            model_id=request.model_id,
            model_version=request.model_version,
            prediction_class=request.prediction_class,
            fraud_probability=request.fraud_probability,
            anomaly_score=request.anomaly_score,
            risk_score=request.risk_score,
            confidence=request.confidence,
            decision=request.decision,
            latency_ms=request.latency_ms,
            explanation_data=request.explanation_data,
            user_id=user_id,
        )

        return self._to_response(prediction)

    @staticmethod
    def _to_response(prediction: Prediction) -> PredictionResponse:
        """Convert domain entity to response DTO."""
        return PredictionResponse(
            prediction_id=prediction.prediction_id,
            transaction_id=prediction.transaction_id,
            model_id=prediction.model_id,
            model_version=prediction.model_version,
            prediction_class=prediction.prediction_class,
            fraud_probability=prediction.fraud_probability,
            anomaly_score=prediction.anomaly_score,
            risk_score=prediction.risk_score,
            confidence=prediction.confidence,
            decision=prediction.decision,
            latency_ms=prediction.latency_ms,
            explanation_data=prediction.explanation_data,
            created_at=prediction.created_at,
            updated_at=prediction.updated_at,
        )


class UpdatePredictionUseCase:
    """Use case for updating a prediction."""

    def __init__(self, prediction_service: PredictionService) -> None:
        """Initialize use case.

        Args:
            prediction_service: Prediction service instance
        """
        self._service = prediction_service

    async def execute(
        self,
        prediction_id: UUID,
        request: UpdatePredictionRequest,
        user_id: UUID | None = None,
    ) -> PredictionResponse:
        """Execute update prediction use case.

        Args:
            prediction_id: Prediction UUID
            request: Update prediction request DTO
            user_id: User performing the action

        Returns:
            Prediction response DTO

        Raises:
            EntityNotFoundException: If prediction not found
            ValidationException: If validation fails
        """
        # Build updates dictionary
        updates = {}
        if request.decision is not None:
            updates["decision"] = request.decision
        if request.explanation_data is not None:
            updates["explanation_data"] = request.explanation_data

        prediction = await self._service.update_prediction(
            prediction_id=prediction_id,
            updates=updates,
            user_id=user_id,
        )

        return CreatePredictionUseCase._to_response(prediction)


class GetPredictionUseCase:
    """Use case for retrieving a prediction."""

    def __init__(self, prediction_service: PredictionService) -> None:
        """Initialize use case.

        Args:
            prediction_service: Prediction service instance
        """
        self._service = prediction_service

    async def execute(self, prediction_id: UUID) -> PredictionResponse:
        """Execute get prediction use case.

        Args:
            prediction_id: Prediction UUID

        Returns:
            Prediction response DTO

        Raises:
            EntityNotFoundException: If prediction not found
        """
        prediction = await self._service.get_prediction_by_id(prediction_id)
        return CreatePredictionUseCase._to_response(prediction)


class GetPredictionByTransactionUseCase:
    """Use case for retrieving prediction by transaction."""

    def __init__(self, prediction_service: PredictionService) -> None:
        """Initialize use case.

        Args:
            prediction_service: Prediction service instance
        """
        self._service = prediction_service

    async def execute(self, transaction_id: UUID) -> PredictionResponse:
        """Execute get prediction by transaction use case.

        Args:
            transaction_id: Transaction UUID

        Returns:
            Prediction response DTO

        Raises:
            EntityNotFoundException: If prediction not found
        """
        prediction = await self._service.get_prediction_by_transaction_id(transaction_id)
        return CreatePredictionUseCase._to_response(prediction)


class ListPredictionsUseCase:
    """Use case for listing predictions."""

    def __init__(self, prediction_service: PredictionService) -> None:
        """Initialize use case.

        Args:
            prediction_service: Prediction service instance
        """
        self._service = prediction_service

    async def execute(
        self,
        request: PredictionListRequest,
        page_request: PageRequest,
    ) -> PageResponse[PredictionResponse]:
        """Execute list predictions use case.

        Args:
            request: Prediction list request with filters
            page_request: Pagination parameters

        Returns:
            Paginated prediction responses
        """
        # Build search criteria
        criteria = {}
        if request.transaction_id:
            criteria["transaction_id"] = request.transaction_id
        if request.model_id:
            criteria["model_id"] = request.model_id
        if request.prediction_class:
            criteria["prediction_class"] = request.prediction_class
        if request.decision:
            criteria["decision"] = request.decision
        if request.min_fraud_probability is not None:
            criteria["min_fraud_probability"] = request.min_fraud_probability
        if request.max_fraud_probability is not None:
            criteria["max_fraud_probability"] = request.max_fraud_probability
        if request.start_date:
            criteria["start_date"] = request.start_date
        if request.end_date:
            criteria["end_date"] = request.end_date

        predictions, total = await self._service.search_predictions(
            criteria=criteria,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        prediction_responses = [CreatePredictionUseCase._to_response(p) for p in predictions]

        return PageResponse.create(
            items=prediction_responses,
            total=total,
            page_request=page_request,
        )


class GetHighRiskPredictionsUseCase:
    """Use case for getting high-risk predictions."""

    def __init__(self, prediction_service: PredictionService) -> None:
        """Initialize use case.

        Args:
            prediction_service: Prediction service instance
        """
        self._service = prediction_service

    async def execute(
        self,
        min_risk_score: int = 80,
        page_request: PageRequest | None = None,
    ) -> PageResponse[PredictionResponse]:
        """Execute get high-risk predictions use case.

        Args:
            min_risk_score: Minimum risk score threshold
            page_request: Pagination parameters

        Returns:
            Paginated high-risk prediction responses
        """
        if page_request is None:
            page_request = PageRequest(page=1, page_size=100)

        predictions, total = await self._service.get_high_risk_predictions(
            min_risk_score=min_risk_score,
            limit=page_request.limit,
            offset=page_request.offset,
        )

        prediction_responses = [CreatePredictionUseCase._to_response(p) for p in predictions]

        return PageResponse.create(
            items=prediction_responses,
            total=total,
            page_request=page_request,
        )


class GetModelPerformanceUseCase:
    """Use case for getting model performance statistics."""

    def __init__(self, prediction_service: PredictionService) -> None:
        """Initialize use case.

        Args:
            prediction_service: Prediction service instance
        """
        self._service = prediction_service

    async def execute(
        self,
        model_id: UUID,
        model_version: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ModelPerformanceResponse:
        """Execute get model performance use case.

        Args:
            model_id: Model UUID
            model_version: Optional specific model version
            start_date: Optional analysis start date
            end_date: Optional analysis end date

        Returns:
            Model performance response DTO
        """
        performance = await self._service.get_model_performance_stats(
            model_id=model_id,
            model_version=model_version,
            start_date=start_date,
            end_date=end_date,
        )

        return ModelPerformanceResponse(
            model_id=model_id,
            model_version=performance["model_version"],
            total_predictions=performance["total_predictions"],
            accuracy=performance.get("accuracy"),
            precision=performance.get("precision"),
            recall=performance.get("recall"),
            f1_score=performance.get("f1_score"),
            avg_latency_ms=performance.get("avg_latency_ms"),
            fraud_detection_rate=performance.get("fraud_detection_rate"),
            false_positive_rate=performance.get("false_positive_rate"),
            analysis_period_start=performance["analysis_period_start"],
            analysis_period_end=performance["analysis_period_end"],
        )


class GetPredictionExplanationUseCase:
    """Use case for getting detailed prediction explanation."""

    def __init__(self, prediction_service: PredictionService) -> None:
        """Initialize use case.

        Args:
            prediction_service: Prediction service instance
        """
        self._service = prediction_service

    async def execute(
        self,
        prediction_id: UUID,
    ) -> PredictionExplanationResponse:
        """Execute get prediction explanation use case.

        Args:
            prediction_id: Prediction UUID

        Returns:
            Prediction explanation response DTO

        Raises:
            EntityNotFoundException: If prediction not found
        """
        explanation = await self._service.get_prediction_explanation(prediction_id)

        return PredictionExplanationResponse(
            prediction_id=prediction_id,
            feature_importance=explanation["feature_importance"],
            top_contributing_features=explanation["top_contributing_features"],
            rule_explanations=explanation["rule_explanations"],
            confidence_intervals=explanation.get("confidence_intervals"),
            similar_cases=explanation.get("similar_cases"),
            recommendation=explanation["recommendation"],
        )


class GetPredictionsNeedingFeedbackUseCase:
    """Use case for getting predictions that need analyst feedback."""

    def __init__(self, prediction_service: PredictionService) -> None:
        """Initialize use case.

        Args:
            prediction_service: Prediction service instance
        """
        self._service = prediction_service

    async def execute(
        self,
        page_request: PageRequest | None = None,
    ) -> PageResponse[PredictionResponse]:
        """Execute get predictions needing feedback use case.

        Args:
            page_request: Pagination parameters

        Returns:
            Paginated prediction responses needing feedback
        """
        if page_request is None:
            page_request = PageRequest(page=1, page_size=50)

        predictions, total = await self._service.get_predictions_needing_feedback(
            limit=page_request.limit,
            offset=page_request.offset,
        )

        prediction_responses = [CreatePredictionUseCase._to_response(p) for p in predictions]

        return PageResponse.create(
            items=prediction_responses,
            total=total,
            page_request=page_request,
        )


class ProvidePredictionFeedbackUseCase:
    """Use case for providing feedback on a prediction."""

    def __init__(self, prediction_service: PredictionService) -> None:
        """Initialize use case.

        Args:
            prediction_service: Prediction service instance
        """
        self._service = prediction_service

    async def execute(
        self,
        prediction_id: UUID,
        is_correct: bool,
        actual_outcome: str,
        feedback_notes: str | None = None,
        analyst_id: UUID | None = None,
    ) -> PredictionResponse:
        """Execute provide prediction feedback use case.

        Args:
            prediction_id: Prediction UUID
            is_correct: Whether the prediction was correct
            actual_outcome: Actual transaction outcome (fraud/legitimate)
            feedback_notes: Optional analyst notes
            analyst_id: UUID of analyst providing feedback

        Returns:
            Updated prediction response DTO

        Raises:
            EntityNotFoundException: If prediction not found
        """
        prediction = await self._service.provide_feedback(
            prediction_id=prediction_id,
            is_correct=is_correct,
            actual_outcome=actual_outcome,
            feedback_notes=feedback_notes,
            analyst_id=analyst_id,
        )

        return CreatePredictionUseCase._to_response(prediction)


class GetModelComparisonUseCase:
    """Use case for comparing model performance."""

    def __init__(self, prediction_service: PredictionService) -> None:
        """Initialize use case.

        Args:
            prediction_service: Prediction service instance
        """
        self._service = prediction_service

    async def execute(
        self,
        model_versions: list[str],
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[ModelPerformanceResponse]:
        """Execute get model comparison use case.

        Args:
            model_versions: List of model versions to compare
            start_date: Optional analysis start date
            end_date: Optional analysis end date

        Returns:
            List of model performance responses for comparison
        """
        comparison_results = []

        for version in model_versions:
            performance = await self._service.get_model_performance_by_version(
                model_version=version,
                start_date=start_date,
                end_date=end_date,
            )

            comparison_results.append(
                ModelPerformanceResponse(
                    model_id=performance["model_id"],
                    model_version=version,
                    total_predictions=performance["total_predictions"],
                    accuracy=performance.get("accuracy"),
                    precision=performance.get("precision"),
                    recall=performance.get("recall"),
                    f1_score=performance.get("f1_score"),
                    avg_latency_ms=performance.get("avg_latency_ms"),
                    fraud_detection_rate=performance.get("fraud_detection_rate"),
                    false_positive_rate=performance.get("false_positive_rate"),
                    analysis_period_start=performance["analysis_period_start"],
                    analysis_period_end=performance["analysis_period_end"],
                )
            )

        return comparison_results
