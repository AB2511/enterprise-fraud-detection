"""Prediction Service - prediction persistence and lifecycle workflows."""

from collections.abc import Mapping
from datetime import datetime
from typing import TypedDict
from uuid import UUID

from src.application.interfaces.audit_repository import AuditRepository
from src.application.interfaces.prediction_repository import PredictionRepository
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.prediction import Prediction


class ModelPerformanceStats(TypedDict):
    model_id: UUID
    model_version: str
    total_predictions: int
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1_score: float | None
    avg_latency_ms: float | None
    fraud_detection_rate: float | None
    false_positive_rate: float | None
    analysis_period_start: datetime
    analysis_period_end: datetime


class PredictionExplanation(TypedDict):
    feature_importance: dict[str, float]
    top_contributing_features: list[str]
    rule_explanations: list[str]
    confidence_intervals: dict[str, float] | None
    similar_cases: list[UUID] | None
    recommendation: str


class PredictionService:
    """Application service for persisted prediction aggregates."""

    def __init__(
        self, prediction_repository: PredictionRepository, audit_repository: AuditRepository
    ) -> None:
        self._prediction_repo = prediction_repository
        self._audit_repo = audit_repository

    async def create_prediction(
        self,
        *,
        transaction_id: UUID,
        model_id: UUID,
        model_version: str,
        prediction_class: str,
        fraud_probability: float,
        anomaly_score: float | None,
        risk_score: float | None,
        confidence: float | None,
        decision: str,
        latency_ms: float | None,
        explanation_data: Mapping[str, object] | None,
        user_id: UUID | None = None,
    ) -> Prediction:
        prediction = Prediction(
            transaction_id=transaction_id,
            model_id=model_id,
            model_version=model_version,
            predicted_class=prediction_class,
            fraud_probability=fraud_probability,
            anomaly_score=anomaly_score if anomaly_score is not None else 0.0,
            risk_score=int(risk_score) if risk_score is not None else 0,
            confidence=confidence if confidence is not None else 0.0,
            decision=decision,
            latency_ms=int(latency_ms) if latency_ms is not None else 0,
            explanation_data=dict(explanation_data) if explanation_data is not None else {},
        )
        created = await self._prediction_repo.create(prediction)
        await self._audit_repo.create(
            AuditLog.for_creation(
                entity_type="prediction",
                entity_id=created.prediction_id,
                user_id=user_id,
                username="system",
                new_value={"decision": created.decision, "risk_score": created.risk_score},
            )
        )
        return created

    async def update_prediction(
        self,
        prediction_id: UUID,
        updates: Mapping[str, object],
        user_id: UUID | None = None,
    ) -> Prediction:
        prediction = await self._require_prediction(prediction_id)
        old_decision = prediction.decision
        decision = updates.get("decision")
        if isinstance(decision, str):
            if decision == "approve":
                prediction.approve()
            elif decision == "review":
                prediction.review()
            elif decision == "decline":
                prediction.reject()
            else:
                raise ValueError(f"Unsupported prediction decision: {decision}")
        explanation_data = updates.get("explanation_data")
        if isinstance(explanation_data, Mapping):
            prediction.explanation_data = dict(explanation_data)
            prediction.updated_at = datetime.utcnow()
        updated = await self._prediction_repo.update(prediction)
        await self._audit_repo.create(
            AuditLog.for_update(
                entity_type="prediction",
                entity_id=prediction_id,
                user_id=user_id,
                username="system",
                old_value={"decision": old_decision},
                new_value={"decision": updated.decision},
            )
        )
        return updated

    async def get_prediction_by_id(self, prediction_id: UUID) -> Prediction:
        return await self._require_prediction(prediction_id)

    async def get_prediction_by_transaction_id(self, transaction_id: UUID) -> Prediction:
        prediction = await self._prediction_repo.get_by_transaction_id(transaction_id)
        if prediction is None:
            raise ValueError(f"Prediction for transaction {transaction_id} not found")
        return prediction

    async def search_predictions(
        self, criteria: Mapping[str, object], limit: int, offset: int
    ) -> tuple[list[Prediction], int]:
        model_version = criteria.get("model_version")
        decision = criteria.get("decision")
        if isinstance(model_version, str):
            predictions = await self._prediction_repo.list_by_model_version(
                model_version, limit, offset
            )
        elif isinstance(decision, str):
            predictions = await self._prediction_repo.list_by_decision(decision, limit, offset)
        else:
            predictions = await self._prediction_repo.list_by_date_range(
                self._as_datetime(criteria.get("start_date"), datetime.min),
                self._as_datetime(criteria.get("end_date"), datetime.max),
                limit,
                offset,
            )
        return predictions, len(predictions)

    async def get_high_risk_predictions(
        self, min_risk_score: int, limit: int, offset: int
    ) -> tuple[list[Prediction], int]:
        predictions = await self._prediction_repo.list_high_risk(min_risk_score, limit, offset)
        return predictions, len(predictions)

    async def get_predictions_needing_feedback(
        self, limit: int, offset: int
    ) -> tuple[list[Prediction], int]:
        predictions = await self._prediction_repo.find_predictions_needing_feedback(limit, offset)
        return predictions, len(predictions)

    async def provide_feedback(
        self,
        prediction_id: UUID,
        is_correct: bool,
        actual_outcome: str,
        feedback_notes: str | None,
        analyst_id: UUID | None,
    ) -> Prediction:
        prediction = await self._require_prediction(prediction_id)
        if analyst_id is not None:
            prediction.add_feedback(analyst_id)
        if actual_outcome == "fraud":
            prediction.reject()
        elif actual_outcome == "legitimate":
            prediction.approve()
        else:
            raise ValueError(f"Unsupported actual outcome: {actual_outcome}")
        updated = await self._prediction_repo.update(prediction)
        await self._audit_repo.create(
            AuditLog.for_update(
                entity_type="prediction",
                entity_id=prediction_id,
                user_id=analyst_id,
                username="analyst",
                old_value={"is_correct": is_correct},
                new_value={"actual_outcome": actual_outcome, "notes": feedback_notes},
            )
        )
        return updated

    async def get_prediction_explanation(self, prediction_id: UUID) -> PredictionExplanation:
        data = (await self._require_prediction(prediction_id)).explanation_data
        importance_value = data.get("feature_importance", {})
        importance = (
            {
                key: value
                for key, value in importance_value.items()
                if isinstance(key, str) and isinstance(value, float)
            }
            if isinstance(importance_value, Mapping)
            else {}
        )
        feature_names = [name for name in importance if name]
        return {
            "feature_importance": importance,
            "top_contributing_features": feature_names,
            "rule_explanations": [],
            "confidence_intervals": None,
            "similar_cases": None,
            "recommendation": "Review prediction details",
        }

    async def get_model_performance_stats(
        self,
        model_id: UUID,
        model_version: str | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> ModelPerformanceStats:
        if model_version is None:
            raise ValueError("A model version is required")
        return await self._performance(model_id, model_version, start_date, end_date)

    async def get_model_performance_by_version(
        self, model_version: str, start_date: datetime | None, end_date: datetime | None
    ) -> ModelPerformanceStats:
        raw = await self._prediction_repo.get_model_performance_stats(
            model_version, start_date, end_date
        )
        return self._stats(UUID(int=0), model_version, raw, start_date, end_date)

    async def _performance(
        self,
        model_id: UUID,
        model_version: str,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> ModelPerformanceStats:
        raw = await self._prediction_repo.get_model_performance_stats(
            model_version, start_date, end_date
        )
        return self._stats(model_id, model_version, raw, start_date, end_date)

    @staticmethod
    def _stats(
        model_id: UUID,
        model_version: str,
        raw: Mapping[str, object],
        start: datetime | None,
        end: datetime | None,
    ) -> ModelPerformanceStats:
        def number(key: str) -> float | None:
            value = raw.get(key)
            return float(value) if isinstance(value, int | float) else None

        total = raw.get("total_predictions")
        return {
            "model_id": model_id,
            "model_version": model_version,
            "total_predictions": total if isinstance(total, int) else 0,
            "accuracy": number("accuracy"),
            "precision": number("precision"),
            "recall": number("recall"),
            "f1_score": number("f1_score"),
            "avg_latency_ms": number("avg_latency_ms"),
            "fraud_detection_rate": number("fraud_rate"),
            "false_positive_rate": number("false_positive_rate"),
            "analysis_period_start": start if start is not None else datetime.min,
            "analysis_period_end": end if end is not None else datetime.max,
        }

    async def _require_prediction(self, prediction_id: UUID) -> Prediction:
        prediction = await self._prediction_repo.get_by_id(prediction_id)
        if prediction is None:
            raise ValueError(f"Prediction {prediction_id} not found")
        return prediction

    @staticmethod
    def _as_datetime(value: object, default: datetime) -> datetime:
        return value if isinstance(value, datetime) else default
