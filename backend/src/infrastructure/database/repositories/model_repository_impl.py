"""Model Repository Implementation using SQLAlchemy."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.model_repository import ModelRepository
from src.domain.entities.model import Model
from src.domain.exceptions.base import DomainException, NotFoundError, RepositoryError
from src.infrastructure.database.models import ModelModel


class ModelRepositoryImpl(ModelRepository):
    """SQLAlchemy implementation of ModelRepository.

    Provides complete CRUD operations, version management, lifecycle tracking,
    and deployment control for ML model entities.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self._session = session

    async def create(self, model: Model) -> Model:
        """Create a new model with version uniqueness validation.

        Args:
            model: Model entity to create

        Returns:
            Created model with generated ID

        Raises:
            RepositoryError: If creation fails
        """
        try:
            db_model = ModelModel(
                id=model.model_id,
                version=model.version,
                model_type=model.model_type,
                artifact_path=model.artifact_path,
                model_metadata=model.metadata,
                metrics=model.metrics,
                training_date=model.training_date,
                status=model.status,
                created_by=model.created_by,
                created_at=model.created_at,
                updated_at=model.created_at,
            )

            self._session.add(db_model)
            await self._session.flush()
            await self._session.refresh(db_model)

            return self._to_entity(db_model)

        except Exception as e:
            raise RepositoryError(f"Failed to create model: {e}") from e

    async def get_by_id(self, model_id: UUID) -> Model | None:
        """Retrieve model by ID.

        Args:
            model_id: Model UUID

        Returns:
            Model if found, None otherwise
        """
        try:
            query = select(ModelModel).where(ModelModel.id == model_id)
            result = await self._session.execute(query)
            db_model = result.scalar_one_or_none()

            return self._to_entity(db_model) if db_model else None

        except Exception as e:
            raise RepositoryError(f"Failed to get model by id: {e}") from e

    async def get_by_version(self, version: str) -> Model | None:
        """Retrieve model by version string.

        Args:
            version: Model version (e.g., "1.0.0")

        Returns:
            Model if found, None otherwise
        """
        try:
            query = select(ModelModel).where(ModelModel.version == version)
            result = await self._session.execute(query)
            db_model = result.scalar_one_or_none()

            return self._to_entity(db_model) if db_model else None

        except Exception as e:
            raise RepositoryError(f"Failed to get model by version: {e}") from e

    async def update(self, model: Model) -> Model:
        """Update existing model.

        Args:
            model: Model entity with updated data

        Returns:
            Updated model

        Raises:
            NotFoundError: If model doesn't exist
            RepositoryError: If update fails
        """
        try:
            query = select(ModelModel).where(ModelModel.id == model.model_id)
            result = await self._session.execute(query)
            db_model = result.scalar_one_or_none()

            if not db_model:
                raise NotFoundError(f"Model {model.model_id} not found")

            # Update fields (version should not be changed in updates)
            db_model.model_type = model.model_type
            db_model.artifact_path = model.artifact_path
            db_model.model_metadata = model.metadata
            db_model.metrics = model.metrics
            db_model.training_date = model.training_date
            db_model.status = model.status
            db_model.created_by = model.created_by
            db_model.updated_at = datetime.now(UTC)

            await self._session.flush()
            await self._session.refresh(db_model)

            return self._to_entity(db_model)

        except NotFoundError:
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to update model: {e}") from e

    async def delete(self, model_id: UUID) -> bool:
        """Delete model (hard delete for models).

        Args:
            model_id: Model UUID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        try:
            query = select(ModelModel).where(ModelModel.id == model_id)
            result = await self._session.execute(query)
            db_model = result.scalar_one_or_none()

            if not db_model:
                return False

            await self._session.delete(db_model)
            await self._session.flush()

            return True

        except Exception as e:
            raise RepositoryError(f"Failed to delete model: {e}") from e

    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Model]:
        """List models by status with pagination.

        Args:
            status: Model status (training, staging, production, archived)
            limit: Maximum number of results (max 1000)
            offset: Number of results to skip

        Returns:
            List of models
        """
        try:
            # Validate and cap limit
            limit = min(max(1, limit), 1000)
            offset = max(0, offset)

            query = (
                select(ModelModel)
                .where(ModelModel.status == status)
                .order_by(desc(ModelModel.training_date))
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(query)
            db_models = result.scalars().all()

            return [self._to_entity(db_model) for db_model in db_models]

        except Exception as e:
            raise RepositoryError(f"Failed to list models by status: {e}") from e

    async def list_by_type(
        self,
        model_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Model]:
        """List models by type with pagination.

        Args:
            model_type: Model type (xgboost, isolation_forest, etc.)
            limit: Maximum number of results (max 1000)
            offset: Number of results to skip

        Returns:
            List of models
        """
        try:
            # Validate and cap limit
            limit = min(max(1, limit), 1000)
            offset = max(0, offset)

            query = (
                select(ModelModel)
                .where(ModelModel.model_type == model_type)
                .order_by(desc(ModelModel.training_date))
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(query)
            db_models = result.scalars().all()

            return [self._to_entity(db_model) for db_model in db_models]

        except Exception as e:
            raise RepositoryError(f"Failed to list models by type: {e}") from e

    async def get_production_models(self) -> list[Model]:
        """Get all production models ordered by training date.

        Returns:
            List of production models
        """
        try:
            query = (
                select(ModelModel)
                .where(ModelModel.status == "production")
                .order_by(desc(ModelModel.training_date))
            )

            result = await self._session.execute(query)
            db_models = result.scalars().all()

            return [self._to_entity(db_model) for db_model in db_models]

        except Exception as e:
            raise RepositoryError(f"Failed to get production models: {e}") from e

    async def get_latest_model(self, model_type: str | None = None) -> Model | None:
        """Get latest model by training date, optionally filtered by type.

        Args:
            model_type: Optional filter by model type

        Returns:
            Latest model if found, None otherwise
        """
        try:
            query = select(ModelModel)

            if model_type:
                query = query.where(ModelModel.model_type == model_type)

            query = query.order_by(desc(ModelModel.training_date)).limit(1)

            result = await self._session.execute(query)
            db_model = result.scalar_one_or_none()

            return self._to_entity(db_model) if db_model else None

        except Exception as e:
            raise RepositoryError(f"Failed to get latest model: {e}") from e

    async def promote_to_production(self, model_id: UUID) -> Model:
        """Promote model to production status.

        This is a critical operation that should be carefully controlled.
        Consider implementing approval workflows in application layer.

        Args:
            model_id: Model UUID to promote

        Returns:
            Updated model

        Raises:
            NotFoundError: If model doesn't exist
            RepositoryError: If promotion fails
        """
        try:
            query = select(ModelModel).where(ModelModel.id == model_id)
            result = await self._session.execute(query)
            db_model = result.scalar_one_or_none()

            if not db_model:
                raise NotFoundError(f"Model {model_id} not found")

            # Validate business rules for promotion
            if db_model.status == "production":
                raise RepositoryError("Model is already in production")

            if db_model.status == "archived":
                raise RepositoryError("Cannot promote archived model")

            db_model.status = "production"
            db_model.updated_at = datetime.now(UTC)

            await self._session.flush()
            await self._session.refresh(db_model)

            return self._to_entity(db_model)

        except (NotFoundError, RepositoryError):
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to promote model to production: {e}") from e

    async def archive_model(self, model_id: UUID) -> Model:
        """Archive a model (mark as no longer active).

        Args:
            model_id: Model UUID to archive

        Returns:
            Updated model

        Raises:
            NotFoundError: If model doesn't exist
            RepositoryError: If archival fails
        """
        try:
            query = select(ModelModel).where(ModelModel.id == model_id)
            result = await self._session.execute(query)
            db_model = result.scalar_one_or_none()

            if not db_model:
                raise NotFoundError(f"Model {model_id} not found")

            db_model.status = "archived"
            db_model.updated_at = datetime.now(UTC)

            await self._session.flush()
            await self._session.refresh(db_model)

            return self._to_entity(db_model)

        except NotFoundError:
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to archive model: {e}") from e

    async def count_by_status(self, status: str) -> int:
        """Count models by status.

        Args:
            status: Model status

        Returns:
            Number of models with the specified status
        """
        try:
            query = select(func.count(ModelModel.id)).where(ModelModel.status == status)
            result = await self._session.execute(query)
            return result.scalar() or 0

        except Exception as e:
            raise RepositoryError(f"Failed to count models by status: {e}") from e

    async def get_model_lineage(self, model_id: UUID) -> list[Model]:
        """Get model version history/lineage.

        For now, this returns models of the same type ordered by training date.
        A more sophisticated implementation might track explicit parent-child relationships.

        Args:
            model_id: Model UUID

        Returns:
            List of related model versions
        """
        try:
            # First get the target model to find its type
            query = select(ModelModel).where(ModelModel.id == model_id)
            result = await self._session.execute(query)
            target_model = result.scalar_one_or_none()

            if not target_model:
                return []

            # Get all models of the same type
            lineage_query = (
                select(ModelModel)
                .where(ModelModel.model_type == target_model.model_type)
                .order_by(desc(ModelModel.training_date))
            )

            lineage_result = await self._session.execute(lineage_query)
            db_models = lineage_result.scalars().all()

            return [self._to_entity(db_model) for db_model in db_models]

        except Exception as e:
            raise DomainException(f"Failed to get model lineage: {e}", "REPOSITORY_ERROR") from e

    # Additional methods for model management and analytics

    async def get_model_statistics(self) -> dict[str, any]:
        """Get comprehensive model statistics.

        Returns:
            Dictionary with model counts and metrics by various dimensions
        """
        try:
            # Count by status
            status_query = select(ModelModel.status, func.count(ModelModel.id)).group_by(
                ModelModel.status
            )
            status_result = await self._session.execute(status_query)
            status_counts = dict(status_result.all())

            # Count by type
            type_query = select(ModelModel.model_type, func.count(ModelModel.id)).group_by(
                ModelModel.model_type
            )
            type_result = await self._session.execute(type_query)
            type_counts = dict(type_result.all())

            # Total count
            total_query = select(func.count(ModelModel.id))
            total_result = await self._session.execute(total_query)
            total_count = total_result.scalar() or 0

            # Latest training date
            latest_query = select(func.max(ModelModel.training_date))
            latest_result = await self._session.execute(latest_query)
            latest_training = latest_result.scalar()

            return {
                "total": total_count,
                "by_status": status_counts,
                "by_type": type_counts,
                "latest_training_date": latest_training.isoformat() if latest_training else None,
            }

        except Exception as e:
            raise RepositoryError(f"Failed to get model statistics: {e}") from e

    async def search_models(
        self,
        model_type: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Model]:
        """Advanced model search with multiple filters.

        Args:
            model_type: Optional model type filter
            status: Optional status filter
            created_by: Optional creator filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of models matching criteria
        """
        try:
            limit = min(max(1, limit), 1000)
            offset = max(0, offset)

            query = select(ModelModel)

            # Apply filters
            conditions = []
            if model_type:
                conditions.append(ModelModel.model_type == model_type)
            if status:
                conditions.append(ModelModel.status == status)
            if created_by:
                conditions.append(ModelModel.created_by == created_by)

            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(desc(ModelModel.training_date)).limit(limit).offset(offset)

            result = await self._session.execute(query)
            db_models = result.scalars().all()

            return [self._to_entity(db_model) for db_model in db_models]

        except Exception as e:
            raise RepositoryError(f"Failed to search models: {e}") from e

    async def get_models_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Model]:
        """Get models trained within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of models trained in the date range
        """
        try:
            limit = min(max(1, limit), 1000)
            offset = max(0, offset)

            query = (
                select(ModelModel)
                .where(
                    and_(
                        ModelModel.training_date >= start_date,
                        ModelModel.training_date <= end_date,
                    )
                )
                .order_by(desc(ModelModel.training_date))
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(query)
            db_models = result.scalars().all()

            return [self._to_entity(db_model) for db_model in db_models]

        except Exception as e:
            raise RepositoryError(f"Failed to get models by date range: {e}") from e

    def _to_entity(self, db_model: ModelModel) -> Model:
        """Convert database model to domain entity.

        Args:
            db_model: SQLAlchemy model model

        Returns:
            Model domain entity
        """
        return Model(
            model_id=db_model.id,
            version=db_model.version,
            model_type=db_model.model_type,
            artifact_path=db_model.artifact_path,
            metadata=db_model.model_metadata,
            metrics=db_model.metrics,
            training_date=db_model.training_date,
            status=db_model.status,
            created_by=db_model.created_by,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
        )

    def _to_model(self, model: Model) -> ModelModel:
        """Convert domain entity to database model.

        Args:
            model: Model domain entity

        Returns:
            SQLAlchemy model model
        """
        return ModelModel(
            id=model.model_id,
            version=model.version,
            model_type=model.model_type,
            artifact_path=model.artifact_path,
            model_metadata=model.metadata,
            metrics=model.metrics,
            training_date=model.training_date,
            status=model.status,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
