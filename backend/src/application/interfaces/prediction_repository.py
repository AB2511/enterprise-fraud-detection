"""Prediction Repository Interface."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.prediction import Prediction


class PredictionRepository(ABC):
    """Repository interface for Prediction entity."""

    @abstractmethod
    async def create(self, prediction: Prediction) -> Prediction:
        """Create a new prediction.

        Args:
            prediction: Prediction entity to create

        Returns:
            Created prediction with generated ID

        Raises:
            RepositoryError: If creation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, prediction_id: UUID) -> Prediction | None:
        """Retrieve prediction by ID.

        Args:
            prediction_id: Prediction UUID

        Returns:
            Prediction if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_transaction_id(self, transaction_id: UUID) -> Prediction | None:
        """Retrieve prediction by transaction ID.

        Args:
            transaction_id: Transaction UUID

        Returns:
            Prediction if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, prediction: Prediction) -> Prediction:
        """Update existing prediction.

        Args:
            prediction: Prediction entity with updated data

        Returns:
            Updated prediction

        Raises:
            RepositoryError: If update fails
            NotFoundError: If prediction doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, prediction_id: UUID) -> bool:
        """Delete prediction.

        Args:
            prediction_id: Prediction UUID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def count_by_decision(self, decision: str) -> int:
        """Count predictions by decision.

        Args:
            decision: Prediction decision

        Returns:
            Number of predictions
        """
        pass

    @abstractmethod
    async def get_model_performance_stats(
        self,
        model_version: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, object]:
        """Get performance statistics for a model version.

        Args:
            model_version: Model version to analyze
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Dictionary with performance statistics
        """
        pass

    @abstractmethod
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
        pass
