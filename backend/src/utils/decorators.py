"""Utility Decorators."""

import asyncio
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from src.config.logging_config import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def timed(func: F) -> F:
    """Decorator to log function execution time.

    Args:
        func: Function to time

    Returns:
        Wrapped function
    """

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        """Async wrapper."""
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"{func.__name__} completed",
                duration_ms=duration_ms,
            )
            return result
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"{func.__name__} failed",
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        """Sync wrapper."""
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"{func.__name__} completed",
                duration_ms=duration_ms,
            )
            return result
        except Exception as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"{func.__name__} failed",
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper  # type: ignore
    else:
        return sync_wrapper  # type: ignore


def retry(max_attempts: int = 3, delay: float = 1.0) -> Callable[[F], F]:
    """Decorator to retry function on failure.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between retries in seconds

    Returns:
        Decorator function
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Async wrapper with retry logic."""
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed, retrying",
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            error=str(exc),
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after all retries",
                            max_attempts=max_attempts,
                            error=str(exc),
                        )
            raise last_exception  # type: ignore

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Sync wrapper with retry logic."""
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{func.__name__} failed, retrying",
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            error=str(exc),
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after all retries",
                            max_attempts=max_attempts,
                            error=str(exc),
                        )
            raise last_exception  # type: ignore

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator
