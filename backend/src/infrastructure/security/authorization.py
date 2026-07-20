"""Role-based authorization dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from src.domain.entities.user import User
from src.infrastructure.security.dependencies import get_current_active_user


class RequireAuthenticated:
    """Dependency that requires authenticated user."""

    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        """Verify user is authenticated and active.

        Args:
            current_user: Current authenticated user

        Returns:
            Authenticated user

        Raises:
            HTTPException: If user is not authenticated
        """
        return current_user


class RequireAdmin:
    """Dependency that requires admin role."""

    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        """Verify user has admin role.

        Args:
            current_user: Current authenticated user

        Returns:
            Admin user

        Raises:
            HTTPException: If user is not admin
        """
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return current_user


class RequireAnalyst:
    """Dependency that requires analyst or admin role."""

    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        """Verify user can review alerts (analyst or admin).

        Args:
            current_user: Current authenticated user

        Returns:
            Analyst or admin user

        Raises:
            HTTPException: If user cannot review alerts
        """
        if not current_user.can_review_alerts:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Analyst or admin access required",
            )
        return current_user


class RequireDataScientist:
    """Dependency that requires data scientist or admin role."""

    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        """Verify user can manage models (data scientist or admin).

        Args:
            current_user: Current authenticated user

        Returns:
            Data scientist or admin user

        Raises:
            HTTPException: If user cannot manage models
        """
        if not current_user.can_manage_models:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Data scientist or admin access required",
            )
        return current_user


class RequireRole:
    """Dependency that requires specific role(s)."""

    def __init__(self, allowed_roles: list[str]):
        """Initialize with allowed roles.

        Args:
            allowed_roles: List of role names that are allowed
        """
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        """Verify user has one of the allowed roles.

        Args:
            current_user: Current authenticated user

        Returns:
            User with allowed role

        Raises:
            HTTPException: If user doesn't have required role
        """
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(self.allowed_roles)}",
            )
        return current_user


# Create reusable dependency instances
require_authenticated = RequireAuthenticated()
require_admin = RequireAdmin()
require_analyst = RequireAnalyst()
require_data_scientist = RequireDataScientist()
