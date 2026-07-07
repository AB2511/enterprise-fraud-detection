"""
ML Pipeline Logging Framework

Centralized structured JSON logging for all ML pipeline components.
Supports correlation IDs, pipeline run IDs, and execution timing.
"""

import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================================
# Log Level Configuration
# ============================================================================

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


# ============================================================================
# Structured JSON Formatter
# ============================================================================


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs log records as JSON with consistent structure:
    - timestamp
    - level
    - logger name
    - message
    - context (correlation_id, pipeline_run_id, etc.)
    - extra fields
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context fields if present
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        if hasattr(record, "pipeline_run_id"):
            log_data["pipeline_run_id"] = record.pipeline_run_id

        if hasattr(record, "stage"):
            log_data["stage"] = record.stage

        if hasattr(record, "dataset_id"):
            log_data["dataset_id"] = record.dataset_id

        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data)


# ============================================================================
# Pipeline Logger
# ============================================================================


class PipelineLogger:
    """
    Centralized logger for ML pipeline with context management.

    Features:
    - Structured JSON logging
    - Correlation ID tracking
    - Pipeline run ID tracking
    - Stage tracking
    - Execution timing
    - Error categorization
    """

    def __init__(
        self,
        name: str,
        log_level: str = "INFO",
        log_file: Path | None = None,
        pipeline_run_id: str | None = None,
    ):
        """
        Initialize pipeline logger.

        Args:
            name: Logger name (e.g., "ml.data.adapter")
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional path to log file
            pipeline_run_id: Optional pipeline run ID for tracking
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(LOG_LEVELS.get(log_level, logging.INFO))
        self.logger.handlers.clear()  # Remove any existing handlers

        # Generate unique IDs
        self.pipeline_run_id = pipeline_run_id or str(uuid.uuid4())
        self.correlation_id = str(uuid.uuid4())

        # Current stage context
        self.current_stage: str | None = None
        self.current_dataset_id: str | None = None

        # Setup handlers
        self._setup_handlers(log_file)

    def _setup_handlers(self, log_file: Path | None) -> None:
        """Setup console and file handlers"""
        formatter = JSONFormatter()

        # Console handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler (if specified)
        if log_file:
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _create_log_record(self, **kwargs) -> dict[str, Any]:
        """Create log record with context"""
        record = {
            "correlation_id": self.correlation_id,
            "pipeline_run_id": self.pipeline_run_id,
        }

        if self.current_stage:
            record["stage"] = self.current_stage

        if self.current_dataset_id:
            record["dataset_id"] = self.current_dataset_id

        record.update(kwargs)
        return record

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        extra = self._create_log_record(**kwargs)
        self.logger.debug(message, extra=extra)

    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        extra = self._create_log_record(**kwargs)
        self.logger.info(message, extra=extra)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        extra = self._create_log_record(**kwargs)
        self.logger.warning(message, extra=extra)

    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log error message"""
        extra = self._create_log_record(**kwargs)
        self.logger.error(message, exc_info=exc_info, extra=extra)

    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log critical message"""
        extra = self._create_log_record(**kwargs)
        self.logger.critical(message, exc_info=exc_info, extra=extra)

    def set_stage(self, stage: str) -> None:
        """Set current pipeline stage for context"""
        self.current_stage = stage
        self.info(f"Entering stage: {stage}")

    def set_dataset(self, dataset_id: str) -> None:
        """Set current dataset ID for context"""
        self.current_dataset_id = dataset_id

    @contextmanager
    def stage_context(self, stage: str):
        """
        Context manager for pipeline stage with automatic timing.

        Usage:
            with logger.stage_context("data_loading"):
                # ... stage code ...
        """
        start_time = time.time()
        old_stage = self.current_stage

        self.set_stage(stage)
        try:
            yield self
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.error(
                f"Stage '{stage}' failed",
                exc_info=True,
                duration_ms=duration_ms,
                error_type=type(e).__name__,
            )
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.info(
                f"Stage '{stage}' completed",
                duration_ms=duration_ms,
            )
            self.current_stage = old_stage

    @contextmanager
    def timed_operation(self, operation_name: str):
        """
        Context manager for timing an operation.

        Usage:
            with logger.timed_operation("load_dataset"):
                # ... operation code ...
        """
        start_time = time.time()
        self.debug(f"Starting operation: {operation_name}")

        try:
            yield
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.error(
                f"Operation '{operation_name}' failed",
                exc_info=True,
                duration_ms=duration_ms,
                error_type=type(e).__name__,
            )
            raise
        else:
            duration_ms = (time.time() - start_time) * 1000
            self.info(
                f"Operation '{operation_name}' completed",
                duration_ms=duration_ms,
            )

    def log_dataset_info(self, dataset_id: str, num_records: int, **kwargs) -> None:
        """Log dataset information"""
        self.info(
            f"Dataset loaded: {num_records:,} records",
            dataset_id=dataset_id,
            num_records=num_records,
            extra_data=kwargs,
        )

    def log_validation_result(
        self, passed: bool, total_checks: int, failed_checks: int, **kwargs
    ) -> None:
        """Log validation result"""
        level = self.info if passed else self.error
        level(
            f"Validation {'passed' if passed else 'FAILED'}: "
            f"{total_checks - failed_checks}/{total_checks} checks passed",
            validation_passed=passed,
            total_checks=total_checks,
            failed_checks=failed_checks,
            extra_data=kwargs,
        )

    def log_execution_summary(
        self, records_processed: int, records_failed: int, duration_seconds: float, **kwargs
    ) -> None:
        """Log execution summary"""
        self.info(
            f"Execution complete: {records_processed:,} processed, "
            f"{records_failed} failed in {duration_seconds:.2f}s",
            records_processed=records_processed,
            records_failed=records_failed,
            duration_seconds=duration_seconds,
            extra_data=kwargs,
        )


# ============================================================================
# Global Logger Factory
# ============================================================================

_loggers: dict[str, PipelineLogger] = {}


def get_logger(
    name: str,
    log_level: str = "INFO",
    log_file: Path | None = None,
    pipeline_run_id: str | None = None,
) -> PipelineLogger:
    """
    Get or create a pipeline logger.

    Args:
        name: Logger name
        log_level: Logging level
        log_file: Optional log file path
        pipeline_run_id: Optional pipeline run ID

    Returns:
        PipelineLogger instance
    """
    if name not in _loggers:
        _loggers[name] = PipelineLogger(
            name=name,
            log_level=log_level,
            log_file=log_file,
            pipeline_run_id=pipeline_run_id,
        )
    return _loggers[name]


def clear_loggers() -> None:
    """Clear all cached loggers (useful for testing)"""
    global _loggers
    _loggers.clear()


# ============================================================================
# Error Categories
# ============================================================================


class ErrorCategory:
    """Error categorization for better debugging"""

    DATA_LOADING = "data_loading"
    DATA_VALIDATION = "data_validation"
    DATA_PROCESSING = "data_processing"
    FEATURE_ENGINEERING = "feature_engineering"
    PIPELINE_EXECUTION = "pipeline_execution"
    CONFIGURATION = "configuration"
    FILE_SYSTEM = "file_system"
    UNKNOWN = "unknown"


def categorize_error(exception: Exception) -> str:
    """
    Categorize an exception for better error tracking.

    Args:
        exception: Exception instance

    Returns:
        Error category string
    """
    error_type = type(exception).__name__
    error_msg = str(exception).lower()

    # Data loading errors
    if any(term in error_msg for term in ["file not found", "no such file", "cannot open"]):
        return ErrorCategory.FILE_SYSTEM

    if any(term in error_type.lower() for term in ["read", "parse", "decode"]):
        return ErrorCategory.DATA_LOADING

    # Validation errors
    if "validation" in error_type.lower() or "validation" in error_msg:
        return ErrorCategory.DATA_VALIDATION

    # Configuration errors
    if any(term in error_msg for term in ["config", "setting", "parameter"]):
        return ErrorCategory.CONFIGURATION

    # Processing errors
    if any(term in error_type.lower() for term in ["value", "type", "key", "index"]):
        return ErrorCategory.DATA_PROCESSING

    return ErrorCategory.UNKNOWN


# ============================================================================
# Setup Function (for backwards compatibility)
# ============================================================================


def setup_logging(level: str = "INFO", log_file: Path | None = None, format: str = "json") -> None:
    """
    Setup basic logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        format: Log format ('json' or 'standard')
    """
    # Convert level to logging constant
    log_level = LOG_LEVELS.get(level.upper(), logging.INFO)

    # Clear existing handlers
    logging.getLogger().handlers.clear()

    # Create formatter
    if format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # Setup file handler if specified
    handlers = [console_handler]
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=log_level, handlers=handlers, force=True  # Override existing configuration
    )
