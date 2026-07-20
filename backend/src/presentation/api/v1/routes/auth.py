"""Authentication API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field

from src.application.interfaces.user_repository import UserRepository
from src.domain.entities.user import User
from src.infrastructure.security.dependencies import (
    get_current_active_user,
    get_user_repository,
)
from src.infrastructure.security.jwt import (
    TokenPair,
    create_token_pair,
    decode_token,
    verify_token_type,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request payload."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class RefreshTokenRequest(BaseModel):
    """Refresh token request payload."""

    refresh_token: str = Field(..., description="Refresh token")


class UserResponse(BaseModel):
    """User information response."""

    user_id: str
    email: str
    role: str
    status: str


class LoginResponse(BaseModel):
    """Login response with tokens and user info."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user and return JWT tokens",
)
async def login(
    request: LoginRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> LoginResponse:
    """Authenticate user and return JWT tokens.

    Args:
        request: Login credentials
        user_repo: User repository

    Returns:
        JWT tokens and user information

    Raises:
        HTTPException: If authentication fails
    """
    # Get user by email
    user = await user_repo.get_by_email(request.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not user.verify_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )

    # Record login
    user.record_login()
    await user_repo.update(user)

    # Create JWT tokens
    tokens = create_token_pair(
        user_id=str(user.user_id),
        email=user.email,
        role=user.role,
    )

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user=UserResponse(
            user_id=str(user.user_id),
            email=user.email,
            role=user.role,
            status=user.status,
        ),
    )


@router.post(
    "/refresh",
    response_model=TokenPair,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Get new access token using refresh token",
)
async def refresh_token(
    request: RefreshTokenRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> TokenPair:
    """Refresh access token using refresh token.

    Args:
        request: Refresh token
        user_repo: User repository

    Returns:
        New token pair

    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Decode refresh token
        token_data = decode_token(request.refresh_token)

        # Verify it's a refresh token
        verify_token_type(token_data, "refresh")

        # Verify user still exists and is active
        user = await user_repo.get_by_email(token_data.email)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Create new token pair
        tokens = create_token_pair(
            user_id=str(user.user_id),
            email=user.email,
            role=user.role,
        )

        return tokens

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
        ) from e


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User logout",
    description="Logout user (client-side token removal)",
)
async def logout() -> None:
    """Logout user.

    Note: This is a client-side operation. The client should remove
    the JWT tokens from storage. Tokens will expire naturally.

    For production, consider implementing a token blacklist in Redis.
    """
    # In a stateless JWT system, logout is handled client-side
    # The client removes the token from storage
    # For enhanced security, implement token blacklist in Redis
    return None


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get authenticated user information",
)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """Get current authenticated user information.

    Args:
        current_user: Current authenticated user

    Returns:
        User information
    """
    return UserResponse(
        user_id=str(current_user.user_id),
        email=current_user.email,
        role=current_user.role,
        status=current_user.status,
    )
