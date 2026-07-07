"""
Pipeline

Container for pipeline stages with execution graph and dependency resolution.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ml.pipeline.stage import PipelineStage, StageResult, StageStatus
from ml.utils.logging_config import PipelineLogger


class PipelineDefinition:
    """Pipeline definition with stages and metadata"""

    def __init__(
        self,
        name: str,
        version: str,
        description: str | None = None,
        stages: list[PipelineStage] | None = None,
    ):
        """
        Initialize pipeline definition.

        Args:
            name: Pipeline name
            version: Pipeline version
            description: Pipeline description
            stages: List of pipeline stages
        """
        self.name = name
        self.version = version
        self.description = description or f"Pipeline: {name}"
        self.stages: dict[str, PipelineStage] = {}
        self.execution_order: list[str] = []

        # Add stages if provided
        if stages:
            for stage in stages:
                self.add_stage(stage)

    def add_stage(self, stage: PipelineStage) -> None:
        """
        Add stage to pipeline.

        Args:
            stage: Pipeline stage to add
        """
        if stage.name in self.stages:
            raise ValueError(f"Stage '{stage.name}' already exists in pipeline")

        self.stages[stage.name] = stage
        self._update_execution_order()

    def remove_stage(self, stage_name: str) -> None:
        """
        Remove stage from pipeline.

        Args:
            stage_name: Name of stage to remove
        """
        if stage_name not in self.stages:
            raise ValueError(f"Stage '{stage_name}' not found in pipeline")

        # Check if other stages depend on this stage
        dependents = [
            name
            for name, stage in self.stages.items()
            if stage_name in stage.dependencies and name != stage_name
        ]

        if dependents:
            raise ValueError(
                f"Cannot remove stage '{stage_name}' - it has dependents: {dependents}"
            )

        del self.stages[stage_name]
        self._update_execution_order()

    def get_stage(self, stage_name: str) -> PipelineStage:
        """Get stage by name"""
        if stage_name not in self.stages:
            raise ValueError(f"Stage '{stage_name}' not found in pipeline")
        return self.stages[stage_name]

    def _update_execution_order(self) -> None:
        """Update execution order based on dependencies (topological sort)"""
        # Kahn's algorithm for topological sorting
        in_degree = dict.fromkeys(self.stages, 0)

        # Calculate in-degrees
        for stage in self.stages.values():
            for dep in stage.dependencies:
                if dep in in_degree:
                    in_degree[stage.name] += 1

        # Find stages with no dependencies
        queue = [name for name, degree in in_degree.items() if degree == 0]
        order = []

        while queue:
            # Sort queue to ensure deterministic order
            queue.sort()
            current = queue.pop(0)
            order.append(current)

            # Update in-degrees of dependent stages
            current_stage = self.stages[current]
            for stage_name, stage in self.stages.items():
                if current in stage.dependencies:
                    in_degree[stage_name] -= 1
                    if in_degree[stage_name] == 0:
                        queue.append(stage_name)

        # Check for cycles
        if len(order) != len(self.stages):
            raise ValueError("Circular dependency detected in pipeline stages")

        self.execution_order = order

    def validate_dependencies(self) -> None:
        """Validate that all dependencies exist"""
        all_stages = set(self.stages.keys())

        for stage_name, stage in self.stages.items():
            missing_deps = stage.dependencies - all_stages
            if missing_deps:
                raise ValueError(f"Stage '{stage_name}' has missing dependencies: {missing_deps}")

    def get_execution_order(self) -> list[str]:
        """Get stages in execution order"""
        return self.execution_order.copy()

    def to_dict(self) -> dict[str, Any]:
        """Convert pipeline definition to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "stages": {
                name: {
                    "dependencies": list(stage.dependencies),
                    "max_retries": stage.max_retries,
                    "checkpoint": stage.checkpoint,
                    "description": stage.description,
                }
                for name, stage in self.stages.items()
            },
            "execution_order": self.execution_order,
        }

    def save_definition(self, path: Path) -> None:
        """Save pipeline definition to JSON"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


class Pipeline:
    """
    Pipeline execution container.

    Manages stage execution, dependency resolution, checkpointing,
    and resumable execution.
    """

    def __init__(
        self,
        definition: PipelineDefinition,
        logger: PipelineLogger | None = None,
    ):
        """
        Initialize pipeline.

        Args:
            definition: Pipeline definition
            logger: Pipeline logger (created if None)
        """
        self.definition = definition
        self.logger = logger or PipelineLogger(f"pipeline.{definition.name}")

        # Set logger for all stages
        for stage in self.definition.stages.values():
            stage.set_logger(self.logger)

        # Execution state
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.status: StageStatus = StageStatus.PENDING
        self.stage_results: dict[str, StageResult] = {}
        self.stage_outputs: dict[str, dict[str, Any]] = {}

        # Resumable execution
        self.checkpoint_path: Path | None = None

    def set_checkpoint_path(self, path: Path) -> None:
        """Set checkpoint save path for resumable execution"""
        self.checkpoint_path = path

    def save_checkpoint(self) -> None:
        """Save execution checkpoint"""
        if not self.checkpoint_path:
            return

        checkpoint_data = {
            "pipeline_name": self.definition.name,
            "pipeline_version": self.definition.version,
            "started_at": self.started_at.isoformat() + "Z" if self.started_at else None,
            "status": self.status.value,
            "stage_results": {
                name: result.to_dict() for name, result in self.stage_results.items()
            },
            "stage_outputs": self.stage_outputs,
        }

        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_path, "w") as f:
            json.dump(checkpoint_data, f, indent=2, default=str)

        self.logger.debug("Checkpoint saved", checkpoint_path=str(self.checkpoint_path))

    def load_checkpoint(self) -> bool:
        """
        Load execution checkpoint.

        Returns:
            True if checkpoint was loaded, False if not found
        """
        if not self.checkpoint_path or not self.checkpoint_path.exists():
            return False

        try:
            with open(self.checkpoint_path) as f:
                checkpoint_data = json.load(f)

            # Restore execution state
            if checkpoint_data.get("started_at"):
                self.started_at = datetime.fromisoformat(
                    checkpoint_data["started_at"].replace("Z", "+00:00")
                )

            self.status = StageStatus(checkpoint_data["status"])
            self.stage_outputs = checkpoint_data.get("stage_outputs", {})

            # Restore stage results
            for stage_name, result_data in checkpoint_data.get("stage_results", {}).items():
                result = StageResult(
                    stage_name=result_data["stage_name"],
                    status=StageStatus(result_data["status"]),
                    started_at=datetime.fromisoformat(
                        result_data["started_at"].replace("Z", "+00:00")
                    ),
                    completed_at=(
                        datetime.fromisoformat(result_data["completed_at"].replace("Z", "+00:00"))
                        if result_data.get("completed_at")
                        else None
                    ),
                    duration_seconds=result_data.get("duration_seconds"),
                    outputs=result_data.get("outputs", {}),
                    error=result_data.get("error"),
                    retry_count=result_data.get("retry_count", 0),
                )
                result.execution_id = result_data.get("execution_id", result.execution_id)
                self.stage_results[stage_name] = result

            self.logger.info("Checkpoint loaded", checkpoint_path=str(self.checkpoint_path))
            return True

        except Exception as e:
            self.logger.warning(f"Failed to load checkpoint: {e}")
            return False

    def get_completed_stages(self) -> set[str]:
        """Get set of completed stage names"""
        return {
            name
            for name, result in self.stage_results.items()
            if result.status == StageStatus.SUCCESS
        }

    def get_failed_stages(self) -> set[str]:
        """Get set of failed stage names"""
        return {
            name
            for name, result in self.stage_results.items()
            if result.status == StageStatus.FAILED
        }

    def get_next_executable_stages(self) -> list[str]:
        """Get list of stages ready to execute"""
        completed = self.get_completed_stages()
        failed = self.get_failed_stages()

        executable = []
        for stage_name in self.definition.execution_order:
            # Skip if already processed
            if stage_name in self.stage_results:
                continue

            # Check if dependencies are met
            stage = self.definition.get_stage(stage_name)
            if stage.can_execute(completed):
                # Check that no dependencies failed
                if not (stage.dependencies & failed):
                    executable.append(stage_name)

        return executable

    def is_complete(self) -> bool:
        """Check if pipeline execution is complete"""
        return len(self.stage_results) == len(self.definition.stages)

    def has_failures(self) -> bool:
        """Check if any stages failed"""
        return len(self.get_failed_stages()) > 0

    def get_summary(self) -> dict[str, Any]:
        """Get execution summary"""
        total_stages = len(self.definition.stages)
        completed_stages = len(self.get_completed_stages())
        failed_stages = len(self.get_failed_stages())
        pending_stages = total_stages - len(self.stage_results)

        duration_seconds = None
        if self.started_at:
            end_time = self.completed_at or datetime.utcnow()
            duration_seconds = (end_time - self.started_at).total_seconds()

        return {
            "pipeline_name": self.definition.name,
            "pipeline_version": self.definition.version,
            "status": self.status.value,
            "total_stages": total_stages,
            "completed_stages": completed_stages,
            "failed_stages": failed_stages,
            "pending_stages": pending_stages,
            "started_at": self.started_at.isoformat() + "Z" if self.started_at else None,
            "completed_at": self.completed_at.isoformat() + "Z" if self.completed_at else None,
            "duration_seconds": duration_seconds,
        }
