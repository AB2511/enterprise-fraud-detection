"""
Pipeline Stage

Base class for pipeline stages with dependency management and execution context.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

from ml.utils.logging_config import PipelineLogger


class StageStatus(str, Enum):
    """Pipeline stage status"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class StageResult:
    """Result of stage execution"""

    def __init__(
        self,
        stage_name: str,
        status: StageStatus,
        started_at: datetime,
        completed_at: datetime | None = None,
        duration_seconds: float | None = None,
        outputs: dict[str, Any] | None = None,
        error: str | None = None,
        retry_count: int = 0,
    ):
        self.stage_name = stage_name
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration_seconds = duration_seconds
        self.outputs = outputs or {}
        self.error = error
        self.retry_count = retry_count
        self.execution_id = str(uuid.uuid4())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "stage_name": self.stage_name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() + "Z",
            "completed_at": self.completed_at.isoformat() + "Z" if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "outputs": self.outputs,
            "error": self.error,
            "retry_count": self.retry_count,
            "execution_id": self.execution_id,
        }


class PipelineStage(ABC):
    """
    Abstract base class for pipeline stages.

    All pipeline stages must inherit from this class and implement
    the execute method. Provides dependency management, retries,
    checkpointing, and structured logging.
    """

    def __init__(
        self,
        name: str,
        dependencies: list[str] | None = None,
        max_retries: int = 0,
        retry_delay_seconds: float = 1.0,
        checkpoint: bool = False,
        description: str | None = None,
    ):
        """
        Initialize pipeline stage.

        Args:
            name: Unique stage name
            dependencies: List of stage names this stage depends on
            max_retries: Maximum number of retries on failure
            retry_delay_seconds: Delay between retries
            checkpoint: Whether to save checkpoint after success
            description: Stage description for documentation
        """
        self.name = name
        self.dependencies = set(dependencies or [])
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.checkpoint = checkpoint
        self.description = description or f"Pipeline stage: {name}"

        # Execution state
        self.status = StageStatus.PENDING
        self.result: StageResult | None = None
        self.logger: PipelineLogger | None = None

    def set_logger(self, logger: PipelineLogger) -> None:
        """Set logger for this stage"""
        self.logger = logger

    @abstractmethod
    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the stage logic.

        Args:
            inputs: Dictionary of input data from previous stages

        Returns:
            Dictionary of output data for subsequent stages
        """
        pass

    def can_execute(self, completed_stages: set[str]) -> bool:
        """
        Check if stage can execute (all dependencies completed).

        Args:
            completed_stages: Set of completed stage names

        Returns:
            True if stage can execute
        """
        return self.dependencies.issubset(completed_stages)

    def get_dependencies(self) -> set[str]:
        """Get stage dependencies"""
        return self.dependencies.copy()

    def add_dependency(self, dependency: str) -> None:
        """Add a dependency"""
        self.dependencies.add(dependency)

    def remove_dependency(self, dependency: str) -> None:
        """Remove a dependency"""
        self.dependencies.discard(dependency)

    def validate_inputs(self, inputs: dict[str, Any]) -> None:
        """
        Validate stage inputs (override in subclasses).

        Args:
            inputs: Input dictionary

        Raises:
            ValueError: If inputs are invalid
        """
        # Default implementation - no validation
        pass

    def validate_outputs(self, outputs: dict[str, Any]) -> None:
        """
        Validate stage outputs (override in subclasses).

        Args:
            outputs: Output dictionary

        Raises:
            ValueError: If outputs are invalid
        """
        # Default implementation - no validation
        pass

    def setup(self, inputs: dict[str, Any]) -> None:
        """
        Setup stage before execution (override in subclasses).

        Args:
            inputs: Input dictionary
        """
        pass

    def cleanup(self, outputs: dict[str, Any]) -> None:
        """
        Cleanup after stage execution (override in subclasses).

        Args:
            outputs: Output dictionary
        """
        pass

    def on_retry(self, attempt: int, error: Exception) -> None:
        """
        Called before retry attempt (override in subclasses).

        Args:
            attempt: Current attempt number (1-based)
            error: Exception that caused retry
        """
        if self.logger:
            self.logger.warning(
                f"Stage '{self.name}' retry attempt {attempt}/{self.max_retries}",
                error_type=type(error).__name__,
                error_msg=str(error),
            )

    def __repr__(self) -> str:
        return f"PipelineStage(name='{self.name}', dependencies={list(self.dependencies)}, status='{self.status.value}')"
