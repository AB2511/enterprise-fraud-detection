"""
Pipeline Executor

Executes pipelines with retry handling, graceful failure, and structured logging.
"""

import time
from datetime import datetime
from typing import Any

from ml.pipeline.pipeline import Pipeline
from ml.pipeline.stage import StageResult, StageStatus
from ml.utils.logging_config import PipelineLogger
from ml.utils.metadata import MetadataManager
from ml.validation.schemas import PipelineRunMetadata


class PipelineExecutor:
    """
    Pipeline executor with retry handling and graceful failure recovery.

    Executes pipeline stages in dependency order, handles retries,
    saves checkpoints, and provides detailed logging.
    """

    def __init__(
        self,
        metadata_manager: MetadataManager | None = None,
        logger: PipelineLogger | None = None,
    ):
        """
        Initialize pipeline executor.

        Args:
            metadata_manager: Metadata manager for saving execution results
            logger: Logger (created if None)
        """
        self.metadata_manager = metadata_manager
        self.logger = logger or PipelineLogger("pipeline.executor")

    def execute(
        self,
        pipeline: Pipeline,
        inputs: dict[str, Any] | None = None,
        resume: bool = False,
    ) -> bool:
        """
        Execute pipeline.

        Args:
            pipeline: Pipeline to execute
            inputs: Initial inputs for pipeline
            resume: Whether to resume from checkpoint

        Returns:
            True if pipeline completed successfully, False if failed
        """
        inputs = inputs or {}

        # Try to resume from checkpoint
        if resume:
            if pipeline.load_checkpoint():
                self.logger.info(f"Resuming pipeline '{pipeline.definition.name}' from checkpoint")
            else:
                self.logger.info(
                    f"No checkpoint found for pipeline '{pipeline.definition.name}', starting fresh"
                )

        # Start execution if not already started
        if pipeline.started_at is None:
            pipeline.started_at = datetime.utcnow()
            pipeline.status = StageStatus.RUNNING

            self.logger.info(
                f"Starting pipeline '{pipeline.definition.name}' v{pipeline.definition.version}",
                total_stages=len(pipeline.definition.stages),
                execution_order=pipeline.definition.execution_order,
            )

        try:
            # Execute stages
            success = self._execute_stages(pipeline, inputs)

            # Mark pipeline as complete
            pipeline.completed_at = datetime.utcnow()
            pipeline.status = StageStatus.SUCCESS if success else StageStatus.FAILED

            # Save final checkpoint
            pipeline.save_checkpoint()

            # Save to metadata manager
            if self.metadata_manager:
                self._save_pipeline_metadata(pipeline)

            # Log summary
            summary = pipeline.get_summary()
            if success:
                self.logger.info(
                    f"Pipeline '{pipeline.definition.name}' completed successfully", **summary
                )
            else:
                self.logger.error(f"Pipeline '{pipeline.definition.name}' failed", **summary)

            return success

        except Exception as e:
            pipeline.status = StageStatus.FAILED
            pipeline.completed_at = datetime.utcnow()

            self.logger.error(
                f"Pipeline '{pipeline.definition.name}' failed with exception",
                exc_info=True,
                error_type=type(e).__name__,
                error_msg=str(e),
            )

            pipeline.save_checkpoint()
            return False

    def _execute_stages(self, pipeline: Pipeline, initial_inputs: dict[str, Any]) -> bool:
        """Execute pipeline stages in order"""
        current_inputs = initial_inputs.copy()

        while not pipeline.is_complete():
            # Get next executable stages
            executable_stages = pipeline.get_next_executable_stages()

            if not executable_stages:
                if pipeline.has_failures():
                    self.logger.error("Cannot continue - some stages failed")
                    return False
                else:
                    self.logger.warning("No executable stages found but pipeline not complete")
                    break

            # Execute stages (could be parallelized in future)
            for stage_name in executable_stages:
                success = self._execute_stage(pipeline, stage_name, current_inputs)

                if success:
                    # Merge outputs into inputs for next stages
                    stage_outputs = pipeline.stage_outputs.get(stage_name, {})
                    current_inputs.update(stage_outputs)
                else:
                    # Stage failed, cannot continue if it's critical
                    self.logger.error(f"Critical stage '{stage_name}' failed, stopping pipeline")
                    return False

                # Save checkpoint after each stage
                pipeline.save_checkpoint()

        return not pipeline.has_failures()

    def _execute_stage(self, pipeline: Pipeline, stage_name: str, inputs: dict[str, Any]) -> bool:
        """Execute a single stage with retry logic"""
        stage = pipeline.definition.get_stage(stage_name)

        # Create stage inputs (only dependencies' outputs + initial inputs)
        stage_inputs = inputs.copy()
        for dep_name in stage.dependencies:
            if dep_name in pipeline.stage_outputs:
                stage_inputs.update(pipeline.stage_outputs[dep_name])

        attempt = 0
        max_attempts = stage.max_retries + 1

        while attempt < max_attempts:
            attempt += 1

            # Create result object
            started_at = datetime.utcnow()
            result = StageResult(
                stage_name=stage_name,
                status=StageStatus.RUNNING,
                started_at=started_at,
                retry_count=attempt - 1,
            )

            # Update stage status
            stage.status = StageStatus.RETRYING if attempt > 1 else StageStatus.RUNNING

            self.logger.info(
                f"Executing stage '{stage_name}' (attempt {attempt}/{max_attempts})",
                stage_description=stage.description,
                dependencies=list(stage.dependencies),
            )

            try:
                # Setup stage
                stage.setup(stage_inputs)

                # Validate inputs
                stage.validate_inputs(stage_inputs)

                # Execute stage
                with self.logger.timed_operation(f"stage_{stage_name}"):
                    outputs = stage.execute(stage_inputs)

                # Validate outputs
                stage.validate_outputs(outputs)

                # Cleanup
                stage.cleanup(outputs)

                # Mark success
                completed_at = datetime.utcnow()
                duration = (completed_at - started_at).total_seconds()

                result.status = StageStatus.SUCCESS
                result.completed_at = completed_at
                result.duration_seconds = duration
                result.outputs = outputs

                stage.status = StageStatus.SUCCESS
                pipeline.stage_results[stage_name] = result
                pipeline.stage_outputs[stage_name] = outputs

                self.logger.info(
                    f"Stage '{stage_name}' completed successfully",
                    duration_seconds=duration,
                    output_keys=list(outputs.keys()),
                )

                return True

            except Exception as e:
                # Mark failure
                completed_at = datetime.utcnow()
                duration = (completed_at - started_at).total_seconds()

                result.status = StageStatus.FAILED
                result.completed_at = completed_at
                result.duration_seconds = duration
                result.error = str(e)

                self.logger.error(
                    f"Stage '{stage_name}' failed (attempt {attempt}/{max_attempts})",
                    exc_info=True,
                    duration_seconds=duration,
                    error_type=type(e).__name__,
                    error_msg=str(e),
                )

                # Check if we should retry
                if attempt < max_attempts:
                    # Call retry hook
                    stage.on_retry(attempt, e)

                    # Wait before retry
                    if stage.retry_delay_seconds > 0:
                        time.sleep(stage.retry_delay_seconds)

                    continue
                else:
                    # No more retries
                    stage.status = StageStatus.FAILED
                    pipeline.stage_results[stage_name] = result
                    return False

        return False

    def _save_pipeline_metadata(self, pipeline: Pipeline) -> None:
        """Save pipeline execution metadata"""
        if not self.metadata_manager:
            return

        try:
            # Calculate statistics
            total_duration = None
            if pipeline.started_at and pipeline.completed_at:
                total_duration = (pipeline.completed_at - pipeline.started_at).total_seconds()

            records_processed = 0
            records_failed = 0
            errors = []

            for result in pipeline.stage_results.values():
                if result.status == StageStatus.SUCCESS:
                    # Try to extract record counts from outputs
                    if "records_processed" in result.outputs:
                        records_processed += result.outputs["records_processed"]
                else:
                    records_failed += 1
                    if result.error:
                        errors.append(f"{result.stage_name}: {result.error}")

            # Create metadata
            metadata = PipelineRunMetadata(
                pipeline_name=pipeline.definition.name,
                pipeline_version=pipeline.definition.version,
                started_at=pipeline.started_at,
                completed_at=pipeline.completed_at,
                status="success" if pipeline.status == StageStatus.SUCCESS else "failed",
                records_processed=records_processed,
                records_failed=records_failed,
                processing_time_seconds=total_duration,
                errors=errors,
            )

            # Save metadata
            self.metadata_manager.save_pipeline_run(metadata)

        except Exception as e:
            self.logger.warning(f"Failed to save pipeline metadata: {e}")
