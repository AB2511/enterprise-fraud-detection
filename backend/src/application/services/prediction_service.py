"""Prediction Service - Manage prediction lifecycle (NO ML inference)."""

from datetime import datetime
from uuid import UUID

from src.application.interfaces.audit_repository import AuditRepository
from src.domain.entities.audit_log import AuditLog


class PredictionService:
    """Service for prediction lifecycle management.

    This service stores and manages prediction records WITHOUT performing
    any ML inference. It stores model outputs, explanations, and metadata.

    NOTE: This service does NOT call ML models. It only manages prediction data.
    """

    def __init__(
        self,
        audit_repository: AuditRepository,
    ) -> None:
        """Initialize prediction service.

        Args:
            audit_repository: Repository for audit logging
        """
        self._audit_repo = audit_repository
        # Note: Prediction repository would be added here when implementing persistence

    async def store_prediction(
        self,
        transaction_id: UUID,
        model_id: UUID,
        model_version: str,
        prediction_class: str,
        fraud_probability: float,
        confidence: float,
        explanation_data: dict | None = None,
        latency_ms: float | None = None,
        user_id: UUID | None = None,
    ) -> dict:
        """Store a prediction result (from external ML service).

        Args:
            transaction_id: Transaction UUID
            model_id: Model UUID that generated prediction
            model_version: Model version string
            prediction_class: Predicted class (fraud/legitimate)
            fraud_probability: Fraud probability (0.0-1.0)
            confidence: Confidence score (0.0-1.0)
            explanation_data: SHAP values or feature importance
            latency_ms: Inference latency in milliseconds
            user_id: User storing prediction

        Returns:
            Stored prediction data

        Note:
            This method does NOT perform inference. It stores results from
            an external ML service.
        """
        # Create prediction record
        prediction_data = {
            "transaction_id": str(transaction_id),
            "model_id": str(model_id),
            "model_version": model_version,
            "prediction_class": prediction_class,
            "fraud_probability": fraud_probability,
            "confidence": confidence,
            "explanation_data": explanation_data,
            "latency_ms": latency_ms,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Audit
        audit = AuditLog.for_creation(
            entity_type="prediction",
            entity_id=UUID(prediction_data["transaction_id"]),  # Placeholder
            user_id=user_id,
            username="ml_service",
            new_value=prediction_data,
        )
        await self._audit_repo.create(audit)

        return prediction_data

    async def update_prediction_status(
        self,
        prediction_id: UUID,
        new_status: str,
        user_id: UUID | None = None,
    ) -> dict:
        """Update prediction review status.

        Args:
            prediction_id: Prediction UUID
            new_status: New status (under_review, confirmed, rejected)
            user_id: User updating status

        Returns:
            Updated prediction data
        """
        # Store status update
        update_data = {
            "prediction_id": str(prediction_id),
            "status": new_status,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Audit
        audit = AuditLog.for_update(
            entity_type="prediction",
            entity_id=prediction_id,
            user_id=user_id,
            username="analyst",
            old_value={"status": "pending"},
            new_value={"status": new_status},
        )
        await self._audit_repo.create(audit)

        return update_data

    async def store_model_metadata(
        self,
        model_id: UUID,
        model_version: str,
        model_type: str,
        training_date: datetime,
        metrics: dict,
        user_id: UUID | None = None,
    ) -> dict:
        """Store model metadata (NOT training logic).

        Args:
            model_id: Model UUID
            model_version: Version string
            model_type: Type (xgboost, isolation_forest, etc.)
            training_date: When model was trained
            metrics: Performance metrics (accuracy, precision, recall, etc.)
            user_id: User storing metadata

        Returns:
            Stored model metadata

        Note:
            This does NOT train models. It stores metadata about pre-trained models.
        """
        model_data = {
            "model_id": str(model_id),
            "model_version": model_version,
            "model_type": model_type,
            "training_date": training_date.isoformat(),
            "metrics": metrics,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Audit
        audit = AuditLog.for_creation(
            entity_type="model",
            entity_id=model_id,
            user_id=user_id,
            username="ml_engineer",
            new_value=model_data,
        )
        await self._audit_repo.create(audit)

        return model_data

    async def store_explanation(
        self,
        prediction_id: UUID,
        explanation_type: str,
        explanation_data: dict,
        user_id: UUID | None = None,
    ) -> dict:
        """Store model explanation data (SHAP, LIME, etc.).

        Args:
            prediction_id: Prediction UUID
            explanation_type: Type (shap, lime, feature_importance)
            explanation_data: Explanation details
            user_id: User storing explanation

        Returns:
            Stored explanation

        Note:
            This stores pre-computed explanations. It does NOT compute SHAP values.
        """
        explanation = {
            "prediction_id": str(prediction_id),
            "explanation_type": explanation_type,
            "explanation_data": explanation_data,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Audit
        audit = AuditLog.for_creation(
            entity_type="explanation",
            entity_id=prediction_id,
            user_id=user_id,
            username="ml_service",
            new_value=explanation,
        )
        await self._audit_repo.create(audit)

        return explanation

    def validate_prediction_data(
        self,
        fraud_probability: float,
        confidence: float,
    ) -> dict:
        """Validate prediction data ranges.

        Args:
            fraud_probability: Fraud probability
            confidence: Confidence score

        Returns:
            Validation result
        """
        errors = []

        if not (0.0 <= fraud_probability <= 1.0):
            errors.append("Fraud probability must be between 0.0 and 1.0")

        if not (0.0 <= confidence <= 1.0):
            errors.append("Confidence must be between 0.0 and 1.0")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
