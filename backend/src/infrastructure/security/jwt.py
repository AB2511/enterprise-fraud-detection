"""JWT token generation and validation."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

from jose import JWTError, jwt
from pydantic import BaseModel

from src.config.settings import get_settings


class TokenData(BaseModel):
    """Token payload data."""

    user_id: str
    email: str
    role: str
    token_type: str  # "access" or "refresh"


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT access token.

    Args:
        user_id: User UUID
        email: User email
        role: User role
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    expire = datetime.now(UTC) + expires_delta

    to_encode: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return cast(str, encoded_jwt)


def create_refresh_token(
    user_id: str,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT refresh token.

    Args:
        user_id: User UUID
        email: User email
        role: User role
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expire_days)

    expire = datetime.now(UTC) + expires_delta

    to_encode: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return cast(str, encoded_jwt)


def create_token_pair(user_id: str, email: str, role: str) -> TokenPair:
    """Create access and refresh token pair.

    Args:
        user_id: User UUID
        email: User email
        role: User role

    Returns:
        TokenPair with access and refresh tokens
    """
    settings = get_settings()

    access_token = create_access_token(user_id, email, role)
    refresh_token = create_refresh_token(user_id, email, role)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenData with user information

    Raises:
        JWTError: If token is invalid or expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")
        token_type: str = payload.get("type")

        if not user_id or not email or not role or not token_type:
            raise JWTError("Invalid token payload")

        return TokenData(
            user_id=user_id,
            email=email,
            role=role,
            token_type=token_type,
        )

    except JWTError as e:
        raise JWTError(f"Could not validate token: {str(e)}") from e


def verify_token_type(token_data: TokenData, expected_type: str) -> None:
    """Verify token is of expected type.

    Args:
        token_data: Decoded token data
        expected_type: Expected token type ("access" or "refresh")

    Raises:
        JWTError: If token type doesn't match
    """
    if token_data.token_type != expected_type:
        raise JWTError(f"Invalid token type. Expected {expected_type}, got {token_data.token_type}")
