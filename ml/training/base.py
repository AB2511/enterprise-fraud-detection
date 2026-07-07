"""
Base Training Framework

Abstract base classes and configurations for model training.
Provides a consistent interface for all model trainers.
"""

import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split

from ml.training.tracking import ExperimentTracker
from ml.utils.logging_config import get_logger


@dataclass
class TrainingConfig:
    """Base configuration for model training."""

    # Model configuration
    model_name: str
    model_version: str = "1.0.0"

    # Data configuration
    target_column: str = "is_fraud"
    feature_columns: list[str] | None = None

    # Training configuration
    test_size: float = 0.2
    validation_size: float = 0.15
    random_seed: int = 42
    stratify: bool = True

    # Cross-validation
    use_cross_validation: bool = True
    cv_folds: int = 5
    cv_scoring: str = "roc_auc"

    # Early stopping
    early_stopping: bool = False
    patience: int = 10
    min_delta: float = 0.001

    # Artifact management
    save_model: bool = True
    save_predictions: bool = True
    save_feature_importance: bool = True
    save_plots: bool = True

    # Reproducibility
    capture_git_hash: bool = True
    capture_environment: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                result[key] = str(value)
            else:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "TrainingConfig":
        """Create config from dictionary."""
        return cls(**config_dict)

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "TrainingConfig":
        """Load configuration from YAML file."""
        import yaml

        with open(yaml_path) as f:
            config_dict = yaml.safe_load(f)

        return cls.from_dict(config_dict)


@dataclass
class TrainingResult:
    """Results from model training."""

    # Training metadata
    run_id: str
    model_name: str
    model_version: str
    training_time: float

    # Model artifacts
    model: Any
    model_path: Path | None = None

    # Performance metrics
    train_metrics: dict[str, float] = field(default_factory=dict)
    validation_metrics: dict[str, float] = field(default_factory=dict)
    test_metrics: dict[str, float] = field(default_factory=dict)
    cv_metrics: dict[str, float] | None = None

    # Feature information
    feature_names: list[str] = field(default_factory=list)
    feature_importance: dict[str, float] | None = None

    # Predictions
    train_predictions: np.ndarray | None = None
    validation_predictions: np.ndarray | None = None
    test_predictions: np.ndarray | None = None

    # Configuration
    config: dict[str, Any] | None = None

    # Artifacts
    artifact_paths: dict[str, Path] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary (excluding large objects)."""
        return {
            "run_id": self.run_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "training_time": self.training_time,
            "train_metrics": self.train_metrics,
            "validation_metrics": self.validation_metrics,
            "test_metrics": self.test_metrics,
            "cv_metrics": self.cv_metrics,
            "feature_names": self.feature_names,
            "feature_importance": self.feature_importance,
            "config": self.config,
            "artifact_paths": {k: str(v) for k, v in self.artifact_paths.items()},
        }


class BaseTrainer(ABC):
    """
    Abstract base class for model trainers.

    Provides common functionality for:
    - Data loading and splitting
    - Cross-validation
    - Model persistence
    - Experiment tracking
    - Artifact management
    """

    def __init__(self, config: TrainingConfig, experiment_tracker: ExperimentTracker | None = None):
        self.config = config
        self.tracker = experiment_tracker
        self.logger = get_logger(f"ml.training.{self.__class__.__name__}")

        # Training state
        self.model = None
        self.is_trained = False
        self.feature_names = []
        self.run_id = None

        # Data splits
        self.X_train = None
        self.X_val = None
        self.X_test = None
        self.y_train = None
        self.y_val = None
        self.y_test = None

    @abstractmethod
    def _create_model(self) -> Any:
        """Create and return the model instance."""
        pass

    @abstractmethod
    def _fit_model(self, X: pd.DataFrame, y: pd.Series) -> Any:
        """Fit the model and return the trained instance."""
        pass

    @abstractmethod
    def _predict(self, model: Any, X: pd.DataFrame) -> np.ndarray:
        """Generate predictions using the trained model."""
        pass

    @abstractmethod
    def _predict_proba(self, model: Any, X: pd.DataFrame) -> np.ndarray:
        """Generate prediction probabilities (if supported)."""
        pass

    @abstractmethod
    def _get_feature_importance(self, model: Any) -> dict[str, float] | None:
        """Extract feature importance from the model (if supported)."""
        pass

    def prepare_data(
        self,
        data: pd.DataFrame,
        target_column: str | None = None,
        feature_columns: list[str] | None = None,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """
        Prepare training data by separating features and target.

        Args:
            data: Input DataFrame
            target_column: Name of target column
            feature_columns: List of feature column names

        Returns:
            Tuple of (features, target)
        """
        target_column = target_column or self.config.target_column
        feature_columns = feature_columns or self.config.feature_columns

        if target_column not in data.columns:
            raise ValueError(f"Target column '{target_column}' not found in data")

        # Extract target
        y = data[target_column]

        # Extract features
        if feature_columns is None:
            # Use all columns except target
            X = data.drop(columns=[target_column])
        else:
            missing_features = set(feature_columns) - set(data.columns)
            if missing_features:
                raise ValueError(f"Feature columns not found: {missing_features}")
            X = data[feature_columns]

        self.feature_names = list(X.columns)

        self.logger.info(f"Prepared data: {len(X)} samples, {len(X.columns)} features")
        self.logger.info(f"Target distribution: {y.value_counts().to_dict()}")

        return X, y

    def split_data(
        self, X: pd.DataFrame, y: pd.Series
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        """
        Split data into train, validation, and test sets.

        Args:
            X: Features DataFrame
            y: Target Series

        Returns:
            Tuple of (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        # First split: train+val vs test
        X_temp, X_test, y_temp, y_test = train_test_split(
            X,
            y,
            test_size=self.config.test_size,
            random_state=self.config.random_seed,
            stratify=y if self.config.stratify else None,
        )

        # Second split: train vs validation
        val_size_adjusted = self.config.validation_size / (1 - self.config.test_size)

        X_train, X_val, y_train, y_val = train_test_split(
            X_temp,
            y_temp,
            test_size=val_size_adjusted,
            random_state=self.config.random_seed,
            stratify=y_temp if self.config.stratify else None,
        )

        self.logger.info(
            f"Data split - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}"
        )
        self.logger.info(f"Train fraud rate: {y_train.mean():.4f}")
        self.logger.info(f"Val fraud rate: {y_val.mean():.4f}")
        self.logger.info(f"Test fraud rate: {y_test.mean():.4f}")

        return X_train, X_val, X_test, y_train, y_val, y_test

    def cross_validate(self, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
        """
        Perform cross-validation on the training data.

        Args:
            X: Training features
            y: Training target

        Returns:
            Dictionary of cross-validation metrics
        """
        from sklearn.model_selection import cross_val_score

        if not self.config.use_cross_validation:
            return {}

        self.logger.info(f"Starting {self.config.cv_folds}-fold cross-validation")

        # Create stratified k-fold
        cv = StratifiedKFold(
            n_splits=self.config.cv_folds, shuffle=True, random_state=self.config.random_seed
        )

        # Create a fresh model for CV
        cv_model = self._create_model()

        # Perform cross-validation
        scores = cross_val_score(cv_model, X, y, cv=cv, scoring=self.config.cv_scoring, n_jobs=-1)

        cv_metrics = {
            f"cv_{self.config.cv_scoring}_mean": scores.mean(),
            f"cv_{self.config.cv_scoring}_std": scores.std(),
            f"cv_{self.config.cv_scoring}_min": scores.min(),
            f"cv_{self.config.cv_scoring}_max": scores.max(),
        }

        self.logger.info(f"CV {self.config.cv_scoring}: {scores.mean():.4f} ± {scores.std():.4f}")

        return cv_metrics

    def train(
        self,
        data: pd.DataFrame,
        target_column: str | None = None,
        feature_columns: list[str] | None = None,
    ) -> TrainingResult:
        """
        Complete training pipeline.

        Args:
            data: Training data DataFrame
            target_column: Name of target column
            feature_columns: List of feature column names

        Returns:
            TrainingResult with metrics and artifacts
        """
        start_time = datetime.now()

        # Start experiment tracking
        if self.tracker:
            self.run_id = self.tracker.start_run(
                run_name=f"{self.config.model_name}_{start_time.strftime('%Y%m%d_%H%M%S')}"
            )

            # Log configuration
            self.tracker.log_params(self.run_id, self.config.to_dict())
            self.tracker.set_tags(
                self.run_id,
                {
                    "model_type": self.config.model_name,
                    "framework": self.__class__.__name__,
                    "timestamp": start_time.isoformat(),
                },
            )

        try:
            with self.logger.stage_context("training_pipeline"):
                # Prepare data
                X, y = self.prepare_data(data, target_column, feature_columns)

                # Split data
                self.X_train, self.X_val, self.X_test, self.y_train, self.y_val, self.y_test = (
                    self.split_data(X, y)
                )

                # Cross-validation
                cv_metrics = (
                    self.cross_validate(self.X_train, self.y_train)
                    if self.config.use_cross_validation
                    else {}
                )

                # Train model
                self.logger.info("Training model...")
                self.model = self._fit_model(self.X_train, self.y_train)
                self.is_trained = True

                # Generate predictions
                train_predictions = self._predict(self.model, self.X_train)
                val_predictions = self._predict(self.model, self.X_val)
                test_predictions = self._predict(self.model, self.X_test)

                # Compute metrics
                from ml.training.evaluation import ModelEvaluator

                evaluator = ModelEvaluator()

                train_metrics = evaluator.compute_classification_metrics(
                    self.y_train, train_predictions
                )
                val_metrics = evaluator.compute_classification_metrics(self.y_val, val_predictions)
                test_metrics = evaluator.compute_classification_metrics(
                    self.y_test, test_predictions
                )

                # Get feature importance
                feature_importance = self._get_feature_importance(self.model)

                # Calculate training time
                training_time = (datetime.now() - start_time).total_seconds()

                # Create result
                result = TrainingResult(
                    run_id=self.run_id or "local",
                    model_name=self.config.model_name,
                    model_version=self.config.model_version,
                    training_time=training_time,
                    model=self.model,
                    train_metrics=train_metrics,
                    validation_metrics=val_metrics,
                    test_metrics=test_metrics,
                    cv_metrics=cv_metrics,
                    feature_names=self.feature_names,
                    feature_importance=feature_importance,
                    train_predictions=train_predictions,
                    validation_predictions=val_predictions,
                    test_predictions=test_predictions,
                    config=self.config.to_dict(),
                )

                # Log metrics to tracker
                if self.tracker:
                    all_metrics = {}
                    all_metrics.update({f"train_{k}": v for k, v in train_metrics.items()})
                    all_metrics.update({f"val_{k}": v for k, v in val_metrics.items()})
                    all_metrics.update({f"test_{k}": v for k, v in test_metrics.items()})
                    all_metrics.update(cv_metrics)
                    all_metrics["training_time"] = training_time

                    self.tracker.log_metrics(self.run_id, all_metrics)

                self.logger.info(f"Training completed in {training_time:.2f} seconds")

                # Log validation metrics safely (handle Mock objects in tests)
                try:
                    val_roc_auc = val_metrics.get("roc_auc", "N/A")
                    if isinstance(val_roc_auc, (int, float)):
                        self.logger.info(f"Validation ROC-AUC: {val_roc_auc:.4f}")
                    else:
                        self.logger.info(f"Validation ROC-AUC: {val_roc_auc}")
                except (TypeError, AttributeError):
                    # Handle case where val_metrics is a Mock object
                    self.logger.info("Validation metrics computed")

                return result

        except Exception as e:
            self.logger.error(f"Training failed: {e}")
            if self.tracker and self.run_id:
                self.tracker.end_run(self.run_id, status="FAILED")
            raise

        finally:
            if self.tracker and self.run_id:
                self.tracker.end_run(self.run_id, status="FINISHED")

    def save_model(self, model_path: Path, format: str = "pickle") -> Path:
        """
        Save trained model to disk.

        Args:
            model_path: Path to save model
            format: Format to save ("pickle", "joblib")

        Returns:
            Path where model was saved
        """
        if not self.is_trained or self.model is None:
            raise ValueError("Model must be trained before saving")

        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "pickle":
            with open(model_path, "wb") as f:
                pickle.dump(self.model, f)
        elif format == "joblib":
            joblib.dump(self.model, model_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

        self.logger.info(f"Model saved to {model_path}")

        return model_path

    def load_model(self, model_path: Path, format: str = "pickle") -> Any:
        """
        Load trained model from disk.

        Args:
            model_path: Path to load model from
            format: Format to load ("pickle", "joblib")

        Returns:
            Loaded model
        """
        model_path = Path(model_path)

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        if format == "pickle":
            with open(model_path, "rb") as f:
                model = pickle.load(f)
        elif format == "joblib":
            model = joblib.load(model_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

        self.model = model
        self.is_trained = True

        self.logger.info(f"Model loaded from {model_path}")

        return model
