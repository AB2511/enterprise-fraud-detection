"""User Repository Interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.user import User


class UserRepository(ABC):
    """Repository interface for User entity."""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: User entity to create

        Returns:
            Created user with generated ID

        Raises:
            RepositoryError: If creation fails
            ConflictError: If email already exists
        """
        pass

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Retrieve user by ID.

        Args:
            user_id: User UUID

        Returns:
            User if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Retrieve user by email.

        Args:
            email: User email address

        Returns:
            User if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update existing user.

        Args:
            user: User entity with updated data

        Returns:
            Updated user

        Raises:
            RepositoryError: If update fails
            NotFoundError: If user doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Soft delete user.

        Args:
            user_id: User UUID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        pass

    @abstractmethod
    async def list_by_role(
        self,
        role: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """List users by role.

        Args:
            role: User role
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of users
        """
        pass

    @abstractmethod
    async def list_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """List active users.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of active users
        """
        pass

    @abstractmethod
    async def count_by_role(self, role: str) -> int:
        """Count users by role.

        Args:
            role: User role

        Returns:
            Number of users
        """
        pass

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists.

        Args:
            email: Email address to check

        Returns:
            True if email exists
        """
        pass
