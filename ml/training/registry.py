"""
Model Registry

Local model registry for tracking trained models, metadata, and artifacts.
Provides versioning, status management, and artifact organization.
"""

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import joblib

from ml.utils.file_manager import atomic_write_json
from ml.utils.logging_config import get_logger


class ModelStatus(Enum):
    """Model status in the registry."""

    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"
    PRODUCTION = "production"
    STAGING = "staging"


@dataclass
class ModelArtifacts:
    """Container for model artifacts and their paths."""

    # Core artifacts
    model_path: Path | None = None
    config_path: Path | None = None
    metrics_path: Path | None = None

    # Training artifacts
    training_report_path: Path | None = None
    feature_importance_path: Path | None = None
    predictions_path: Path | None = None

    # Evaluation artifacts
    roc_curve_path: Path | None = None
    pr_curve_path: Path | None = None
    confusion_matrix_path: Path | None = None
    calibration_curve_path: Path | None = None
    feature_importance_plot_path: Path | None = None

    # Interactive artifacts
    dashboard_path: Path | None = None

    # Logs and metadata
    training_log_path: Path | None = None
    environment_path: Path | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Convert artifacts to dictionary with string paths."""
        return {k: str(v) if v else None for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelArtifacts":
        """Create ModelArtifacts from dictionary."""
        # Convert string paths back to Path objects
        artifacts = {}
        for key, value in data.items():
            if value is not None:
                artifacts[key] = Path(value)
            else:
                artifacts[key] = None
        return cls(**artifacts)


@dataclass
class TrainingMetadata:
    """Comprehensive training metadata."""

    # Model identification
    model_id: str
    model_name: str
    model_version: str
    model_type: str  # "xgboost", "isolation_forest", etc.

    # Training information
    training_start_time: str
    training_end_time: str | None = None
    training_duration_seconds: float | None = None

    # Data information
    dataset_name: str | None = None
    dataset_version: str | None = None
    feature_version: str | None = None
    n_training_samples: int | None = None
    n_validation_samples: int | None = None
    n_test_samples: int | None = None
    n_features: int | None = None

    # Performance metrics
    train_metrics: dict[str, float] = field(default_factory=dict)
    validation_metrics: dict[str, float] = field(default_factory=dict)
    test_metrics: dict[str, float] = field(default_factory=dict)
    cv_metrics: dict[str, float] | None = None

    # Configuration
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    training_config: dict[str, Any] = field(default_factory=dict)

    # Environment
    python_version: str | None = None
    framework_versions: dict[str, str] = field(default_factory=dict)
    git_commit: str | None = None

    # Experiment tracking
    experiment_id: str | None = None
    run_id: str | None = None

    # Registry metadata
    created_by: str | None = None
    status: ModelStatus = ModelStatus.TRAINING
    tags: list[str] = field(default_factory=list)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainingMetadata":
        """Create TrainingMetadata from dictionary."""
        # Convert status string back to enum
        if "status" in data:
            data["status"] = ModelStatus(data["status"])
        return cls(**data)


class ModelRegistry:
    """
    Local model registry for managing trained models and metadata.

    Provides:
    - Model versioning and tracking
    - Artifact management
    - Metadata storage and retrieval
    - Model lifecycle management
    - Search and filtering capabilities
    """

    def __init__(self, registry_path: Path = Path("models/registry")):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)

        # Registry structure
        self.models_dir = self.registry_path / "models"
        self.metadata_dir = self.registry_path / "metadata"
        self.artifacts_dir = self.registry_path / "artifacts"

        # Create subdirectories
        self.models_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)
        self.artifacts_dir.mkdir(exist_ok=True)

        # Registry index
        self.index_file = self.registry_path / "registry_index.json"

        self.logger = get_logger("ml.training.ModelRegistry")

        # Load existing registry
        self._load_registry_index()

    def register_model(
        self,
        model: Any,
        metadata: TrainingMetadata,
        artifacts: ModelArtifacts | None = None,
        save_model: bool = True,
    ) -> str:
        """
        Register a trained model in the registry.

        Args:
            model: Trained model object
            metadata: Training metadata
            artifacts: Model artifacts
            save_model: Whether to save the model to disk

        Returns:
            Model ID in the registry
        """
        model_id = metadata.model_id

        with self.logger.stage_context(f"registering_model_{model_id}"):
            # Create model directory
            model_dir = self.models_dir / model_id
            model_dir.mkdir(exist_ok=True)

            # Save model if requested
            if save_model and model is not None:
                model_path = model_dir / f"{model_id}_model.pkl"
                try:
                    joblib.dump(model, model_path)
                    self.logger.info(f"Saved model to {model_path}")

                    # Update artifacts with model path
                    if artifacts is None:
                        artifacts = ModelArtifacts()
                    artifacts.model_path = model_path

                except Exception as e:
                    self.logger.error(f"Failed to save model: {e}")

            # Save metadata
            metadata_path = self.metadata_dir / f"{model_id}_metadata.json"
            atomic_write_json(metadata.to_dict(), metadata_path)

            # Save artifacts information
            if artifacts:
                artifacts_path = self.metadata_dir / f"{model_id}_artifacts.json"
                atomic_write_json(artifacts.to_dict(), artifacts_path)

            # Update registry index
            self._update_registry_index(model_id, metadata, artifacts)

            self.logger.info(f"Registered model: {model_id}")

            return model_id

    def get_model(self, model_id: str) -> Any | None:
        """
        Load a model from the registry.

        Args:
            model_id: Model identifier

        Returns:
            Loaded model or None if not found
        """
        metadata = self.get_metadata(model_id)
        if not metadata:
            return None

        artifacts = self.get_artifacts(model_id)
        if not artifacts or not artifacts.model_path:
            self.logger.warning(f"No model file found for {model_id}")
            return None

        try:
            model = joblib.load(artifacts.model_path)
            self.logger.info(f"Loaded model: {model_id}")
            return model

        except Exception as e:
            self.logger.error(f"Failed to load model {model_id}: {e}")
            return None

    def get_metadata(self, model_id: str) -> TrainingMetadata | None:
        """
        Get metadata for a model.

        Args:
            model_id: Model identifier

        Returns:
            TrainingMetadata or None if not found
        """
        metadata_path = self.metadata_dir / f"{model_id}_metadata.json"

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path) as f:
                data = json.load(f)

            return TrainingMetadata.from_dict(data)

        except Exception as e:
            self.logger.error(f"Failed to load metadata for {model_id}: {e}")
            return None

    def get_artifacts(self, model_id: str) -> ModelArtifacts | None:
        """
        Get artifacts for a model.

        Args:
            model_id: Model identifier

        Returns:
            ModelArtifacts or None if not found
        """
        artifacts_path = self.metadata_dir / f"{model_id}_artifacts.json"

        if not artifacts_path.exists():
            return None

        try:
            with open(artifacts_path) as f:
                data = json.load(f)

            return ModelArtifacts.from_dict(data)

        except Exception as e:
            self.logger.error(f"Failed to load artifacts for {model_id}: {e}")
            return None

    def list_models(
        self,
        model_type: str | None = None,
        status: ModelStatus | None = None,
        tags: list[str] | None = None,
        limit: int | None = None,
    ) -> list[TrainingMetadata]:
        """
        List models in the registry with optional filtering.

        Args:
            model_type: Filter by model type
            status: Filter by status
            tags: Filter by tags (must have all tags)
            limit: Maximum number of results

        Returns:
            List of TrainingMetadata
        """
        models = []

        for metadata_file in self.metadata_dir.glob("*_metadata.json"):
            try:
                metadata = self.get_metadata(metadata_file.stem.replace("_metadata", ""))
                if metadata:
                    # Apply filters
                    if model_type and metadata.model_type != model_type:
                        continue

                    if status and metadata.status != status:
                        continue

                    if tags and not all(tag in metadata.tags for tag in tags):
                        continue

                    models.append(metadata)

            except Exception as e:
                self.logger.warning(f"Could not load metadata from {metadata_file}: {e}")

        # Sort by creation time (newest first)
        models.sort(key=lambda x: x.training_start_time, reverse=True)

        # Apply limit
        if limit:
            models = models[:limit]

        return models

    def update_status(self, model_id: str, status: ModelStatus, notes: str | None = None):
        """
        Update model status in the registry.

        Args:
            model_id: Model identifier
            status: New status
            notes: Optional notes about the status change
        """
        metadata = self.get_metadata(model_id)
        if not metadata:
            raise ValueError(f"Model not found: {model_id}")

        old_status = metadata.status
        metadata.status = status

        if notes:
            if metadata.notes:
                metadata.notes += f"\n{datetime.utcnow().isoformat()}: {notes}"
            else:
                metadata.notes = f"{datetime.utcnow().isoformat()}: {notes}"

        # Save updated metadata
        metadata_path = self.metadata_dir / f"{model_id}_metadata.json"
        atomic_write_json(metadata.to_dict(), metadata_path)

        # Update registry index
        self._update_registry_index(model_id, metadata, None)

        self.logger.info(f"Updated {model_id} status: {old_status.value} -> {status.value}")

    def add_tags(self, model_id: str, tags: list[str]):
        """Add tags to a model."""
        metadata = self.get_metadata(model_id)
        if not metadata:
            raise ValueError(f"Model not found: {model_id}")

        # Add new tags (avoid duplicates)
        for tag in tags:
            if tag not in metadata.tags:
                metadata.tags.append(tag)

        # Save updated metadata
        metadata_path = self.metadata_dir / f"{model_id}_metadata.json"
        atomic_write_json(metadata.to_dict(), metadata_path)

        self.logger.info(f"Added tags to {model_id}: {tags}")

    def remove_tags(self, model_id: str, tags: list[str]):
        """Remove tags from a model."""
        metadata = self.get_metadata(model_id)
        if not metadata:
            raise ValueError(f"Model not found: {model_id}")

        # Remove tags
        for tag in tags:
            if tag in metadata.tags:
                metadata.tags.remove(tag)

        # Save updated metadata
        metadata_path = self.metadata_dir / f"{model_id}_metadata.json"
        atomic_write_json(metadata.to_dict(), metadata_path)

        self.logger.info(f"Removed tags from {model_id}: {tags}")

    def delete_model(self, model_id: str, remove_artifacts: bool = True):
        """
        Delete a model from the registry.

        Args:
            model_id: Model identifier
            remove_artifacts: Whether to remove artifact files
        """
        with self.logger.stage_context(f"deleting_model_{model_id}"):
            # Remove artifacts if requested
            if remove_artifacts:
                artifacts = self.get_artifacts(model_id)
                if artifacts:
                    for artifact_path in artifacts.to_dict().values():
                        if artifact_path and Path(artifact_path).exists():
                            try:
                                Path(artifact_path).unlink()
                            except Exception as e:
                                self.logger.warning(
                                    f"Could not remove artifact {artifact_path}: {e}"
                                )

            # Remove model directory
            model_dir = self.models_dir / model_id
            if model_dir.exists():
                shutil.rmtree(model_dir)

            # Remove metadata files
            metadata_path = self.metadata_dir / f"{model_id}_metadata.json"
            if metadata_path.exists():
                metadata_path.unlink()

            artifacts_path = self.metadata_dir / f"{model_id}_artifacts.json"
            if artifacts_path.exists():
                artifacts_path.unlink()

            # Update registry index
            self._remove_from_registry_index(model_id)

            self.logger.info(f"Deleted model: {model_id}")

    def get_best_model(
        self,
        model_type: str | None = None,
        metric: str = "validation_roc_auc",
        status: ModelStatus | None = None,
    ) -> TrainingMetadata | None:
        """
        Get the best model based on a metric.

        Args:
            model_type: Filter by model type
            metric: Metric to optimize
            status: Filter by status

        Returns:
            TrainingMetadata of best model or None
        """
        models = self.list_models(model_type=model_type, status=status)

        if not models:
            return None

        # Find model with best metric
        best_model = None
        best_score = float("-inf")

        for model in models:
            score = None

            # Try to get score from different metric sources
            if metric.startswith("validation_"):
                score = model.validation_metrics.get(metric.replace("validation_", ""))
            elif metric.startswith("test_"):
                score = model.test_metrics.get(metric.replace("test_", ""))
            elif metric.startswith("train_"):
                score = model.train_metrics.get(metric.replace("train_", ""))
            else:
                # Try all metric sources
                score = (
                    model.validation_metrics.get(metric)
                    or model.test_metrics.get(metric)
                    or model.train_metrics.get(metric)
                )

            if score is not None and score > best_score:
                best_score = score
                best_model = model

        return best_model

    def export_registry(self, export_path: Path):
        """Export registry to a backup file."""
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "registry_path": str(self.registry_path),
            "models": [],
        }

        for model_id in self._get_all_model_ids():
            model_data = {
                "model_id": model_id,
                "metadata": (
                    self.get_metadata(model_id).to_dict() if self.get_metadata(model_id) else None
                ),
                "artifacts": (
                    self.get_artifacts(model_id).to_dict() if self.get_artifacts(model_id) else None
                ),
            }
            export_data["models"].append(model_data)

        atomic_write_json(export_data, export_path)
        self.logger.info(f"Registry exported to {export_path}")

    def _load_registry_index(self):
        """Load registry index from file."""
        if not self.index_file.exists():
            self._create_registry_index()
            return

        try:
            with open(self.index_file) as f:
                self.registry_index = json.load(f)
        except Exception as e:
            self.logger.error(f"Could not load registry index: {e}")
            self._create_registry_index()

    def _create_registry_index(self):
        """Create new registry index."""
        self.registry_index = {
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "models": {},
        }
        self._save_registry_index()

    def _update_registry_index(
        self, model_id: str, metadata: TrainingMetadata, artifacts: ModelArtifacts | None
    ):
        """Update registry index with model information."""
        self.registry_index["models"][model_id] = {
            "model_name": metadata.model_name,
            "model_type": metadata.model_type,
            "model_version": metadata.model_version,
            "status": metadata.status.value,
            "training_start_time": metadata.training_start_time,
            "last_updated": datetime.utcnow().isoformat(),
        }

        self.registry_index["last_updated"] = datetime.utcnow().isoformat()
        self._save_registry_index()

    def _remove_from_registry_index(self, model_id: str):
        """Remove model from registry index."""
        if model_id in self.registry_index["models"]:
            del self.registry_index["models"][model_id]
            self.registry_index["last_updated"] = datetime.utcnow().isoformat()
            self._save_registry_index()

    def _save_registry_index(self):
        """Save registry index to file."""
        atomic_write_json(self.registry_index, self.index_file)

    def _get_all_model_ids(self) -> list[str]:
        """Get all model IDs in the registry."""
        model_ids = []

        for metadata_file in self.metadata_dir.glob("*_metadata.json"):
            model_id = metadata_file.stem.replace("_metadata", "")
            model_ids.append(model_id)

        return model_ids


def generate_model_id(model_name: str, timestamp: datetime | None = None) -> str:
    """
    Generate a unique model ID.

    Args:
        model_name: Base name of the model
        timestamp: Optional timestamp (current time if None)

    Returns:
        Unique model ID
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    return f"{model_name}_{timestamp_str}"
