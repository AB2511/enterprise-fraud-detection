"""Tests for JWT token generation and validation."""

from datetime import UTC, datetime, timedelta

import pytest
from jose import JWTError

from src.infrastructure.security.jwt import (
    TokenData,
    TokenPair,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    verify_token_type,
)


class TestJWTTokens:
    """Test JWT token generation and decoding."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "analyst"

        token = create_access_token(user_id, email, role)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "analyst"

        token = create_refresh_token(user_id, email, role)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_pair(self):
        """Test token pair creation."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "admin"

        tokens = create_token_pair(user_id, email, role)

        assert isinstance(tokens, TokenPair)
        assert isinstance(tokens.access_token, str)
        assert isinstance(tokens.refresh_token, str)
        assert tokens.token_type == "bearer"
        assert tokens.expires_in > 0

    def test_decode_valid_access_token(self):
        """Test decoding valid access token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "analyst"

        token = create_access_token(user_id, email, role)
        token_data = decode_token(token)

        assert isinstance(token_data, TokenData)
        assert token_data.user_id == user_id
        assert token_data.email == email
        assert token_data.role == role
        assert token_data.token_type == "access"

    def test_decode_valid_refresh_token(self):
        """Test decoding valid refresh token."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "admin@example.com"
        role = "admin"

        token = create_refresh_token(user_id, email, role)
        token_data = decode_token(token)

        assert isinstance(token_data, TokenData)
        assert token_data.user_id == user_id
        assert token_data.email == email
        assert token_data.role == role
        assert token_data.token_type == "refresh"

    def test_decode_expired_token(self):
        """Test decoding expired token raises error."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "analyst"

        # Create token that expires immediately
        token = create_access_token(
            user_id, email, role, expires_delta=timedelta(seconds=-1)
        )

        with pytest.raises(JWTError):
            decode_token(token)

    def test_decode_invalid_token(self):
        """Test decoding invalid token raises error."""
        with pytest.raises(JWTError):
            decode_token("invalid.token.here")

    def test_verify_correct_token_type(self):
        """Test verifying correct token type."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "analyst"

        access_token = create_access_token(user_id, email, role)
        token_data = decode_token(access_token)

        # Should not raise error
        verify_token_type(token_data, "access")

    def test_verify_incorrect_token_type(self):
        """Test verifying incorrect token type raises error."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "analyst"

        access_token = create_access_token(user_id, email, role)
        token_data = decode_token(access_token)

        with pytest.raises(JWTError, match="Invalid token type"):
            verify_token_type(token_data, "refresh")

    def test_token_contains_required_claims(self):
        """Test that token contains all required claims."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "data_scientist"

        token = create_access_token(user_id, email, role)
        token_data = decode_token(token)

        assert token_data.user_id is not None
        assert token_data.email is not None
        assert token_data.role is not None
        assert token_data.token_type is not None

    def test_different_tokens_for_same_user(self):
        """Test that creating tokens at different times produces different tokens."""
        import time
        
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"
        role = "analyst"

        token1 = create_access_token(user_id, email, role)
        time.sleep(1)  # Wait 1 second to ensure different iat timestamp
        token2 = create_access_token(user_id, email, role)

        # Tokens should be different (due to different iat timestamps)
        assert token1 != token2
