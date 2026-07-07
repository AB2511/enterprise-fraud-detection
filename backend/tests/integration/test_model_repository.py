"""Integration tests for ModelRepositoryImpl."""

import pytest
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.model import Model
from src.domain.exceptions.base import NotFoundError, RepositoryError
from src.infrastructure.database.repositories.model_repository_impl import ModelRepositoryImpl


class TestModelRepositoryImpl:
    """Test suite for ModelRepositoryImpl."""

    @pytest.fixture
    async def repository(self, async_session: AsyncSession) -> ModelRepositoryImpl:
        """Create repository instance."""
        return ModelRepositoryImpl(async_session)

    @pytest.fixture
    def sample_model(self) -> Model:
        """Create sample model entity."""
        return Model(
            version="1.0.0",
            model_type="xgboost",
            artifact_path="s3://ml-models/fraud/v1.0.0/model.pkl",
            metadata={
                "hyperparameters": {"n_estimators": 100, "max_depth": 6},
                "dataset_version": "2024-01",
                "features_count": 47
            },
            metrics={
                "accuracy": 0.95,
                "precision": 0.92,
                "recall": 0.88,
                "f1_score": 0.90
            },
            created_by="data_scientist@company.com"
        )

    async def test_create_model(self, repository: ModelRepositoryImpl, sample_model: Model):
        """Test model creation."""
        # Act
        created = await repository.create(sample_model)
        
        # Assert
        assert created.model_id is not None
        assert created.version == "1.0.0"
        assert created.model_type == "xgboost"
        assert created.status == "training"
        assert created.artifact_path == "s3://ml-models/fraud/v1.0.0/model.pkl"
        assert created.metadata["hyperparameters"]["n_estimators"] == 100
        assert created.metrics["accuracy"] == 0.95

    async def test_get_by_id(self, repository: ModelRepositoryImpl, sample_model: Model):
        """Test retrieving model by ID."""
        # Arrange
        created = await repository.create(sample_model)
        
        # Act
        retrieved = await repository.get_by_id(created.model_id)
        
        # Assert
        assert retrieved is not None
        assert retrieved.model_id == created.model_id
        assert retrieved.version == "1.0.0"

    async def test_get_by_id_not_found(self, repository: ModelRepositoryImpl):
        """Test retrieving non-existent model returns None."""
        # Act
        result = await repository.get_by_id(uuid4())
        
        # Assert
        assert result is None

    async def test_get_by_version(self, repository: ModelRepositoryImpl, sample_model: Model):
        """Test retrieving model by version."""
        # Arrange
        await repository.create(sample_model)
        
        # Act
        retrieved = await repository.get_by_version("1.0.0")
        
        # Assert
        assert retrieved is not None
        assert retrieved.version == "1.0.0"

    async def test_get_by_version_not_found(self, repository: ModelRepositoryImpl):
        """Test retrieving model by non-existent version returns None."""
        # Act
        result = await repository.get_by_version("999.0.0")
        
        # Assert
        assert result is None

    async def test_update_model(self, repository: ModelRepositoryImpl, sample_model: Model):
        """Test updating model."""
        # Arrange
        created = await repository.create(sample_model)
        created.status = "staging"
        created.metrics["accuracy"] = 0.96
        
        # Act
        updated = await repository.update(created)
        
        # Assert
        assert updated.status == "staging"
        assert updated.metrics["accuracy"] == 0.96
        assert updated.updated_at > updated.created_at

    async def test_update_nonexistent_model_fails(self, repository: ModelRepositoryImpl):
        """Test updating non-existent model fails."""
        # Arrange
        model = Model(
            model_id=uuid4(),
            version="2.0.0",
            model_type="xgboost",
            artifact_path="s3://test/model.pkl"
        )
        
        # Act & Assert
        with pytest.raises(NotFoundError):
            await repository.update(model)

    async def test_delete_model_hard_delete(self, repository: ModelRepositoryImpl, sample_model: Model):
        """Test hard delete functionality."""
        # Arrange
        created = await repository.create(sample_model)
        
        # Act
        result = await repository.delete(created.model_id)
        
        # Assert
        assert result is True
        
        # Verify hard delete - should not be retrievable
        retrieved = await repository.get_by_id(created.model_id)
        assert retrieved is None

    async def test_delete_nonexistent_model(self, repository: ModelRepositoryImpl):
        """Test deleting non-existent model returns False."""
        # Act
        result = await repository.delete(uuid4())
        
        # Assert
        assert result is False

    async def test_list_by_status(self, repository: ModelRepositoryImpl):
        """Test listing models by status."""
        # Arrange
        training_model = Model(version="1.0.0", model_type="xgboost", artifact_path="s3://test1.pkl", status="training")
        production_model = Model(version="2.0.0", model_type="xgboost", artifact_path="s3://test2.pkl", status="production")
        
        await repository.create(training_model)
        await repository.create(production_model)
        
        # Act
        production_models = await repository.list_by_status("production")
        
        # Assert
        assert len(production_models) == 1
        assert production_models[0].status == "production"

    async def test_list_by_type(self, repository: ModelRepositoryImpl):
        """Test listing models by type."""
        # Arrange
        xgboost_model = Model(version="1.0.0", model_type="xgboost", artifact_path="s3://test1.pkl")
        isolation_forest_model = Model(version="2.0.0", model_type="isolation_forest", artifact_path="s3://test2.pkl")
        
        await repository.create(xgboost_model)
        await repository.create(isolation_forest_model)
        
        # Act
        xgboost_models = await repository.list_by_type("xgboost")
        
        # Assert
        assert len(xgboost_models) == 1
        assert xgboost_models[0].model_type == "xgboost"

    async def test_get_production_models(self, repository: ModelRepositoryImpl):
        """Test getting all production models."""
        # Arrange
        prod_model1 = Model(version="1.0.0", model_type="xgboost", artifact_path="s3://test1.pkl", status="production")
        prod_model2 = Model(version="2.0.0", model_type="isolation_forest", artifact_path="s3://test2.pkl", status="production")
        staging_model = Model(version="3.0.0", model_type="xgboost", artifact_path="s3://test3.pkl", status="staging")
        
        await repository.create(prod_model1)
        await repository.create(prod_model2)
        await repository.create(staging_model)
        
        # Act
        production_models = await repository.get_production_models()
        
        # Assert
        assert len(production_models) == 2
        for model in production_models:
            assert model.status == "production"

    async def test_get_latest_model(self, repository: ModelRepositoryImpl):
        """Test getting latest model by training date."""
        # Arrange
        old_model = Model(
            version="1.0.0", 
            model_type="xgboost", 
            artifact_path="s3://test1.pkl",
            training_date=datetime(2024, 1, 1)
        )
        new_model = Model(
            version="2.0.0", 
            model_type="xgboost", 
            artifact_path="s3://test2.pkl",
            training_date=datetime(2024, 2, 1)
        )
        
        await repository.create(old_model)
        await repository.create(new_model)
        
        # Act
        latest = await repository.get_latest_model()
        
        # Assert
        assert latest is not None
        assert latest.version == "2.0.0"

    async def test_get_latest_model_by_type(self, repository: ModelRepositoryImpl):
        """Test getting latest model filtered by type."""
        # Arrange
        xgb_model = Model(
            version="1.0.0", 
            model_type="xgboost", 
            artifact_path="s3://test1.pkl",
            training_date=datetime(2024, 1, 1)
        )
        iso_model = Model(
            version="2.0.0", 
            model_type="isolation_forest", 
            artifact_path="s3://test2.pkl",
            training_date=datetime(2024, 2, 1)
        )
        
        await repository.create(xgb_model)
        await repository.create(iso_model)
        
        # Act
        latest_xgb = await repository.get_latest_model("xgboost")
        
        # Assert
        assert latest_xgb is not None
        assert latest_xgb.model_type == "xgboost"
        assert latest_xgb.version == "1.0.0"

    async def test_promote_to_production(self, repository: ModelRepositoryImpl, sample_model: Model):
        """Test promoting model to production."""
        # Arrange
        sample_model.status = "staging"
        created = await repository.create(sample_model)
        
        # Act
        promoted = await repository.promote_to_production(created.model_id)
        
        # Assert
        assert promoted.status == "production"
        assert promoted.is_production is True

    async def test_promote_already_production_model_fails(self, repository: ModelRepositoryImpl):
        """Test promoting already production model fails."""
        # Arrange
        prod_model = Model(version="1.0.0", model_type="xgboost", artifact_path="s3://test.pkl", status="production")
        created = await repository.create(prod_model)
        
        # Act & Assert
        with pytest.raises(RepositoryError, match="already in production"):
            await repository.promote_to_production(created.model_id)

    async def test_promote_archived_model_fails(self, repository: ModelRepositoryImpl):
        """Test promoting archived model fails."""
        # Arrange
        archived_model = Model(version="1.0.0", model_type="xgboost", artifact_path="s3://test.pkl", status="archived")
        created = await repository.create(archived_model)
        
        # Act & Assert
        with pytest.raises(RepositoryError, match="Cannot promote archived model"):
            await repository.promote_to_production(created.model_id)

    async def test_archive_model(self, repository: ModelRepositoryImpl, sample_model: Model):
        """Test archiving a model."""
        # Arrange
        created = await repository.create(sample_model)
        
        # Act
        archived = await repository.archive_model(created.model_id)
        
        # Assert
        assert archived.status == "archived"
        assert archived.is_archived is True

    async def test_count_by_status(self, repository: ModelRepositoryImpl):
        """Test counting models by status."""
        # Arrange
        for i in range(3):
            model = Model(version=f"{i}.0.0", model_type="xgboost", artifact_path=f"s3://test{i}.pkl", status="training")
            await repository.create(model)
        
        # Act
        count = await repository.count_by_status("training")
        
        # Assert
        assert count == 3

    async def test_get_model_lineage(self, repository: ModelRepositoryImpl):
        """Test getting model lineage by type."""
        # Arrange
        model1 = Model(
            version="1.0.0", 
            model_type="xgboost", 
            artifact_path="s3://test1.pkl",
            training_date=datetime(2024, 1, 1)
        )
        model2 = Model(
            version="2.0.0", 
            model_type="xgboost", 
            artifact_path="s3://test2.pkl",
            training_date=datetime(2024, 2, 1)
        )
        different_type = Model(
            version="1.0.0", 
            model_type="isolation_forest", 
            artifact_path="s3://test3.pkl"
        )
        
        created1 = await repository.create(model1)
        await repository.create(model2)
        await repository.create(different_type)
        
        # Act
        lineage = await repository.get_model_lineage(created1.model_id)
        
        # Assert
        assert len(lineage) == 2  # Only xgboost models
        for model in lineage:
            assert model.model_type == "xgboost"

    async def test_get_model_statistics(self, repository: ModelRepositoryImpl):
        """Test getting model statistics."""
        # Arrange
        training_model = Model(version="1.0.0", model_type="xgboost", artifact_path="s3://test1.pkl", status="training")
        production_model = Model(version="2.0.0", model_type="isolation_forest", artifact_path="s3://test2.pkl", status="production")
        
        await repository.create(training_model)
        await repository.create(production_model)
        
        # Act
        stats = await repository.get_model_statistics()
        
        # Assert
        assert stats["total"] == 2
        assert "by_status" in stats
        assert "by_type" in stats
        assert stats["by_status"]["training"] == 1
        assert stats["by_status"]["production"] == 1
        assert stats["by_type"]["xgboost"] == 1
        assert stats["by_type"]["isolation_forest"] == 1

    async def test_search_models(self, repository: ModelRepositoryImpl):
        """Test advanced model search."""
        # Arrange
        model1 = Model(version="1.0.0", model_type="xgboost", artifact_path="s3://test1.pkl", status="production", created_by="user1")
        model2 = Model(version="2.0.0", model_type="xgboost", artifact_path="s3://test2.pkl", status="staging", created_by="user2")
        model3 = Model(version="3.0.0", model_type="isolation_forest", artifact_path="s3://test3.pkl", status="production", created_by="user1")
        
        await repository.create(model1)
        await repository.create(model2)
        await repository.create(model3)
        
        # Act - Search by multiple filters
        results = await repository.search_models(
            model_type="xgboost",
            status="production",
            created_by="user1"
        )
        
        # Assert
        assert len(results) == 1
        assert results[0].version == "1.0.0"

    async def test_get_models_by_date_range(self, repository: ModelRepositoryImpl):
        """Test getting models by date range."""
        # Arrange
        old_model = Model(
            version="1.0.0", 
            model_type="xgboost", 
            artifact_path="s3://test1.pkl",
            training_date=datetime(2024, 1, 1)
        )
        recent_model = Model(
            version="2.0.0", 
            model_type="xgboost", 
            artifact_path="s3://test2.pkl",
            training_date=datetime(2024, 6, 1)
        )
        
        await repository.create(old_model)
        await repository.create(recent_model)
        
        # Act
        recent_models = await repository.get_models_by_date_range(
            start_date=datetime(2024, 5, 1),
            end_date=datetime(2024, 12, 31)
        )
        
        # Assert
        assert len(recent_models) == 1
        assert recent_models[0].version == "2.0.0"

    async def test_pagination_parameters(self, repository: ModelRepositoryImpl):
        """Test pagination limits and offsets."""
        # Arrange
        for i in range(5):
            model = Model(version=f"{i}.0.0", model_type="xgboost", artifact_path=f"s3://test{i}.pkl")
            await repository.create(model)
        
        # Act
        page1 = await repository.list_by_type("xgboost", limit=2, offset=0)
        page2 = await repository.list_by_type("xgboost", limit=2, offset=2)
        
        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].model_id != page2[0].model_id

    async def test_version_uniqueness(self, repository: ModelRepositoryImpl):
        """Test that version strings must be unique."""
        # Arrange
        model1 = Model(version="1.0.0", model_type="xgboost", artifact_path="s3://test1.pkl")
        model2 = Model(version="1.0.0", model_type="isolation_forest", artifact_path="s3://test2.pkl")
        
        # Act
        await repository.create(model1)
        
        # Assert - Should handle duplicate versions (database constraint)
        with pytest.raises(RepositoryError):
            await repository.create(model2)

    async def test_metadata_and_metrics_serialization(self, repository: ModelRepositoryImpl):
        """Test that complex metadata and metrics are properly serialized."""
        # Arrange
        complex_model = Model(
            version="1.0.0",
            model_type="neural_network",
            artifact_path="s3://test.pkl",
            metadata={
                "layers": [{"type": "dense", "units": 128}, {"type": "dropout", "rate": 0.2}],
                "optimizer": {"name": "adam", "learning_rate": 0.001},
                "nested": {"deep": {"value": 42}}
            },
            metrics={
                "train_accuracy": 0.95,
                "val_accuracy": 0.92,
                "test_accuracy": 0.90,
                "confusion_matrix": [[100, 5], [8, 87]]
            }
        )
        
        # Act
        created = await repository.create(complex_model)
        retrieved = await repository.get_by_id(created.model_id)
        
        # Assert
        assert retrieved.metadata["layers"][0]["type"] == "dense"
        assert retrieved.metadata["nested"]["deep"]["value"] == 42
        assert retrieved.metrics["confusion_matrix"] == [[100, 5], [8, 87]]