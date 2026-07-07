"""Integration tests for UserRepositoryImpl."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.user import User
from src.domain.exceptions.base import ConflictError, NotFoundError
from src.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl


class TestUserRepositoryImpl:
    """Test suite for UserRepositoryImpl."""

    @pytest.fixture
    async def repository(self, async_session: AsyncSession) -> UserRepositoryImpl:
        """Create repository instance."""
        return UserRepositoryImpl(async_session)

    @pytest.fixture
    def sample_user(self) -> User:
        """Create sample user entity."""
        return User.create(
            email="analyst@company.com",
            password="SecurePass123!",
            role="analyst"
        )

    async def test_create_user(self, repository: UserRepositoryImpl, sample_user: User):
        """Test user creation."""
        # Act
        created = await repository.create(sample_user)

        # Assert
        assert created.user_id is not None
        assert created.email == "analyst@company.com"
        assert created.role == "analyst"
        assert created.status == "active"
        assert created.hashed_password is not None
        assert created.hashed_password != "SecurePass123!"  # Password should be hashed

    async def test_create_duplicate_email_fails(self, repository: UserRepositoryImpl):
        """Test that creating user with duplicate email fails."""
        # Arrange
        user1 = User.create("test@company.com", "password1", "analyst")
        user2 = User.create("test@company.com", "password2", "admin")

        # Act
        await repository.create(user1)

        # Assert
        with pytest.raises(ConflictError):
            await repository.create(user2)

    async def test_get_by_id(self, repository: UserRepositoryImpl, sample_user: User):
        """Test retrieving user by ID."""
        # Arrange
        created = await repository.create(sample_user)

        # Act
        retrieved = await repository.get_by_id(created.user_id)

        # Assert
        assert retrieved is not None
        assert retrieved.user_id == created.user_id
        assert retrieved.email == "analyst@company.com"

    async def test_get_by_id_not_found(self, repository: UserRepositoryImpl):
        """Test retrieving non-existent user returns None."""
        # Act
        result = await repository.get_by_id(uuid4())

        # Assert
        assert result is None

    async def test_get_by_email(self, repository: UserRepositoryImpl, sample_user: User):
        """Test retrieving user by email."""
        # Arrange
        await repository.create(sample_user)

        # Act
        retrieved = await repository.get_by_email("analyst@company.com")

        # Assert
        assert retrieved is not None
        assert retrieved.email == "analyst@company.com"

    async def test_get_by_email_case_insensitive(self, repository: UserRepositoryImpl, sample_user: User):
        """Test email lookup is case insensitive."""
        # Arrange
        await repository.create(sample_user)

        # Act
        retrieved = await repository.get_by_email("ANALYST@COMPANY.COM")

        # Assert
        assert retrieved is not None
        assert retrieved.email == "analyst@company.com"

    async def test_update_user(self, repository: UserRepositoryImpl, sample_user: User):
        """Test updating user."""
        # Arrange
        created = await repository.create(sample_user)
        created.role = "admin"
        created.status = "inactive"

        # Act
        updated = await repository.update(created)

        # Assert
        assert updated.role == "admin"
        assert updated.status == "inactive"
        assert updated.updated_at > updated.created_at

    async def test_update_nonexistent_user_fails(self, repository: UserRepositoryImpl):
        """Test updating non-existent user fails."""
        # Arrange
        user = User.create("test@company.com", "password", "analyst")
        user.user_id = uuid4()

        # Act & Assert
        with pytest.raises(NotFoundError):
            await repository.update(user)

    async def test_delete_user_soft_delete(self, repository: UserRepositoryImpl, sample_user: User):
        """Test soft delete functionality."""
        # Arrange
        created = await repository.create(sample_user)

        # Act
        result = await repository.delete(created.user_id)

        # Assert
        assert result is True

        # Verify soft delete - should not be retrievable
        retrieved = await repository.get_by_id(created.user_id)
        assert retrieved is None

    async def test_delete_nonexistent_user(self, repository: UserRepositoryImpl):
        """Test deleting non-existent user returns False."""
        # Act
        result = await repository.delete(uuid4())

        # Assert
        assert result is False

    async def test_list_by_role(self, repository: UserRepositoryImpl):
        """Test listing users by role."""
        # Arrange
        analyst1 = User.create("analyst1@company.com", "pass1", "analyst")
        analyst2 = User.create("analyst2@company.com", "pass2", "analyst")
        admin = User.create("admin@company.com", "pass3", "admin")

        await repository.create(analyst1)
        await repository.create(analyst2)
        await repository.create(admin)

        # Act
        analysts = await repository.list_by_role("analyst")

        # Assert
        assert len(analysts) == 2
        for user in analysts:
            assert user.role == "analyst"

    async def test_list_active(self, repository: UserRepositoryImpl):
        """Test listing active users."""
        # Arrange
        active_user = User.create("active@company.com", "pass1", "analyst")
        inactive_user = User.create("inactive@company.com", "pass2", "analyst")
        inactive_user.deactivate()

        await repository.create(active_user)
        await repository.create(inactive_user)

        # Act
        active_users = await repository.list_active()

        # Assert
        assert len(active_users) == 1
        assert active_users[0].email == "active@company.com"

    async def test_count_by_role(self, repository: UserRepositoryImpl):
        """Test counting users by role."""
        # Arrange
        for i in range(3):
            user = User.create(f"analyst{i}@company.com", f"pass{i}", "analyst")
            await repository.create(user)

        # Act
        count = await repository.count_by_role("analyst")

        # Assert
        assert count == 3

    async def test_email_exists(self, repository: UserRepositoryImpl, sample_user: User):
        """Test email existence check."""
        # Arrange
        await repository.create(sample_user)

        # Act & Assert
        assert await repository.email_exists("analyst@company.com") is True
        assert await repository.email_exists("nonexistent@company.com") is False

    async def test_list_by_status(self, repository: UserRepositoryImpl):
        """Test listing users by status."""
        # Arrange
        active_user = User.create("active@company.com", "pass1", "analyst")
        locked_user = User.create("locked@company.com", "pass2", "analyst")
        locked_user.lock()

        await repository.create(active_user)
        await repository.create(locked_user)

        # Act
        locked_users = await repository.list_by_status("locked", limit=10, offset=0)

        # Assert
        assert len(locked_users) == 1
        assert locked_users[0].status == "locked"

    async def test_update_last_login(self, repository: UserRepositoryImpl, sample_user: User):
        """Test updating last login timestamp."""
        # Arrange
        created = await repository.create(sample_user)
        original_last_login = created.last_login

        # Act
        await repository.update_last_login(created.user_id)

        # Verify update
        updated = await repository.get_by_id(created.user_id)
        assert updated.last_login is not None
        assert updated.last_login != original_last_login

    async def test_get_recently_active_users(self, repository: UserRepositoryImpl):
        """Test getting recently active users."""
        # Arrange
        recent_user = User.create("recent@company.com", "pass1", "analyst")
        old_user = User.create("old@company.com", "pass2", "analyst")

        created_recent = await repository.create(recent_user)
        created_old = await repository.create(old_user)

        # Update login times
        await repository.update_last_login(created_recent.user_id)

        # Act
        recent_users = await repository.get_recently_active_users(days=30)

        # Assert
        assert len(recent_users) >= 1
        user_emails = [u.email for u in recent_users]
        assert "recent@company.com" in user_emails

    async def test_get_user_statistics(self, repository: UserRepositoryImpl):
        """Test getting user statistics."""
        # Arrange
        analyst = User.create("analyst@company.com", "pass1", "analyst")
        admin = User.create("admin@company.com", "pass2", "admin")
        locked_user = User.create("locked@company.com", "pass3", "analyst")
        locked_user.lock()

        await repository.create(analyst)
        await repository.create(admin)
        await repository.create(locked_user)

        # Act
        stats = await repository.get_user_statistics()

        # Assert
        assert stats["total"] >= 3
        assert "by_role" in stats
        assert "by_status" in stats
        assert stats["by_role"]["analyst"] >= 2
        assert stats["by_role"]["admin"] >= 1

    async def test_pagination_parameters(self, repository: UserRepositoryImpl):
        """Test pagination limits and offsets."""
        # Arrange
        for i in range(5):
            user = User.create(f"user{i}@company.com", f"pass{i}", "analyst")
            await repository.create(user)

        # Act
        page1 = await repository.list_by_role("analyst", limit=2, offset=0)
        page2 = await repository.list_by_role("analyst", limit=2, offset=2)

        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].user_id != page2[0].user_id

    async def test_password_security(self, repository: UserRepositoryImpl):
        """Test password hashing and verification."""
        # Arrange
        original_password = "TestPassword123!"
        user = User.create("test@company.com", original_password, "analyst")

        # Act
        created = await repository.create(user)

        # Assert
        assert created.hashed_password != original_password
        assert created.verify_password(original_password) is True
        assert created.verify_password("WrongPassword") is False

    async def test_concurrent_email_creation(self, repository: UserRepositoryImpl):
        """Test handling concurrent email creation attempts."""
        # Arrange
        user1 = User.create("concurrent@company.com", "pass1", "analyst")
        user2 = User.create("concurrent@company.com", "pass2", "admin")

        # Act
        created1 = await repository.create(user1)

        # Assert - Second creation should fail
        with pytest.raises(ConflictError):
            await repository.create(user2)

        # Verify first user exists
        retrieved = await repository.get_by_email("concurrent@company.com")
        assert retrieved.user_id == created1.user_id

    async def test_role_validation(self, repository: UserRepositoryImpl):
        """Test role validation in repository operations."""
        # Valid roles should work
        valid_user = User.create("valid@company.com", "pass", "data_scientist")
        created = await repository.create(valid_user)
        assert created.role == "data_scientist"

    async def test_search_edge_cases(self, repository: UserRepositoryImpl):
        """Test edge cases in search operations."""
        # Test empty results
        empty_result = await repository.list_by_role("nonexistent_role")
        assert empty_result == []

        # Test limit boundaries
        zero_limit = await repository.list_active(limit=0)
        assert len(zero_limit) == 0

        # Test large offset
        large_offset = await repository.list_active(offset=1000)
        assert large_offset == []

    async def test_soft_delete_excludes_from_searches(self, repository: UserRepositoryImpl, sample_user: User):
        """Test that soft-deleted users are excluded from searches."""
        # Arrange
        created = await repository.create(sample_user)

        # Verify user appears in searches before deletion
        by_email = await repository.get_by_email(created.email)
        assert by_email is not None

        by_role = await repository.list_by_role(created.role)
        user_ids = [u.user_id for u in by_role]
        assert created.user_id in user_ids

        # Act - Soft delete
        await repository.delete(created.user_id)

        # Assert - User should not appear in any searches
        by_email_after = await repository.get_by_email(created.email)
        assert by_email_after is None

        by_role_after = await repository.list_by_role(created.role)
        user_ids_after = [u.user_id for u in by_role_after]
        assert created.user_id not in user_ids_after
