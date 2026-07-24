"""FastAPI dependencies for authentication."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.user_repository import UserRepository
from src.domain.entities.user import User
from src.infrastructure.database.connection import get_async_session
from src.infrastructure.database.repositories.user_repository_impl import (
    UserRepositoryImpl,
)
from src.infrastructure.security.jwt import decode_token, verify_token_type

# HTTP Bearer scheme for extracting JWT from Authorization header
security = HTTPBearer()


async def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserRepository:
    """Get user repository instance.

    Args:
        session: Database session

    Returns:
        UserRepository implementation
    """
    return UserRepositoryImpl(session)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    """Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials (JWT token)
        user_repo: User repository

    Returns:
        Authenticated User entity

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode token
        token_data = decode_token(credentials.credentials)

        # Verify it's an access token
        verify_token_type(token_data, "access")

        # Get user from database
        user_id = UUID(token_data.user_id)
        user = await user_repo.get_by_id(user_id)

        if user is None:
            raise credentials_exception

        return user

    except (JWTError, ValueError) as e:
        raise credentials_exception from e


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current authenticated and active user.

    Args:
        current_user: Current authenticated user

    Returns:
        Active User entity

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return current_user
