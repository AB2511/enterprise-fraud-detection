"""Base Domain Exception."""


class DomainException(Exception):
    """Base exception for all domain-level errors.

    Domain exceptions represent business rule violations and
    invalid state transitions in the domain model.
    """

    def __init__(self, message: str, code: str = "DOMAIN_ERROR") -> None:
        """Initialize domain exception.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
        """
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        """Return string representation."""
        return f"[{self.code}] {self.message}"


class RepositoryError(DomainException):
    """Exception raised by repository operations.

    Indicates infrastructure-level errors during data persistence operations.
    """

    def __init__(self, message: str) -> None:
        """Initialize repository error.

        Args:
            message: Error description
        """
        super().__init__(message, "REPOSITORY_ERROR")


class NotFoundError(DomainException):
    """Exception raised when an entity is not found in repository.

    Indicates the requested entity does not exist.
    """

    def __init__(self, message: str) -> None:
        """Initialize not found error.

        Args:
            message: Error description
        """
        super().__init__(message, "NOT_FOUND")


class ConflictError(DomainException):
    """Exception raised when a resource conflict occurs.

    Indicates a constraint violation or duplicate resource.
    """

    def __init__(self, message: str) -> None:
        """Initialize conflict error.

        Args:
            message: Error description
        """
        super().__init__(message, "CONFLICT_ERROR")
