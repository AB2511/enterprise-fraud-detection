"""
Experiment Tracking

Abstract experiment tracking interface with MLflow and local implementations.
Designed to support both local development and production MLflow tracking.
"""

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ml.utils.logging_config import get_logger


@dataclass
class ExperimentRun:
    """Represents a single experiment run."""

    run_id: str
    experiment_id: str
    run_name: str | None = None
    status: str = "RUNNING"
    start_time: datetime | None = None
    end_time: datetime | None = None
    metrics: dict[str, float] = None
    params: dict[str, Any] = None
    tags: dict[str, str] = None
    artifacts: list[str] = None

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
        if self.params is None:
            self.params = {}
        if self.tags is None:
            self.tags = {}
        if self.artifacts is None:
            self.artifacts = []
        if self.start_time is None:
            self.start_time = datetime.utcnow()


class ExperimentTracker(ABC):
    """
    Abstract base class for experiment tracking.

    Provides a common interface that can be implemented by different
    tracking backends (MLflow, local JSON, etc.).
    """

    def __init__(self, experiment_name: str):
        self.experiment_name = experiment_name
        self.logger = get_logger(f"ml.training.{self.__class__.__name__}")

    @abstractmethod
    def create_experiment(self, experiment_name: str) -> str:
        """Create a new experiment and return its ID."""
        pass

    @abstractmethod
    def start_run(self, run_name: str | None = None, **kwargs) -> str:
        """Start a new run and return its ID."""
        pass

    @abstractmethod
    def end_run(self, run_id: str, status: str = "FINISHED"):
        """End a run with the given status."""
        pass

    @abstractmethod
    def log_param(self, run_id: str, key: str, value: Any):
        """Log a parameter for the run."""
        pass

    @abstractmethod
    def log_params(self, run_id: str, params: dict[str, Any]):
        """Log multiple parameters for the run."""
        pass

    @abstractmethod
    def log_metric(self, run_id: str, key: str, value: float, step: int | None = None):
        """Log a metric for the run."""
        pass

    @abstractmethod
    def log_metrics(self, run_id: str, metrics: dict[str, float], step: int | None = None):
        """Log multiple metrics for the run."""
        pass

    @abstractmethod
    def log_artifact(
        self, run_id: str, artifact_path: str | Path, artifact_name: str | None = None
    ):
        """Log an artifact (file) for the run."""
        pass

    @abstractmethod
    def set_tag(self, run_id: str, key: str, value: str):
        """Set a tag for the run."""
        pass

    @abstractmethod
    def set_tags(self, run_id: str, tags: dict[str, str]):
        """Set multiple tags for the run."""
        pass

    @abstractmethod
    def get_run(self, run_id: str) -> ExperimentRun | None:
        """Get run information by ID."""
        pass

    @abstractmethod
    def list_runs(self, experiment_id: str | None = None) -> list[ExperimentRun]:
        """List all runs for an experiment."""
        pass


class LocalTracker(ExperimentTracker):
    """
    Local JSON-based experiment tracker.

    Stores experiment data in local JSON files for development
    and environments where MLflow is not available.
    """

    def __init__(self, experiment_name: str, tracking_dir: Path = Path("experiments")):
        super().__init__(experiment_name)
        self.tracking_dir = Path(tracking_dir)
        self.tracking_dir.mkdir(parents=True, exist_ok=True)

        self.experiments_file = self.tracking_dir / "experiments.json"
        self.runs_dir = self.tracking_dir / "runs"
        self.runs_dir.mkdir(exist_ok=True)

        # Load or create experiments index
        self._experiments = self._load_experiments()

        # Ensure experiment exists
        self.experiment_id = self._get_or_create_experiment(experiment_name)

    def _load_experiments(self) -> dict[str, dict[str, Any]]:
        """Load experiments index from file."""
        if self.experiments_file.exists():
            try:
                with open(self.experiments_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {}

    def _save_experiments(self):
        """Save experiments index to file."""
        with open(self.experiments_file, "w") as f:
            json.dump(self._experiments, f, indent=2, default=str)

    def _get_or_create_experiment(self, experiment_name: str) -> str:
        """Get existing experiment ID or create new one."""
        for exp_id, exp_data in self._experiments.items():
            if exp_data.get("name") == experiment_name:
                return exp_id

        return self.create_experiment(experiment_name)

    def create_experiment(self, experiment_name: str) -> str:
        """Create a new experiment."""
        experiment_id = str(uuid.uuid4())

        self._experiments[experiment_id] = {
            "name": experiment_name,
            "creation_time": datetime.now(UTC).isoformat(),
            "lifecycle_stage": "active",
        }

        self._save_experiments()
        self.logger.info(f"Created experiment '{experiment_name}' with ID: {experiment_id}")

        return experiment_id

    def start_run(self, run_name: str | None = None, **kwargs) -> str:
        """Start a new run."""
        run_id = str(uuid.uuid4())

        run = ExperimentRun(
            run_id=run_id,
            experiment_id=self.experiment_id,
            run_name=run_name,
            status="RUNNING",
            start_time=datetime.now(UTC),
        )

        # Add any additional tags
        if kwargs:
            run.tags.update({k: str(v) for k, v in kwargs.items()})

        self._save_run(run)
        self.logger.info(f"Started run {run_id} in experiment {self.experiment_id}")

        return run_id

    def end_run(self, run_id: str, status: str = "FINISHED"):
        """End a run."""
        run = self._load_run(run_id)
        if run:
            run.status = status
            run.end_time = datetime.now(UTC)
            self._save_run(run)
            self.logger.info(f"Ended run {run_id} with status: {status}")

    def log_param(self, run_id: str, key: str, value: Any):
        """Log a parameter."""
        run = self._load_run(run_id)
        if run:
            run.params[key] = value
            self._save_run(run)

    def log_params(self, run_id: str, params: dict[str, Any]):
        """Log multiple parameters."""
        run = self._load_run(run_id)
        if run:
            run.params.update(params)
            self._save_run(run)

    def log_metric(self, run_id: str, key: str, value: float, step: int | None = None):
        """Log a metric."""
        run = self._load_run(run_id)
        if run:
            # For simplicity, store latest value (could extend to support history)
            run.metrics[key] = value
            self._save_run(run)

    def log_metrics(self, run_id: str, metrics: dict[str, float], step: int | None = None):
        """Log multiple metrics."""
        run = self._load_run(run_id)
        if run:
            run.metrics.update(metrics)
            self._save_run(run)

    def log_artifact(
        self, run_id: str, artifact_path: str | Path, artifact_name: str | None = None
    ):
        """Log an artifact."""
        run = self._load_run(run_id)
        if run:
            artifact_path = Path(artifact_path)
            artifact_name = artifact_name or artifact_path.name

            # Copy artifact to run artifacts directory
            run_artifacts_dir = self.runs_dir / run_id / "artifacts"
            run_artifacts_dir.mkdir(parents=True, exist_ok=True)

            dest_path = run_artifacts_dir / artifact_name

            if artifact_path.is_file():
                import shutil

                shutil.copy2(artifact_path, dest_path)
                run.artifacts.append(artifact_name)
                self._save_run(run)
                self.logger.debug(f"Logged artifact {artifact_name} for run {run_id}")

    def set_tag(self, run_id: str, key: str, value: str):
        """Set a tag."""
        run = self._load_run(run_id)
        if run:
            run.tags[key] = value
            self._save_run(run)

    def set_tags(self, run_id: str, tags: dict[str, str]):
        """Set multiple tags."""
        run = self._load_run(run_id)
        if run:
            run.tags.update(tags)
            self._save_run(run)

    def get_run(self, run_id: str) -> ExperimentRun | None:
        """Get run by ID."""
        return self._load_run(run_id)

    def list_runs(self, experiment_id: str | None = None) -> list[ExperimentRun]:
        """List runs for experiment."""
        experiment_id = experiment_id or self.experiment_id
        runs = []

        for run_file in self.runs_dir.glob("*/run.json"):
            run = self._load_run_from_file(run_file)
            if run and run.experiment_id == experiment_id:
                runs.append(run)

        return sorted(runs, key=lambda x: x.start_time or datetime.min, reverse=True)

    def _load_run(self, run_id: str) -> ExperimentRun | None:
        """Load run from file."""
        run_file = self.runs_dir / run_id / "run.json"
        return self._load_run_from_file(run_file)

    def _load_run_from_file(self, run_file: Path) -> ExperimentRun | None:
        """Load run from specific file."""
        if run_file.exists():
            try:
                with open(run_file) as f:
                    data = json.load(f)

                # Convert datetime strings back to datetime objects
                if data.get("start_time"):
                    data["start_time"] = datetime.fromisoformat(data["start_time"])
                if data.get("end_time"):
                    data["end_time"] = datetime.fromisoformat(data["end_time"])

                return ExperimentRun(**data)
            except (json.JSONDecodeError, FileNotFoundError, TypeError) as e:
                self.logger.warning(f"Could not load run from {run_file}: {e}")

        return None

    def _save_run(self, run: ExperimentRun):
        """Save run to file."""
        run_dir = self.runs_dir / run.run_id
        run_dir.mkdir(exist_ok=True)

        run_file = run_dir / "run.json"

        # Convert to dict and handle datetime serialization
        run_dict = asdict(run)
        if run_dict.get("start_time"):
            run_dict["start_time"] = run_dict["start_time"].isoformat()
        if run_dict.get("end_time"):
            run_dict["end_time"] = run_dict["end_time"].isoformat()

        with open(run_file, "w") as f:
            json.dump(run_dict, f, indent=2, default=str)


class MLflowTracker(ExperimentTracker):
    """
    MLflow-based experiment tracker.

    Integrates with MLflow for comprehensive experiment tracking,
    model registry, and artifact management.
    """

    def __init__(self, experiment_name: str, tracking_uri: str | None = None):
        super().__init__(experiment_name)

        try:
            import mlflow
            import mlflow.sklearn

            self.mlflow = mlflow
        except ImportError:
            raise ImportError(
                "MLflow is required for MLflowTracker. " "Install with: pip install mlflow"
            )

        # Set tracking URI if provided
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)

        # Set or create experiment
        try:
            self.experiment_id = mlflow.create_experiment(experiment_name)
            self.logger.info(f"Created MLflow experiment: {experiment_name}")
        except Exception:
            # Experiment already exists
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment:
                self.experiment_id = experiment.experiment_id
                self.logger.info(f"Using existing MLflow experiment: {experiment_name}")
            else:
                raise ValueError(f"Could not create or find experiment: {experiment_name}")

    def create_experiment(self, experiment_name: str) -> str:
        """Create a new MLflow experiment."""
        return self.mlflow.create_experiment(experiment_name)

    def start_run(self, run_name: str | None = None, **kwargs) -> str:
        """Start a new MLflow run."""
        run = self.mlflow.start_run(experiment_id=self.experiment_id, run_name=run_name, **kwargs)

        self.logger.info(f"Started MLflow run {run.info.run_id}")
        return run.info.run_id

    def end_run(self, run_id: str, status: str = "FINISHED"):
        """End MLflow run."""
        # MLflow manages active run state, so we need to ensure correct run is active
        self.mlflow.end_run(status=status.upper())
        self.logger.info(f"Ended MLflow run {run_id} with status: {status}")

    def log_param(self, run_id: str, key: str, value: Any):
        """Log parameter to MLflow."""
        with self.mlflow.start_run(run_id=run_id):
            self.mlflow.log_param(key, value)

    def log_params(self, run_id: str, params: dict[str, Any]):
        """Log multiple parameters to MLflow."""
        with self.mlflow.start_run(run_id=run_id):
            self.mlflow.log_params(params)

    def log_metric(self, run_id: str, key: str, value: float, step: int | None = None):
        """Log metric to MLflow."""
        with self.mlflow.start_run(run_id=run_id):
            self.mlflow.log_metric(key, value, step=step)

    def log_metrics(self, run_id: str, metrics: dict[str, float], step: int | None = None):
        """Log multiple metrics to MLflow."""
        with self.mlflow.start_run(run_id=run_id):
            self.mlflow.log_metrics(metrics, step=step)

    def log_artifact(
        self, run_id: str, artifact_path: str | Path, artifact_name: str | None = None
    ):
        """Log artifact to MLflow."""
        with self.mlflow.start_run(run_id=run_id):
            self.mlflow.log_artifact(str(artifact_path), artifact_path=artifact_name)

    def set_tag(self, run_id: str, key: str, value: str):
        """Set tag in MLflow."""
        with self.mlflow.start_run(run_id=run_id):
            self.mlflow.set_tag(key, value)

    def set_tags(self, run_id: str, tags: dict[str, str]):
        """Set multiple tags in MLflow."""
        with self.mlflow.start_run(run_id=run_id):
            self.mlflow.set_tags(tags)

    def get_run(self, run_id: str) -> ExperimentRun | None:
        """Get run from MLflow."""
        try:
            mlflow_run = self.mlflow.get_run(run_id)

            return ExperimentRun(
                run_id=mlflow_run.info.run_id,
                experiment_id=mlflow_run.info.experiment_id,
                run_name=mlflow_run.data.tags.get("mlflow.runName"),
                status=mlflow_run.info.status,
                start_time=(
                    datetime.fromtimestamp(mlflow_run.info.start_time / 1000)
                    if mlflow_run.info.start_time
                    else None
                ),
                end_time=(
                    datetime.fromtimestamp(mlflow_run.info.end_time / 1000)
                    if mlflow_run.info.end_time
                    else None
                ),
                metrics=dict(mlflow_run.data.metrics),
                params=dict(mlflow_run.data.params),
                tags=dict(mlflow_run.data.tags),
                artifacts=[],  # Would need separate API call to list artifacts
            )
        except Exception as e:
            self.logger.error(f"Error retrieving MLflow run {run_id}: {e}")
            return None

    def list_runs(self, experiment_id: str | None = None) -> list[ExperimentRun]:
        """List runs from MLflow."""
        experiment_id = experiment_id or self.experiment_id

        try:
            mlflow_runs = self.mlflow.search_runs(
                experiment_ids=[experiment_id], output_format="list"
            )

            runs = []
            for mlflow_run in mlflow_runs:
                run = ExperimentRun(
                    run_id=mlflow_run.info.run_id,
                    experiment_id=mlflow_run.info.experiment_id,
                    run_name=mlflow_run.data.tags.get("mlflow.runName"),
                    status=mlflow_run.info.status,
                    start_time=(
                        datetime.fromtimestamp(mlflow_run.info.start_time / 1000)
                        if mlflow_run.info.start_time
                        else None
                    ),
                    end_time=(
                        datetime.fromtimestamp(mlflow_run.info.end_time / 1000)
                        if mlflow_run.info.end_time
                        else None
                    ),
                    metrics=dict(mlflow_run.data.metrics),
                    params=dict(mlflow_run.data.params),
                    tags=dict(mlflow_run.data.tags),
                    artifacts=[],
                )
                runs.append(run)

            return runs

        except Exception as e:
            self.logger.error(f"Error listing MLflow runs: {e}")
            return []


def create_tracker(
    experiment_name: str, tracker_type: str = "auto", tracking_uri: str | None = None, **kwargs
) -> ExperimentTracker:
    """
    Create an experiment tracker.

    Args:
        experiment_name: Name of the experiment
        tracker_type: Type of tracker ("mlflow", "local", "auto")
        tracking_uri: MLflow tracking URI (if using MLflow)
        **kwargs: Additional arguments

    Returns:
        ExperimentTracker instance
    """
    if tracker_type == "auto":
        # Try MLflow first, fall back to local
        try:
            import mlflow

            tracker_type = "mlflow"
        except ImportError:
            tracker_type = "local"

    if tracker_type == "mlflow":
        return MLflowTracker(experiment_name, tracking_uri)
    elif tracker_type == "local":
        return LocalTracker(experiment_name, **kwargs)
    else:
        raise ValueError(f"Unknown tracker type: {tracker_type}")
