"""Model Repository Interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.model import Model


class ModelRepository(ABC):
    """Repository interface for Model entity."""

    @abstractmethod
    async def create(self, model: Model) -> Model:
        """Create a new model.

        Args:
            model: Model entity to create

        Returns:
            Created model with generated ID

        Raises:
            RepositoryError: If creation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, model_id: UUID) -> Model | None:
        """Retrieve model by ID.

        Args:
            model_id: Model UUID

        Returns:
            Model if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_version(self, version: str) -> Model | None:
        """Retrieve model by version string.

        Args:
            version: Model version (e.g., "1.0.0")

        Returns:
            Model if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, model: Model) -> Model:
        """Update existing model.

        Args:
            model: Model entity with updated data

        Returns:
            Updated model

        Raises:
            RepositoryError: If update fails
            NotFoundError: If model doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, model_id: UUID) -> bool:
        """Delete model.

        Args:
            model_id: Model UUID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        pass

    @abstractmethod
    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Model]:
        """List models by status.

        Args:
            status: Model status (training, staging, production, archived)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of models
        """
        pass

    @abstractmethod
    async def list_by_type(
        self,
        model_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Model]:
        """List models by type.

        Args:
            model_type: Model type (xgboost, isolation_forest, etc.)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of models
        """
        pass

    @abstractmethod
    async def get_production_models(self) -> list[Model]:
        """Get all production models.

        Returns:
            List of production models
        """
        pass

    @abstractmethod
    async def get_latest_model(self, model_type: str | None = None) -> Model | None:
        """Get latest model by training date.

        Args:
            model_type: Optional filter by model type

        Returns:
            Latest model if found, None otherwise
        """
        pass

    @abstractmethod
    async def promote_to_production(self, model_id: UUID) -> Model:
        """Promote model to production status.

        Args:
            model_id: Model UUID to promote

        Returns:
            Updated model

        Raises:
            NotFoundError: If model doesn't exist
            RepositoryError: If promotion fails
        """
        pass

    @abstractmethod
    async def archive_model(self, model_id: UUID) -> Model:
        """Archive a model.

        Args:
            model_id: Model UUID to archive

        Returns:
            Updated model

        Raises:
            NotFoundError: If model doesn't exist
            RepositoryError: If archival fails
        """
        pass

    @abstractmethod
    async def count_by_status(self, status: str) -> int:
        """Count models by status.

        Args:
            status: Model status

        Returns:
            Number of models
        """
        pass

    @abstractmethod
    async def get_model_lineage(self, model_id: UUID) -> list[Model]:
        """Get model version history/lineage.

        Args:
            model_id: Model UUID

        Returns:
            List of related model versions
        """
        pass
