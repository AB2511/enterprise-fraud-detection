"""Integration tests for authentication API endpoints."""

from httpx import AsyncClient
import pytest

from src.domain.entities.user import User


@pytest.mark.asyncio
class TestAuthenticationAPI:
    """Test authentication endpoints."""

    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful login."""
        response = await client.post(
            "/v1/auth/login",
            json={
                "email": "auth_test@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "user" in data
        assert data["user"]["email"] == "auth_test@example.com"
        assert data["user"]["role"] == "analyst"

    async def test_login_invalid_email(self, client: AsyncClient):
        """Test login with non-existent email."""
        response = await client.post(
            "/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    async def test_login_invalid_password(self, client: AsyncClient, test_user: User):
        """Test login with incorrect password."""
        response = await client.post(
            "/v1/auth/login",
            json={
                "email": "auth_test@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    async def test_login_inactive_user(self, client: AsyncClient, async_session):
        """Test login with inactive user account."""
        from src.infrastructure.database.repositories.user_repository_impl import (
            UserRepositoryImpl,
        )

        repo = UserRepositoryImpl(async_session)

        # Create inactive user
        user = User.create(
            email="inactive_test@example.com",
            password="testpassword123",
            role="analyst",
        )
        user.deactivate()

        await repo.create(user)
        await async_session.commit()

        response = await client.post(
            "/v1/auth/login",
            json={
                "email": "inactive_test@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 403
        assert "not active" in response.json()["detail"]

        # Cleanup
        await repo.delete(user.user_id)
        await async_session.commit()

    async def test_get_current_user(self, client: AsyncClient, test_user: User):
        """Test getting current user information."""
        # First login to get token
        login_response = await client.post(
            "/v1/auth/login",
            json={
                "email": "auth_test@example.com",
                "password": "testpassword123",
            },
        )

        token = login_response.json()["access_token"]

        # Get current user
        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == "auth_test@example.com"
        assert data["role"] == "analyst"
        assert data["status"] == "active"

    async def test_get_current_user_no_token(self, client: AsyncClient):
        """Test getting current user without token."""
        response = await client.get("/v1/auth/me")

        assert response.status_code == 403

    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token."""
        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401

    async def test_refresh_token(self, client: AsyncClient, test_user: User):
        """Test refreshing access token."""
        # First login to get refresh token
        login_response = await client.post(
            "/v1/auth/login",
            json={
                "email": "auth_test@example.com",
                "password": "testpassword123",
            },
        )

        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = await client.post(
            "/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_with_access_token_fails(
        self, client: AsyncClient, test_user: User
    ):
        """Test that using access token for refresh fails."""
        # Login to get access token
        login_response = await client.post(
            "/v1/auth/login",
            json={
                "email": "auth_test@example.com",
                "password": "testpassword123",
            },
        )

        access_token = login_response.json()["access_token"]

        # Try to refresh with access token (should fail)
        response = await client.post(
            "/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401
        assert "Invalid token type" in response.json()["detail"]

    async def test_logout(self, client: AsyncClient):
        """Test logout endpoint."""
        response = await client.post("/v1/auth/logout")

        assert response.status_code == 204
