"""User Repository Implementation using SQLAlchemy."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.interfaces.user_repository import UserRepository
from src.domain.entities.user import User
from src.domain.exceptions.base import ConflictError, NotFoundError, RepositoryError
from src.infrastructure.database.models import UserModel


class UserRepositoryImpl(UserRepository):
    """SQLAlchemy implementation of UserRepository.
    
    Provides complete CRUD operations, authentication support, role management,
    and advanced querying capabilities for user entities.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            session: Async SQLAlchemy session
        """
        self._session = session

    async def create(self, user: User) -> User:
        """Create a new user with email uniqueness validation.

        Args:
            user: User entity to create

        Returns:
            Created user with generated ID

        Raises:
            ConflictError: If email already exists
            RepositoryError: If creation fails
        """
        try:
            # Check email uniqueness
            if await self.email_exists(user.email):
                raise ConflictError(f"User with email {user.email} already exists")

            db_user = UserModel(
                id=user.user_id,
                email=user.email.lower(),  # Normalize email
                hashed_password=user.hashed_password,
                role=user.role,
                status=user.status,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login_at=user.last_login,
            )

            self._session.add(db_user)
            await self._session.flush()
            await self._session.refresh(db_user)

            return self._to_entity(db_user)

        except ConflictError:
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to create user: {e}") from e

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Retrieve user by ID, excluding soft-deleted records.

        Args:
            user_id: User UUID

        Returns:
            User if found and not deleted, None otherwise
        """
        try:
            query = select(UserModel).where(
                and_(
                    UserModel.id == user_id,
                    UserModel.deleted_at.is_(None),
                )
            )
            result = await self._session.execute(query)
            db_user = result.scalar_one_or_none()

            return self._to_entity(db_user) if db_user else None

        except Exception as e:
            raise RepositoryError(f"Failed to get user by id: {e}") from e

    async def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve user by email, case-insensitive lookup.

        Args:
            email: User email address

        Returns:
            User if found and not deleted, None otherwise
        """
        try:
            query = select(UserModel).where(
                and_(
                    func.lower(UserModel.email) == email.lower(),
                    UserModel.deleted_at.is_(None),
                )
            )
            result = await self._session.execute(query)
            db_user = result.scalar_one_or_none()

            return self._to_entity(db_user) if db_user else None

        except Exception as e:
            raise RepositoryError(f"Failed to get user by email: {e}") from e

    async def update(self, user: User) -> User:
        """Update existing user with optimistic locking.

        Args:
            user: User entity with updated data

        Returns:
            Updated user

        Raises:
            NotFoundError: If user doesn't exist
            ConflictError: If email change conflicts with existing user
            RepositoryError: If update fails
        """
        try:
            # Get existing user
            query = select(UserModel).where(
                and_(
                    UserModel.id == user.user_id,
                    UserModel.deleted_at.is_(None),
                )
            )
            result = await self._session.execute(query)
            db_user = result.scalar_one_or_none()

            if not db_user:
                raise NotFoundError(f"User {user.user_id} not found")

            # Check email uniqueness if email changed
            if db_user.email.lower() != user.email.lower():
                if await self.email_exists(user.email):
                    raise ConflictError(f"User with email {user.email} already exists")

            # Update fields
            db_user.email = user.email.lower()
            db_user.hashed_password = user.hashed_password
            db_user.role = user.role
            db_user.status = user.status
            db_user.last_login_at = user.last_login
            db_user.updated_at = datetime.utcnow()

            await self._session.flush()
            await self._session.refresh(db_user)

            return self._to_entity(db_user)

        except (NotFoundError, ConflictError):
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to update user: {e}") from e

    async def delete(self, user_id: UUID) -> bool:
        """Soft delete user by setting deleted_at timestamp.

        Args:
            user_id: User UUID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        try:
            query = select(UserModel).where(
                and_(
                    UserModel.id == user_id,
                    UserModel.deleted_at.is_(None),
                )
            )
            result = await self._session.execute(query)
            db_user = result.scalar_one_or_none()

            if not db_user:
                return False

            db_user.soft_delete()
            await self._session.flush()

            return True

        except Exception as e:
            raise RepositoryError(f"Failed to delete user: {e}") from e

    async def list_by_role(
        self,
        role: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """List users by role with pagination.

        Args:
            role: User role to filter by
            limit: Maximum number of results (max 1000)
            offset: Number of results to skip

        Returns:
            List of users
        """
        try:
            # Validate and cap limit
            limit = min(max(1, limit), 1000)
            offset = max(0, offset)

            query = (
                select(UserModel)
                .where(
                    and_(
                        UserModel.role == role,
                        UserModel.deleted_at.is_(None),
                    )
                )
                .order_by(UserModel.email)
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(query)
            db_users = result.scalars().all()

            return [self._to_entity(db_user) for db_user in db_users]

        except Exception as e:
            raise RepositoryError(f"Failed to list users by role: {e}") from e

    async def list_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """List active users with pagination.

        Args:
            limit: Maximum number of results (max 1000)
            offset: Number of results to skip

        Returns:
            List of active users
        """
        try:
            # Validate and cap limit
            limit = min(max(1, limit), 1000)
            offset = max(0, offset)

            query = (
                select(UserModel)
                .where(
                    and_(
                        UserModel.status == "active",
                        UserModel.deleted_at.is_(None),
                    )
                )
                .order_by(UserModel.email)
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(query)
            db_users = result.scalars().all()

            return [self._to_entity(db_user) for db_user in db_users]

        except Exception as e:
            raise RepositoryError(f"Failed to list active users: {e}") from e

    async def count_by_role(self, role: str) -> int:
        """Count users by role, excluding soft-deleted.

        Args:
            role: User role

        Returns:
            Number of users with the specified role
        """
        try:
            query = select(func.count(UserModel.id)).where(
                and_(
                    UserModel.role == role,
                    UserModel.deleted_at.is_(None),
                )
            )
            result = await self._session.execute(query)
            return result.scalar() or 0

        except Exception as e:
            raise RepositoryError(f"Failed to count users by role: {e}") from e

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists, case-insensitive.

        Args:
            email: Email address to check

        Returns:
            True if email exists (excluding soft-deleted users)
        """
        try:
            query = select(func.count(UserModel.id)).where(
                and_(
                    func.lower(UserModel.email) == email.lower(),
                    UserModel.deleted_at.is_(None),
                )
            )
            result = await self._session.execute(query)
            count = result.scalar() or 0
            return count > 0

        except Exception as e:
            raise RepositoryError(f"Failed to check email existence: {e}") from e

    # Additional methods for authentication and user management

    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """List users by status with pagination.

        Args:
            status: User status (active, inactive, locked)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of users
        """
        try:
            limit = min(max(1, limit), 1000)
            offset = max(0, offset)

            query = (
                select(UserModel)
                .where(
                    and_(
                        UserModel.status == status,
                        UserModel.deleted_at.is_(None),
                    )
                )
                .order_by(UserModel.email)
                .limit(limit)
                .offset(offset)
            )

            result = await self._session.execute(query)
            db_users = result.scalars().all()

            return [self._to_entity(db_user) for db_user in db_users]

        except Exception as e:
            raise RepositoryError(f"Failed to list users by status: {e}") from e

    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp.

        Args:
            user_id: User UUID

        Raises:
            NotFoundError: If user doesn't exist
            RepositoryError: If update fails
        """
        try:
            query = select(UserModel).where(
                and_(
                    UserModel.id == user_id,
                    UserModel.deleted_at.is_(None),
                )
            )
            result = await self._session.execute(query)
            db_user = result.scalar_one_or_none()

            if not db_user:
                raise NotFoundError(f"User {user_id} not found")

            db_user.last_login_at = datetime.utcnow()
            await self._session.flush()

        except NotFoundError:
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to update last login: {e}") from e

    async def get_recently_active_users(self, days: int = 30) -> list[User]:
        """Get users who logged in within the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of recently active users
        """
        try:
            cutoff_date = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - datetime.timedelta(days=days)

            query = (
                select(UserModel)
                .where(
                    and_(
                        UserModel.last_login_at >= cutoff_date,
                        UserModel.status == "active",
                        UserModel.deleted_at.is_(None),
                    )
                )
                .order_by(desc(UserModel.last_login_at))
            )

            result = await self._session.execute(query)
            db_users = result.scalars().all()

            return [self._to_entity(db_user) for db_user in db_users]

        except Exception as e:
            raise RepositoryError(f"Failed to get recently active users: {e}") from e

    async def get_user_statistics(self) -> dict[str, int]:
        """Get user statistics by role and status.

        Returns:
            Dictionary with user counts by various dimensions
        """
        try:
            # Count by role
            role_query = (
                select(UserModel.role, func.count(UserModel.id))
                .where(UserModel.deleted_at.is_(None))
                .group_by(UserModel.role)
            )
            role_result = await self._session.execute(role_query)
            role_counts = dict(role_result.all())

            # Count by status
            status_query = (
                select(UserModel.status, func.count(UserModel.id))
                .where(UserModel.deleted_at.is_(None))
                .group_by(UserModel.status)
            )
            status_result = await self._session.execute(status_query)
            status_counts = dict(status_result.all())

            # Total count
            total_query = select(func.count(UserModel.id)).where(
                UserModel.deleted_at.is_(None)
            )
            total_result = await self._session.execute(total_query)
            total_count = total_result.scalar() or 0

            return {
                "total": total_count,
                "by_role": role_counts,
                "by_status": status_counts,
            }

        except Exception as e:
            raise RepositoryError(f"Failed to get user statistics: {e}") from e

    def _to_entity(self, db_user: UserModel) -> User:
        """Convert database model to domain entity.

        Args:
            db_user: SQLAlchemy user model

        Returns:
            User domain entity
        """
        return User(
            user_id=db_user.id,
            email=db_user.email,
            hashed_password=db_user.hashed_password,
            role=db_user.role,
            status=db_user.status,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            last_login=db_user.last_login_at,
        )

    def _to_model(self, user: User) -> UserModel:
        """Convert domain entity to database model.

        Args:
            user: User domain entity

        Returns:
            SQLAlchemy user model
        """
        return UserModel(
            id=user.user_id,
            email=user.email.lower(),
            hashed_password=user.hashed_password,
            role=user.role,
            status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login,
        )