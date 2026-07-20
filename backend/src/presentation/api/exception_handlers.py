"""Global Exception Handlers for FastAPI.

Converts application exceptions to RFC7807 Problem Details format
with consistent error responses.
"""

from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.application.exceptions.application_exceptions import (
    ApplicationException,
    AuthenticationException,
    AuthorizationException,
    BusinessRuleViolationException,
    ConflictException,
    DuplicateTransactionException,
    EntityNotFoundException,
    ValidationException,
)
from src.config.logging_config import get_logger

logger = get_logger(__name__)


def create_problem_detail(
    status_code: int,
    title: str,
    detail: str,
    error_type: str = "about:blank",
    instance: str = "",
    **kwargs: object,
) -> dict:
    """Create RFC7807 Problem Details response.

    Args:
        status_code: HTTP status code
        title: Short error title
        detail: Detailed error description
        error_type: URI reference identifying the problem type
        instance: URI reference identifying the specific occurrence
        **kwargs: Additional members for the problem detail

    Returns:
        Problem details dictionary
    """
    problem = {
        "type": error_type,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }
    problem.update(kwargs)
    return problem


async def entity_not_found_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle EntityNotFoundException.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON response with 404 status
    """
    entity_exc = cast(EntityNotFoundException, exc)

    logger.warning(
        "Entity not found",
        entity_type=entity_exc.entity_type,
        entity_id=entity_exc.entity_id,
        path=request.url.path,
    )

    problem = create_problem_detail(
        status_code=status.HTTP_404_NOT_FOUND,
        title="Entity Not Found",
        detail=entity_exc.message,
        error_type="entity-not-found",
        instance=str(request.url),
        entity_type=entity_exc.entity_type,
        entity_id=str(entity_exc.entity_id),
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=problem,
    )


async def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle ValidationException.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON response with 422 status
    """
    validation_exc = cast(ValidationException, exc)

    logger.warning(
        "Validation error",
        field=validation_exc.field,
        errors=validation_exc.validation_errors,
        path=request.url.path,
    )

    problem = create_problem_detail(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        title="Validation Error",
        detail=validation_exc.message,
        error_type="validation-error",
        instance=str(request.url),
        field=validation_exc.field,
        validation_errors=validation_exc.validation_errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem,
    )


async def conflict_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle ConflictException.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON response with 409 status
    """
    conflict_exc = cast(ConflictException, exc)

    logger.warning(
        "Resource conflict",
        resource_type=conflict_exc.resource_type,
        field=conflict_exc.conflicting_field,
        path=request.url.path,
    )

    problem = create_problem_detail(
        status_code=status.HTTP_409_CONFLICT,
        title="Resource Conflict",
        detail=conflict_exc.message,
        error_type="conflict",
        instance=str(request.url),
        resource_type=conflict_exc.resource_type,
        conflicting_field=conflict_exc.conflicting_field,
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=problem,
    )


async def duplicate_transaction_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle DuplicateTransactionException.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON response with 409 status
    """
    duplicate_exc = cast(DuplicateTransactionException, exc)

    logger.warning(
        "Duplicate transaction",
        details=duplicate_exc.transaction_details,
        window=duplicate_exc.window_minutes,
        path=request.url.path,
    )

    problem = create_problem_detail(
        status_code=status.HTTP_409_CONFLICT,
        title="Duplicate Transaction",
        detail=duplicate_exc.message,
        error_type="duplicate-transaction",
        instance=str(request.url),
        window_minutes=duplicate_exc.window_minutes,
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=problem,
    )


async def authorization_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle AuthorizationException.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON response with 403 status
    """
    authorization_exc = cast(AuthorizationException, exc)

    logger.warning(
        "Authorization failed",
        required_permission=authorization_exc.required_permission,
        user_id=authorization_exc.user_id,
        path=request.url.path,
    )

    problem = create_problem_detail(
        status_code=status.HTTP_403_FORBIDDEN,
        title="Authorization Failed",
        detail=authorization_exc.message,
        error_type="authorization-error",
        instance=str(request.url),
        required_permission=authorization_exc.required_permission,
    )

    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=problem,
    )


async def authentication_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle AuthenticationException.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON response with 401 status
    """
    authentication_exc = cast(AuthenticationException, exc)

    logger.warning(
        "Authentication failed",
        reason=authentication_exc.reason,
        path=request.url.path,
    )

    problem = create_problem_detail(
        status_code=status.HTTP_401_UNAUTHORIZED,
        title="Authentication Failed",
        detail=authentication_exc.message,
        error_type="authentication-error",
        instance=str(request.url),
        reason=authentication_exc.reason,
    )

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=problem,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def business_rule_violation_handler(
    request: Request,
    exc: BusinessRuleViolationException,
) -> JSONResponse:
    """Handle BusinessRuleViolationException.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON response with 400 status
    """
    logger.warning(
        "Business rule violation",
        rule_name=exc.rule_name,
        constraint=exc.violated_constraint,
        path=request.url.path,
    )

    problem = create_problem_detail(
        status_code=status.HTTP_400_BAD_REQUEST,
        title="Business Rule Violation",
        detail=exc.message,
        error_type="business-rule-violation",
        instance=str(request.url),
        rule_name=exc.rule_name,
        violated_constraint=exc.violated_constraint,
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=problem,
    )


async def application_exception_handler(
    request: Request,
    exc: ApplicationException,
) -> JSONResponse:
    """Handle generic ApplicationException.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON response with 500 status
    """
    logger.error(
        "Application error",
        error_code=exc.error_code,
        details=exc.details,
        path=request.url.path,
    )

    problem = create_problem_detail(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        title="Application Error",
        detail=exc.message,
        error_type=exc.error_code.lower().replace("_", "-"),
        instance=str(request.url),
        **exc.details,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem,
    )


async def pydantic_validation_handler(
    request: Request,
    exc: RequestValidationError | ValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors.

    Args:
        request: FastAPI request
        exc: Validation exception

    Returns:
        JSON response with 422 status
    """
    errors = exc.errors() if hasattr(exc, "errors") else []

    logger.warning(
        "Request validation failed",
        errors=errors,
        path=request.url.path,
    )

    problem = create_problem_detail(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        title="Request Validation Error",
        detail="Request data validation failed",
        error_type="validation-error",
        instance=str(request.url),
        validation_errors=errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem,
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions.

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON response with 500 status
    """
    logger.exception(
        "Unhandled exception",
        exception_type=type(exc).__name__,
        path=request.url.path,
    )

    problem = create_problem_detail(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        title="Internal Server Error",
        detail="An unexpected error occurred. Please try again later.",
        error_type="internal-error",
        instance=str(request.url),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem,
    )


def add_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Application exceptions
    app.add_exception_handler(EntityNotFoundException, entity_not_found_handler)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(ConflictException, conflict_exception_handler)
    app.add_exception_handler(DuplicateTransactionException, duplicate_transaction_handler)
    app.add_exception_handler(AuthorizationException, authorization_exception_handler)
    app.add_exception_handler(AuthenticationException, authentication_exception_handler)
    app.add_exception_handler(
        BusinessRuleViolationException,
        cast(Callable[[Request, Exception], Awaitable[JSONResponse]], business_rule_violation_handler),
    )
    app.add_exception_handler(
        ApplicationException,
        cast(Callable[[Request, Exception], Awaitable[JSONResponse]], application_exception_handler),
    )

    # Framework exceptions
    app.add_exception_handler(
        RequestValidationError,
        cast(Callable[[Request, Exception], Awaitable[JSONResponse]], pydantic_validation_handler),
    )
    app.add_exception_handler(
        ValidationError,
        cast(Callable[[Request, Exception], Awaitable[JSONResponse]], pydantic_validation_handler),
    )

    # Catch-all
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered")
