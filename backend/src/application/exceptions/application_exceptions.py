"""Application Layer Exception Hierarchy."""

from typing import Any, Optional


class ApplicationException(Exception):
    """Base exception for application layer.

    All application exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize application exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class EntityNotFoundException(ApplicationException):
    """Exception raised when an entity is not found.

    Used for GET, UPDATE, DELETE operations on non-existent entities.
    """

    def __init__(
        self,
        entity_type: str,
        entity_id: Any,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize entity not found exception.

        Args:
            entity_type: Type of entity (e.g., "Customer", "Transaction")
            entity_id: ID of the entity that was not found
            details: Additional details
        """
        message = f"{entity_type} with ID {entity_id} not found"
        super().__init__(
            message=message,
            error_code="ENTITY_NOT_FOUND",
            details={"entity_type": entity_type, "entity_id": str(entity_id), **(details or {})},
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class ValidationException(ApplicationException):
    """Exception raised for validation errors.

    Used when input data fails validation rules.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        validation_errors: Optional[list[dict[str, Any]]] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize validation exception.

        Args:
            message: Error message
            field: Field that failed validation
            validation_errors: List of validation errors
            details: Additional details
        """
        error_details = {
            "field": field,
            "validation_errors": validation_errors or [],
            **(details or {}),
        }
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=error_details,
        )
        self.field = field
        self.validation_errors = validation_errors or []


class ConflictException(ApplicationException):
    """Exception raised when a resource conflict occurs.

    Used when creating a resource that already exists or updating
    creates a conflict.
    """

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        conflicting_field: Optional[str] = None,
        conflicting_value: Optional[Any] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize conflict exception.

        Args:
            message: Error message
            resource_type: Type of conflicting resource
            conflicting_field: Field causing conflict
            conflicting_value: Value causing conflict
            details: Additional details
        """
        error_details = {
            "resource_type": resource_type,
            "conflicting_field": conflicting_field,
            "conflicting_value": str(conflicting_value) if conflicting_value else None,
            **(details or {}),
        }
        super().__init__(
            message=message,
            error_code="CONFLICT",
            details=error_details,
        )
        self.resource_type = resource_type
        self.conflicting_field = conflicting_field


class DuplicateTransactionException(ConflictException):
    """Exception raised when a duplicate transaction is detected.

    Used when the same transaction is submitted multiple times
    within a short time window.
    """

    def __init__(
        self,
        transaction_details: dict[str, Any],
        window_minutes: int = 5,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize duplicate transaction exception.

        Args:
            transaction_details: Details of the duplicate transaction
            window_minutes: Time window for duplicate detection
            details: Additional details
        """
        message = f"Duplicate transaction detected within {window_minutes} minutes"
        error_details = {
            "transaction_details": transaction_details,
            "window_minutes": window_minutes,
            **(details or {}),
        }
        super().__init__(
            message=message,
            resource_type="Transaction",
            conflicting_field="transaction",
            details=error_details,
        )
        self.transaction_details = transaction_details
        self.window_minutes = window_minutes


class AuthorizationException(ApplicationException):
    """Exception raised when user lacks required permissions.

    Used when a user attempts an operation they're not authorized for.
    """

    def __init__(
        self,
        message: str = "User not authorized for this operation",
        required_permission: Optional[str] = None,
        user_id: Optional[Any] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize authorization exception.

        Args:
            message: Error message
            required_permission: Permission required for operation
            user_id: ID of user attempting operation
            details: Additional details
        """
        error_details = {
            "required_permission": required_permission,
            "user_id": str(user_id) if user_id else None,
            **(details or {}),
        }
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=error_details,
        )
        self.required_permission = required_permission
        self.user_id = user_id


class AuthenticationException(ApplicationException):
    """Exception raised when authentication fails.

    Used when credentials are invalid or authentication token is missing/expired.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        reason: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize authentication exception.

        Args:
            message: Error message
            reason: Reason for authentication failure
            details: Additional details
        """
        error_details = {
            "reason": reason,
            **(details or {}),
        }
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=error_details,
        )
        self.reason = reason


class BusinessRuleViolationException(ApplicationException):
    """Exception raised when a business rule is violated.

    Used when an operation violates domain business rules.
    """

    def __init__(
        self,
        message: str,
        rule_name: Optional[str] = None,
        violated_constraint: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize business rule violation exception.

        Args:
            message: Error message
            rule_name: Name of violated business rule
            violated_constraint: Constraint that was violated
            details: Additional details
        """
        error_details = {
            "rule_name": rule_name,
            "violated_constraint": violated_constraint,
            **(details or {}),
        }
        super().__init__(
            message=message,
            error_code="BUSINESS_RULE_VIOLATION",
            details=error_details,
        )
        self.rule_name = rule_name
        self.violated_constraint = violated_constraint
