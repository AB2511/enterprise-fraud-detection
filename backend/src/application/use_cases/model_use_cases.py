"""Model Use Cases (CQRS Pattern) - STUB Implementation."""

# NOTE: Model use cases are stubbed pending implementation of ModelService
# The Model entity exists but the service layer for models needs to be implemented

from uuid import UUID

from src.application.dtos.model_dtos import (
    CreateModelRequest,
    ModelResponse,
)

# from src.application.services.model_service import ModelService  # TODO: Implement this service
from src.domain.entities.model import Model


class CreateModelUseCase:
    """Use case for creating a new model."""

    def __init__(self, model_service: object | None = None) -> None:
        """Initialize use case.

        Args:
            model_service: Model service instance (TODO: implement ModelService)
        """
        self._service = model_service

    async def execute(
        self,
        request: CreateModelRequest,
        user_id: UUID | None = None,
    ) -> ModelResponse:
        """Execute create model use case."""
        raise NotImplementedError("ModelService not yet implemented")

    @staticmethod
    def _to_response(model: Model) -> ModelResponse:
        """Convert domain entity to response DTO."""
        return ModelResponse(
            model_id=model.model_id,
            version=model.version,
            model_type=model.model_type,
            artifact_path=model.artifact_path,
            metadata=model.metadata,
            metrics=model.metrics,
            training_date=model.training_date,
            status=model.status,
            is_production=model.is_production,
            is_archived=model.is_archived,
            created_by=model.created_by,
            created_at=model.created_at,
        )


# TODO: Implement remaining model use cases when ModelService is available:
# - UpdateModelUseCase
# - GetModelUseCase
# - ListModelsUseCase
# - PromoteModelUseCase
# - ArchiveModelUseCase
# - GetModelStatisticsUseCase
# etc.
