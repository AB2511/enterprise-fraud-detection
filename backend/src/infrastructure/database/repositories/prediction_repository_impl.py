"""Prediction Repository Implementation using SQLAlchemy Async."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Integer, and_, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.prediction_repository import PredictionRepository
from src.domain.entities.prediction import Prediction
from src.domain.exceptions.base import DomainException
from src.infrastructure.database.models import PredictionModel


class PredictionNotFoundError(DomainException):
    """Raised when prediction is not found."""

    def __init__(self, prediction_id: UUID) -> None:
        super().__init__(f"Prediction with ID {prediction_id} not found", "PREDICTION_NOT_FOUND")


class PredictionRepositoryImpl(PredictionRepository):
    """SQLAlchemy implementation of PredictionRepository.

    Provides async database operations for Prediction entities with
    comprehensive analytics and performance tracking capabilities.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, prediction: Prediction) -> Prediction:
        """Create a new prediction.

        Args:
            prediction: Prediction entity to create

        Returns:
            Created prediction with generated ID

        Raises:
            RepositoryError: If creation fails
        """
        try:
            # Convert domain entity to database model
            prediction_model = PredictionModel(
                id=prediction.prediction_id,
                transaction_id=prediction.transaction_id,
                model_id=None,
                model_version=prediction.model_version,
                prediction_class=prediction.predicted_class,
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

            self._session.add(prediction_model)
            await self._session.flush()
            await self._session.refresh(prediction_model)

            return self._model_to_entity(prediction_model)

        except IntegrityError as e:
            await self._session.rollback()
            raise DomainException(
                f"Database constraint violation: {e}", "DB_CONSTRAINT_ERROR"
            ) from e

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to create prediction: {e}", "REPOSITORY_ERROR") from e

    async def get_by_id(self, prediction_id: UUID) -> Prediction | None:
        """Retrieve prediction by ID.

        Args:
            prediction_id: Prediction UUID

        Returns:
            Prediction if found, None otherwise
        """
        try:
            result = await self._session.execute(
                select(PredictionModel).where(PredictionModel.id == prediction_id)
            )
            prediction_model = result.scalar_one_or_none()

            if prediction_model:
                return self._model_to_entity(prediction_model)
            return None

        except Exception as e:
            raise DomainException(f"Failed to get prediction by ID: {e}", "REPOSITORY_ERROR") from e

    async def get_by_transaction_id(self, transaction_id: UUID) -> Prediction | None:
        """Retrieve prediction by transaction ID.

        Args:
            transaction_id: Transaction UUID

        Returns:
            Prediction if found, None otherwise
        """
        try:
            result = await self._session.execute(
                select(PredictionModel)
                .where(PredictionModel.transaction_id == transaction_id)
                .order_by(desc(PredictionModel.created_at))
            )
            prediction_model = result.scalar_one_or_none()

            if prediction_model:
                return self._model_to_entity(prediction_model)
            return None

        except Exception as e:
            raise DomainException(
                f"Failed to get prediction by transaction ID: {e}", "REPOSITORY_ERROR"
            ) from e

    async def update(self, prediction: Prediction) -> Prediction:
        """Update existing prediction.

        Args:
            prediction: Prediction entity with updated data

        Returns:
            Updated prediction

        Raises:
            PredictionNotFoundError: If prediction doesn't exist
            RepositoryError: If update fails
        """
        try:
            # Check if prediction exists
            existing = await self._session.execute(
                select(PredictionModel).where(PredictionModel.id == prediction.prediction_id)
            )
            if not existing.scalar_one_or_none():
                raise PredictionNotFoundError(prediction.prediction_id)

            # Update fields
            await self._session.execute(
                update(PredictionModel)
                .where(PredictionModel.id == prediction.prediction_id)
                .values(
                    decision=prediction.decision,
                    explanation_data=prediction.explanation_data,
                    updated_at=datetime.now(UTC),
                )
            )

            # Fetch updated record
            result = await self._session.execute(
                select(PredictionModel).where(PredictionModel.id == prediction.prediction_id)
            )
            updated_model = result.scalar_one()

            return self._model_to_entity(updated_model)

        except PredictionNotFoundError:
            raise
        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to update prediction: {e}", "REPOSITORY_ERROR") from e

    async def delete(self, prediction_id: UUID) -> bool:
        """Delete prediction.

        Args:
            prediction_id: Prediction UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self._session.execute(
                select(PredictionModel).where(PredictionModel.id == prediction_id)
            )
            prediction = result.scalar_one_or_none()

            if prediction:
                await self._session.delete(prediction)
                return True
            return False

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to delete prediction: {e}", "REPOSITORY_ERROR") from e

    async def list_by_model_version(
        self,
        model_version: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prediction]:
        """List predictions by model version.

        Args:
            model_version: Model version string
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of predictions
        """
        try:
            result = await self._session.execute(
                select(PredictionModel)
                .where(PredictionModel.model_version == model_version)
                .order_by(desc(PredictionModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            predictions = result.scalars().all()
            return [self._model_to_entity(pred) for pred in predictions]

        except Exception as e:
            raise DomainException(
                f"Failed to list predictions by model version: {e}", "REPOSITORY_ERROR"
            ) from e

    async def list_by_decision(
        self,
        decision: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prediction]:
        """List predictions by decision.

        Args:
            decision: Prediction decision (approve, review, decline)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of predictions
        """
        try:
            result = await self._session.execute(
                select(PredictionModel)
                .where(PredictionModel.decision == decision)
                .order_by(desc(PredictionModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            predictions = result.scalars().all()
            return [self._model_to_entity(pred) for pred in predictions]

        except Exception as e:
            raise DomainException(
                f"Failed to list predictions by decision: {e}", "REPOSITORY_ERROR"
            ) from e

    async def list_high_risk(
        self,
        min_risk_score: int = 80,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prediction]:
        """List high-risk predictions.

        Args:
            min_risk_score: Minimum risk score threshold
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of high-risk predictions
        """
        try:
            result = await self._session.execute(
                select(PredictionModel)
                .where(PredictionModel.risk_score >= min_risk_score)
                .order_by(desc(PredictionModel.risk_score), desc(PredictionModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            predictions = result.scalars().all()
            return [self._model_to_entity(pred) for pred in predictions]

        except Exception as e:
            raise DomainException(
                f"Failed to list high-risk predictions: {e}", "REPOSITORY_ERROR"
            ) from e

    async def list_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[Prediction]:
        """List predictions within date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of predictions
        """
        try:
            result = await self._session.execute(
                select(PredictionModel)
                .where(
                    and_(
                        PredictionModel.created_at >= start_date,
                        PredictionModel.created_at <= end_date,
                    )
                )
                .order_by(desc(PredictionModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            predictions = result.scalars().all()
            return [self._model_to_entity(pred) for pred in predictions]

        except Exception as e:
            raise DomainException(
                f"Failed to list predictions by date range: {e}", "REPOSITORY_ERROR"
            ) from e

    async def count_by_decision(self, decision: str) -> int:
        """Count predictions by decision.

        Args:
            decision: Prediction decision

        Returns:
            Number of predictions
        """
        try:
            result = await self._session.execute(
                select(func.count(PredictionModel.id)).where(PredictionModel.decision == decision)
            )

            return result.scalar() or 0

        except Exception as e:
            raise DomainException(
                f"Failed to count predictions by decision: {e}", "REPOSITORY_ERROR"
            ) from e

    async def get_model_performance_stats(
        self,
        model_version: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, any]:
        """Get performance statistics for a model version.

        Args:
            model_version: Model version to analyze
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Dictionary with performance statistics
        """
        try:
            query = select(
                func.count(PredictionModel.id).label("total_predictions"),
                func.avg(PredictionModel.fraud_probability).label("avg_fraud_prob"),
                func.avg(PredictionModel.risk_score).label("avg_risk_score"),
                func.avg(PredictionModel.confidence).label("avg_confidence"),
                func.avg(PredictionModel.latency_ms).label("avg_latency"),
                func.sum(func.cast(PredictionModel.prediction_class == "fraud", Integer)).label(
                    "fraud_predictions"
                ),
                func.sum(func.cast(PredictionModel.decision == "approve", Integer)).label(
                    "approved_count"
                ),
                func.sum(func.cast(PredictionModel.decision == "review", Integer)).label(
                    "review_count"
                ),
                func.sum(func.cast(PredictionModel.decision == "decline", Integer)).label(
                    "declined_count"
                ),
            ).where(PredictionModel.model_version == model_version)

            if start_date:
                query = query.where(PredictionModel.created_at >= start_date)
            if end_date:
                query = query.where(PredictionModel.created_at <= end_date)

            result = await self._session.execute(query)
            row = result.first()

            if not row or row.total_predictions == 0:
                return {
                    "total_predictions": 0,
                    "avg_fraud_probability": 0.0,
                    "avg_risk_score": 0.0,
                    "avg_confidence": 0.0,
                    "avg_latency_ms": 0.0,
                    "fraud_rate": 0.0,
                    "approval_rate": 0.0,
                    "review_rate": 0.0,
                    "decline_rate": 0.0,
                }

            total = row.total_predictions
            fraud_rate = (row.fraud_predictions / total * 100) if total > 0 else 0.0
            approval_rate = (row.approved_count / total * 100) if total > 0 else 0.0
            review_rate = (row.review_count / total * 100) if total > 0 else 0.0
            decline_rate = (row.declined_count / total * 100) if total > 0 else 0.0

            return {
                "total_predictions": total,
                "avg_fraud_probability": float(row.avg_fraud_prob or 0),
                "avg_risk_score": float(row.avg_risk_score or 0),
                "avg_confidence": float(row.avg_confidence or 0),
                "avg_latency_ms": float(row.avg_latency or 0),
                "fraud_rate": fraud_rate,
                "approval_rate": approval_rate,
                "review_rate": review_rate,
                "decline_rate": decline_rate,
            }

        except Exception as e:
            raise DomainException(
                f"Failed to get model performance stats: {e}", "REPOSITORY_ERROR"
            ) from e

    async def find_predictions_needing_feedback(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prediction]:
        """Find predictions that need analyst feedback.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of predictions needing feedback
        """
        try:
            result = await self._session.execute(
                select(PredictionModel)
                .where(
                    and_(
                        PredictionModel.decision == "review",
                        PredictionModel.risk_score >= 70,  # High risk predictions
                    )
                )
                .order_by(desc(PredictionModel.risk_score), desc(PredictionModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            predictions = result.scalars().all()
            return [self._model_to_entity(pred) for pred in predictions]

        except Exception as e:
            raise DomainException(
                f"Failed to find predictions needing feedback: {e}", "REPOSITORY_ERROR"
            ) from e

    async def find_by_criteria(
        self,
        model_version: str | None = None,
        prediction_class: str | None = None,
        decision: str | None = None,
        min_fraud_probability: float | None = None,
        max_fraud_probability: float | None = None,
        min_risk_score: int | None = None,
        max_risk_score: int | None = None,
        min_confidence: float | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> list[Prediction]:
        """Find predictions by multiple criteria.

        Args:
            model_version: Model version filter
            prediction_class: Prediction class filter
            decision: Decision filter
            min_fraud_probability: Minimum fraud probability
            max_fraud_probability: Maximum fraud probability
            min_risk_score: Minimum risk score
            max_risk_score: Maximum risk score
            min_confidence: Minimum confidence
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum results
            offset: Results offset
            sort_by: Field to sort by
            sort_desc: Sort descending if True

        Returns:
            List of matching predictions
        """
        try:
            query = select(PredictionModel)

            # Add filters dynamically
            if model_version:
                query = query.where(PredictionModel.model_version == model_version)
            if prediction_class:
                query = query.where(PredictionModel.prediction_class == prediction_class)
            if decision:
                query = query.where(PredictionModel.decision == decision)
            if min_fraud_probability is not None:
                query = query.where(PredictionModel.fraud_probability >= min_fraud_probability)
            if max_fraud_probability is not None:
                query = query.where(PredictionModel.fraud_probability <= max_fraud_probability)
            if min_risk_score is not None:
                query = query.where(PredictionModel.risk_score >= min_risk_score)
            if max_risk_score is not None:
                query = query.where(PredictionModel.risk_score <= max_risk_score)
            if min_confidence is not None:
                query = query.where(PredictionModel.confidence >= min_confidence)
            if start_date:
                query = query.where(PredictionModel.created_at >= start_date)
            if end_date:
                query = query.where(PredictionModel.created_at <= end_date)

            # Add sorting
            sort_column = getattr(PredictionModel, sort_by, PredictionModel.created_at)
            if sort_desc:
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)

            query = query.limit(limit).offset(offset)

            result = await self._session.execute(query)
            predictions = result.scalars().all()

            return [self._model_to_entity(pred) for pred in predictions]

        except Exception as e:
            raise DomainException(
                f"Failed to find predictions by criteria: {e}", "REPOSITORY_ERROR"
            ) from e

    def _model_to_entity(self, model: PredictionModel) -> Prediction:
        """Convert database model to domain entity.

        Args:
            model: SQLAlchemy model instance

        Returns:
            Domain entity
        """
        return Prediction(
            prediction_id=model.id,
            transaction_id=model.transaction_id,
            model_version=model.model_version,
            fraud_probability=model.fraud_probability,
            anomaly_score=model.anomaly_score or 0.0,
            risk_score=int(model.risk_score or 0),
            predicted_class=model.prediction_class,
            decision=model.decision,
            confidence=model.confidence or 0.0,
            explanation_data=model.explanation_data or {},
            latency_ms=int(model.latency_ms or 0),
            timestamp=model.created_at,
            analyst_feedback_id=None,  # Would need separate feedback table
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
