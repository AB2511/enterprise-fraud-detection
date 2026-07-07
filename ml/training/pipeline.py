"""
Training Pipeline

Complete end-to-end training pipeline orchestrating data loading,
feature preparation, model training, evaluation, and artifact management.
"""

import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ml.features import LocalFeatureStore
from ml.training.base import TrainingConfig, TrainingResult
from ml.training.evaluation import ModelEvaluator
from ml.training.optimization import OptimizationConfig, ThresholdOptimizer
from ml.training.registry import (
    ModelArtifacts,
    ModelRegistry,
    ModelStatus,
    TrainingMetadata,
    generate_model_id,
)
from ml.training.tracking import ExperimentTracker, create_tracker
from ml.utils.file_manager import atomic_write_json
from ml.utils.logging_config import get_logger


@dataclass
class PipelineConfig:
    """Configuration for the training pipeline."""

    # Pipeline identification
    pipeline_name: str = "fraud_detection_training"
    pipeline_version: str = "1.0.0"

    # Data configuration
    dataset_path: Path | None = None
    feature_store_path: Path | None = None
    feature_set_name: str | None = None
    feature_set_version: str | None = None

    # Model configuration
    trainer_configs: list[TrainingConfig] = field(default_factory=list)

    # Experiment tracking
    experiment_tracker_type: str = "auto"  # "mlflow", "local", "auto"
    experiment_name: str = "fraud_detection"
    tracking_uri: str | None = None

    # Registry configuration
    registry_path: Path = Path("models/registry")

    # Evaluation configuration
    generate_evaluation_reports: bool = True
    evaluation_output_dir: Path = Path("evaluation_reports")

    # Threshold optimization
    optimize_thresholds: bool = True
    threshold_optimization_configs: list[OptimizationConfig] = field(default_factory=list)

    # Artifact management
    artifacts_base_dir: Path = Path("artifacts")
    save_predictions: bool = True
    save_plots: bool = True
    save_models: bool = True

    # Reproducibility
    random_seed: int = 42
    capture_environment: bool = True

    def __post_init__(self):
        # Ensure paths are Path objects
        self.dataset_path = Path(self.dataset_path) if self.dataset_path else None
        self.feature_store_path = Path(self.feature_store_path) if self.feature_store_path else None
        self.registry_path = Path(self.registry_path)
        self.evaluation_output_dir = Path(self.evaluation_output_dir)
        self.artifacts_base_dir = Path(self.artifacts_base_dir)

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "PipelineConfig":
        """Load pipeline configuration from YAML file."""
        with open(yaml_path) as f:
            config_dict = yaml.safe_load(f)

        return cls(**config_dict)

    def save_yaml(self, yaml_path: str | Path):
        """Save configuration to YAML file."""
        # Convert to serializable dict
        config_dict = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                config_dict[key] = str(value)
            elif isinstance(value, list) and value and hasattr(value[0], "to_dict"):
                config_dict[key] = [item.to_dict() for item in value]
            else:
                config_dict[key] = value

        with open(yaml_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)


class TrainingPipeline:
    """
    Complete training pipeline for fraud detection models.

    Orchestrates:
    - Data loading and preparation
    - Feature engineering integration
    - Model training with multiple trainers
    - Evaluation and reporting
    - Threshold optimization
    - Model registry management
    - Artifact management
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = get_logger("ml.training.TrainingPipeline")

        # Initialize components
        self.experiment_tracker = self._create_experiment_tracker()
        self.model_registry = ModelRegistry(self.config.registry_path)
        self.evaluator = ModelEvaluator()
        self.threshold_optimizer = ThresholdOptimizer()
        self.feature_store = None

        # Pipeline state
        self.pipeline_id = str(uuid.uuid4())
        self.start_time = None
        self.end_time = None
        self.results = {}

    def _create_experiment_tracker(self) -> ExperimentTracker:
        """Create experiment tracker based on configuration."""
        return create_tracker(
            experiment_name=self.config.experiment_name,
            tracker_type=self.config.experiment_tracker_type,
            tracking_uri=self.config.tracking_uri,
        )

    def _setup_feature_store(self):
        """Setup feature store if configured."""
        if self.config.feature_store_path:
            self.feature_store = LocalFeatureStore(self.config.feature_store_path)
            self.logger.info(f"Initialized feature store at {self.config.feature_store_path}")

    def load_data(self) -> pd.DataFrame:
        """Load training data from configured source."""

        if self.config.dataset_path:
            # Load from file
            self.logger.info(f"Loading data from {self.config.dataset_path}")

            if self.config.dataset_path.suffix.lower() == ".csv":
                data = pd.read_csv(self.config.dataset_path)
            elif self.config.dataset_path.suffix.lower() == ".parquet":
                data = pd.read_parquet(self.config.dataset_path)
            elif self.config.dataset_path.suffix.lower() == ".json":
                data = pd.read_json(self.config.dataset_path)
            else:
                raise ValueError(f"Unsupported file format: {self.config.dataset_path.suffix}")

        elif self.config.feature_store_path and self.config.feature_set_name:
            # Load from feature store
            self._setup_feature_store()

            self.logger.info(f"Loading features from feature store: {self.config.feature_set_name}")

            data, metadata = self.feature_store.load_features(
                self.config.feature_set_name, self.config.feature_set_version
            )

            self.logger.info(f"Loaded {len(data)} samples with {len(data.columns)} features")

        else:
            raise ValueError("Either dataset_path or feature_store configuration must be provided")

        # Basic data validation
        if data.empty:
            raise ValueError("Loaded dataset is empty")

        self.logger.info(f"Data loaded successfully: {data.shape}")
        return data

    def run(self, data: pd.DataFrame | None = None) -> dict[str, TrainingResult]:
        """
        Run the complete training pipeline.

        Args:
            data: Optional data to use (will load from config if not provided)

        Returns:
            Dictionary of training results keyed by trainer name
        """
        self.start_time = datetime.utcnow()

        with self.logger.stage_context("training_pipeline"):
            try:
                # Load data if not provided
                if data is None:
                    data = self.load_data()

                # Create artifacts directory
                self.config.artifacts_base_dir.mkdir(parents=True, exist_ok=True)

                # Run training for each configured trainer
                results = {}

                for i, trainer_config in enumerate(self.config.trainer_configs):
                    trainer_name = f"{trainer_config.model_name}_{i}"

                    self.logger.info(f"Starting training for {trainer_name}")

                    try:
                        result = self._run_single_trainer(data, trainer_config, trainer_name)
                        results[trainer_name] = result

                        self.logger.info(f"Completed training for {trainer_name}")

                    except Exception as e:
                        self.logger.error(f"Training failed for {trainer_name}: {e}")
                        # Continue with other trainers
                        continue

                # Generate comparative analysis
                if len(results) > 1:
                    self._generate_comparative_analysis(results)

                self.results = results
                self.end_time = datetime.utcnow()

                # Save pipeline summary
                self._save_pipeline_summary()

                self.logger.info(
                    f"Training pipeline completed with {len(results)} successful models"
                )

                return results

            except Exception as e:
                self.end_time = datetime.utcnow()
                self.logger.error(f"Training pipeline failed: {e}")
                raise

    def _run_single_trainer(
        self, data: pd.DataFrame, trainer_config: TrainingConfig, trainer_name: str
    ) -> TrainingResult:
        """Run training for a single trainer."""

        # Import trainer classes
        from ml.training.trainers import IsolationForestTrainer, XGBoostTrainer

        # Create trainer based on configuration
        if trainer_config.model_name.lower().startswith("xgboost"):
            trainer = XGBoostTrainer(trainer_config, self.experiment_tracker)
        elif trainer_config.model_name.lower().startswith("isolation"):
            trainer = IsolationForestTrainer(trainer_config, self.experiment_tracker)
        else:
            raise ValueError(f"Unknown trainer type: {trainer_config.model_name}")

        # Train model
        result = trainer.train(data)

        # Generate model ID for registry
        model_id = generate_model_id(trainer_config.model_name)

        # Create artifacts directory for this model
        model_artifacts_dir = self.config.artifacts_base_dir / model_id
        model_artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Generate evaluation report
        artifacts = ModelArtifacts()

        if self.config.generate_evaluation_reports:
            evaluation_dir = model_artifacts_dir / "evaluation"

            # Get predictions with probabilities
            y_pred = result.test_predictions
            y_proba = None

            # Try to get probabilities
            try:
                y_proba = trainer._predict_proba(result.model, trainer.X_test)
            except Exception as e:
                self.logger.warning(f"Could not generate probabilities: {e}")

            # Generate evaluation report
            evaluation_report = self.evaluator.generate_evaluation_report(
                trainer.y_test, y_pred, y_proba, result.feature_importance, evaluation_dir, model_id
            )

            # Update artifacts
            artifacts.metrics_path = evaluation_report["artifact_paths"]["metrics"]
            artifacts.roc_curve_path = evaluation_report["artifact_paths"].get("roc_curve")
            artifacts.pr_curve_path = evaluation_report["artifact_paths"].get("pr_curve")
            artifacts.confusion_matrix_path = evaluation_report["artifact_paths"][
                "confusion_matrix"
            ]
            artifacts.calibration_curve_path = evaluation_report["artifact_paths"].get(
                "calibration_curve"
            )
            artifacts.feature_importance_plot_path = evaluation_report["artifact_paths"].get(
                "feature_importance"
            )
            artifacts.dashboard_path = evaluation_report["artifact_paths"].get("dashboard")
            artifacts.training_report_path = evaluation_report["artifact_paths"][
                "classification_report"
            ]

        # Optimize thresholds
        if self.config.optimize_thresholds and y_proba is not None:
            self._optimize_thresholds(trainer.y_test, y_proba, model_artifacts_dir, artifacts)

        # Save model
        if self.config.save_models:
            model_path = model_artifacts_dir / f"{model_id}_model.pkl"
            trainer.save_model(model_path)
            artifacts.model_path = model_path

        # Save configuration
        config_path = model_artifacts_dir / f"{model_id}_config.yaml"
        trainer_config.save_yaml(config_path)
        artifacts.config_path = config_path

        # Save predictions
        if self.config.save_predictions:
            predictions_path = model_artifacts_dir / f"{model_id}_predictions.json"
            predictions_data = {
                "train_predictions": (
                    result.train_predictions.tolist()
                    if result.train_predictions is not None
                    else None
                ),
                "validation_predictions": (
                    result.validation_predictions.tolist()
                    if result.validation_predictions is not None
                    else None
                ),
                "test_predictions": (
                    result.test_predictions.tolist()
                    if result.test_predictions is not None
                    else None
                ),
                "test_probabilities": y_proba.tolist() if y_proba is not None else None,
            }
            atomic_write_json(predictions_data, predictions_path)
            artifacts.predictions_path = predictions_path

        # Create training metadata
        metadata = self._create_training_metadata(model_id, result, trainer_config, data, artifacts)

        # Register model
        self.model_registry.register_model(
            result.model if self.config.save_models else None,
            metadata,
            artifacts,
            save_model=False,  # Already saved above
        )

        # Update result with model ID
        result.run_id = model_id
        result.artifact_paths = artifacts.to_dict()

        return result

    def _optimize_thresholds(
        self, y_true: np.ndarray, y_proba: np.ndarray, output_dir: Path, artifacts: ModelArtifacts
    ):
        """Optimize classification thresholds."""

        threshold_dir = output_dir / "threshold_optimization"
        threshold_dir.mkdir(parents=True, exist_ok=True)

        # Use configured optimization or default ones
        optimization_configs = self.config.threshold_optimization_configs
        if not optimization_configs:
            from ml.training.optimization import (
                create_business_cost_optimizer,
                create_f1_optimizer,
                create_recall_optimizer,
            )

            optimization_configs = [
                create_business_cost_optimizer(),
                create_f1_optimizer(),
                create_recall_optimizer(min_precision=0.1),
            ]

        threshold_results = {}

        for opt_config in optimization_configs:
            try:
                # Set plot saving
                opt_config.save_plots = True

                result = self.threshold_optimizer.optimize_threshold(y_true, y_proba, opt_config)

                # Save result
                result_path = threshold_dir / f"threshold_opt_{opt_config.objective.value}.json"
                atomic_write_json(result.to_dict(), result_path)

                threshold_results[opt_config.objective.value] = result

                self.logger.info(
                    f"Threshold optimization ({opt_config.objective.value}): {result.optimal_threshold:.4f}"
                )

            except Exception as e:
                self.logger.warning(
                    f"Threshold optimization failed for {opt_config.objective.value}: {e}"
                )

        # Save summary
        if threshold_results:
            summary_path = threshold_dir / "threshold_summary.json"
            summary = {
                objective: {
                    "optimal_threshold": result.optimal_threshold,
                    "objective_value": result.objective_value,
                    "precision": result.metrics_at_optimal["precision"],
                    "recall": result.metrics_at_optimal["recall"],
                    "f1_score": result.metrics_at_optimal["f1_score"],
                }
                for objective, result in threshold_results.items()
            }
            atomic_write_json(summary, summary_path)

    def _create_training_metadata(
        self,
        model_id: str,
        result: TrainingResult,
        config: TrainingConfig,
        data: pd.DataFrame,
        artifacts: ModelArtifacts,
    ) -> TrainingMetadata:
        """Create comprehensive training metadata."""

        # Capture environment information
        environment_info = {}
        if self.config.capture_environment:
            environment_info = {
                "python_version": sys.version,
                "pandas_version": pd.__version__,
                "numpy_version": np.__version__,
            }

            # Try to get additional framework versions
            try:
                import xgboost

                environment_info["xgboost_version"] = xgboost.__version__
            except ImportError:
                pass

            try:
                import sklearn

                environment_info["sklearn_version"] = sklearn.__version__
            except ImportError:
                pass

        # Try to get git commit
        git_commit = None
        if self.config.capture_environment:
            try:
                import subprocess

                git_commit = (
                    subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
                    .decode()
                    .strip()
                )
            except:
                pass

        return TrainingMetadata(
            model_id=model_id,
            model_name=config.model_name,
            model_version=config.model_version,
            model_type=config.model_name,
            training_start_time=(
                result.config.get("training_start_time")
                if hasattr(result, "config") and result.config
                else (
                    self.start_time.isoformat()
                    if self.start_time
                    else datetime.utcnow().isoformat()
                )
            ),
            training_end_time=datetime.utcnow().isoformat(),
            training_duration_seconds=result.training_time,
            dataset_name="fraud_detection_dataset",
            n_training_samples=len(data) if data is not None else None,
            n_features=len(result.feature_names),
            train_metrics=result.train_metrics,
            validation_metrics=result.validation_metrics,
            test_metrics=result.test_metrics,
            cv_metrics=result.cv_metrics,
            hyperparameters=config.to_dict(),
            training_config=config.to_dict(),
            python_version=environment_info.get("python_version"),
            framework_versions=environment_info,
            git_commit=git_commit,
            experiment_id=(
                self.experiment_tracker.experiment_id
                if hasattr(self.experiment_tracker, "experiment_id")
                else None
            ),
            run_id=result.run_id,
            created_by=os.getenv("USER", "unknown"),
            status=ModelStatus.COMPLETED,
            tags=["fraud_detection", config.model_name],
            notes=f"Trained via TrainingPipeline {self.pipeline_id}",
        )

    def _generate_comparative_analysis(self, results: dict[str, TrainingResult]):
        """Generate comparative analysis of multiple models."""

        comparison_dir = self.config.artifacts_base_dir / "model_comparison"
        comparison_dir.mkdir(parents=True, exist_ok=True)

        # Create comparison metrics table
        comparison_data = []

        for trainer_name, result in results.items():
            row = {
                "model_name": trainer_name,
                "model_type": result.model_name,
                "training_time": result.training_time,
                "n_features": len(result.feature_names),
            }

            # Add metrics
            row.update({f"train_{k}": v for k, v in result.train_metrics.items()})
            row.update({f"val_{k}": v for k, v in result.validation_metrics.items()})
            row.update({f"test_{k}": v for k, v in result.test_metrics.items()})

            if result.cv_metrics:
                row.update({f"cv_{k}": v for k, v in result.cv_metrics.items()})

            comparison_data.append(row)

        # Save comparison table
        comparison_df = pd.DataFrame(comparison_data)
        comparison_path = comparison_dir / "model_comparison.csv"
        comparison_df.to_csv(comparison_path, index=False)

        # Generate comparison visualizations
        try:
            self._plot_model_comparison(comparison_df, comparison_dir)
        except Exception as e:
            self.logger.warning(f"Could not generate comparison plots: {e}")

        self.logger.info(f"Model comparison saved to {comparison_dir}")

    def _plot_model_comparison(self, comparison_df: pd.DataFrame, output_dir: Path):
        """Generate comparison visualizations."""

        try:
            import matplotlib.pyplot as plt
            import seaborn as sns

            # Key metrics to compare
            metrics = [
                "test_roc_auc",
                "test_pr_auc",
                "test_f1_score",
                "test_precision",
                "test_recall",
            ]
            available_metrics = [m for m in metrics if m in comparison_df.columns]

            if not available_metrics:
                return

            # Create comparison plot
            fig, axes = plt.subplots(2, 3, figsize=(18, 12))
            axes = axes.ravel()

            for i, metric in enumerate(available_metrics):
                if i >= len(axes):
                    break

                ax = axes[i]
                comparison_df.plot(x="model_name", y=metric, kind="bar", ax=ax, legend=False)
                ax.set_title(metric.replace("_", " ").title())
                ax.set_xlabel("Model")
                ax.set_ylabel("Score")
                ax.tick_params(axis="x", rotation=45)

            # Training time comparison
            if "training_time" in comparison_df.columns and len(available_metrics) < len(axes):
                ax = axes[len(available_metrics)]
                comparison_df.plot(
                    x="model_name",
                    y="training_time",
                    kind="bar",
                    ax=ax,
                    legend=False,
                    color="orange",
                )
                ax.set_title("Training Time")
                ax.set_xlabel("Model")
                ax.set_ylabel("Seconds")
                ax.tick_params(axis="x", rotation=45)

            plt.tight_layout()

            plot_path = output_dir / "model_comparison.png"
            fig.savefig(plot_path, dpi=300, bbox_inches="tight")
            plt.close()

            self.logger.info(f"Comparison plot saved to {plot_path}")

        except ImportError:
            self.logger.warning("matplotlib/seaborn not available for plotting")

    def _save_pipeline_summary(self):
        """Save pipeline execution summary."""

        summary = {
            "pipeline_id": self.pipeline_id,
            "pipeline_name": self.config.pipeline_name,
            "pipeline_version": self.config.pipeline_version,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.start_time and self.end_time
                else None
            ),
            "models_trained": len(self.results),
            "successful_models": [
                name for name, result in self.results.items() if result is not None
            ],
            "configuration": {
                "experiment_tracker_type": self.config.experiment_tracker_type,
                "registry_path": str(self.config.registry_path),
                "artifacts_base_dir": str(self.config.artifacts_base_dir),
                "random_seed": self.config.random_seed,
            },
        }

        summary_path = self.config.artifacts_base_dir / "pipeline_summary.json"
        atomic_write_json(summary, summary_path)

        self.logger.info(f"Pipeline summary saved to {summary_path}")


class ExperimentRunner:
    """
    High-level experiment runner for running multiple training experiments.

    Supports:
    - Hyperparameter sweeps
    - Cross-validation experiments
    - Model comparison studies
    - Automated experiment tracking
    """

    def __init__(self, base_config: PipelineConfig):
        self.base_config = base_config
        self.logger = get_logger("ml.training.ExperimentRunner")

        self.experiments = []
        self.results = {}

    def add_experiment(
        self, experiment_name: str, trainer_configs: list[TrainingConfig], **config_overrides
    ):
        """Add an experiment to the runner."""

        # Create experiment-specific config
        base_dict = self.base_config.__dict__.copy()
        base_dict.update(config_overrides)
        base_dict["pipeline_name"] = f"{self.base_config.pipeline_name}_{experiment_name}"

        experiment_config = PipelineConfig(**base_dict)
        experiment_config.trainer_configs = trainer_configs

        self.experiments.append({"name": experiment_name, "config": experiment_config})

        self.logger.info(f"Added experiment: {experiment_name}")

    def run_all_experiments(
        self, data: pd.DataFrame | None = None
    ) -> dict[str, dict[str, TrainingResult]]:
        """Run all configured experiments."""

        self.logger.info(f"Starting {len(self.experiments)} experiments")

        all_results = {}

        for experiment in self.experiments:
            experiment_name = experiment["name"]
            experiment_config = experiment["config"]

            self.logger.info(f"Running experiment: {experiment_name}")

            try:
                # Create experiment-specific pipeline
                pipeline = TrainingPipeline(experiment_config)

                # Run experiment
                results = pipeline.run(data)
                all_results[experiment_name] = results

                self.logger.info(f"Completed experiment: {experiment_name}")

            except Exception as e:
                self.logger.error(f"Experiment {experiment_name} failed: {e}")
                all_results[experiment_name] = {}

        self.results = all_results

        # Generate cross-experiment analysis
        self._generate_cross_experiment_analysis()

        return all_results

    def _generate_cross_experiment_analysis(self):
        """Generate analysis across all experiments."""

        if not self.results:
            return

        # Collect all results
        all_model_results = []

        for exp_name, exp_results in self.results.items():
            for model_name, model_result in exp_results.items():
                result_record = {
                    "experiment": exp_name,
                    "model": model_name,
                    "model_type": model_result.model_name,
                    "training_time": model_result.training_time,
                }

                # Add metrics - check if they're real dictionaries (not Mock objects)
                if hasattr(model_result.train_metrics, "items") and not hasattr(
                    model_result.train_metrics, "_mock_name"
                ):
                    try:
                        result_record.update(
                            {f"train_{k}": v for k, v in model_result.train_metrics.items()}
                        )
                    except (TypeError, AttributeError):
                        # Skip if metrics can't be iterated
                        pass

                if hasattr(model_result.validation_metrics, "items") and not hasattr(
                    model_result.validation_metrics, "_mock_name"
                ):
                    try:
                        result_record.update(
                            {f"val_{k}": v for k, v in model_result.validation_metrics.items()}
                        )
                    except (TypeError, AttributeError):
                        # Skip if metrics can't be iterated
                        pass

                if hasattr(model_result.test_metrics, "items") and not hasattr(
                    model_result.test_metrics, "_mock_name"
                ):
                    try:
                        result_record.update(
                            {f"test_{k}": v for k, v in model_result.test_metrics.items()}
                        )
                    except (TypeError, AttributeError):
                        # Skip if metrics can't be iterated
                        pass

                all_model_results.append(result_record)

        # Save cross-experiment results
        results_df = pd.DataFrame(all_model_results)

        output_dir = self.base_config.artifacts_base_dir / "cross_experiment_analysis"
        output_dir.mkdir(parents=True, exist_ok=True)

        results_path = output_dir / "all_experiments_results.csv"
        results_df.to_csv(results_path, index=False)

        self.logger.info(f"Cross-experiment analysis saved to {output_dir}")
