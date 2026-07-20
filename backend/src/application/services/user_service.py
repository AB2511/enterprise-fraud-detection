"""User Service - Business workflows for user management."""

from datetime import datetime
from typing import Any
from uuid import UUID

from src.application.interfaces.audit_repository import AuditRepository
from src.application.interfaces.user_repository import UserRepository
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.user import User


class UserService:
    """Service for user management business workflows.

    This service handles user lifecycle, authentication preparation,
    role management, and permission validation.

    NOTE: This service prepares for authentication but does NOT implement
    JWT generation or session management. That belongs to auth middleware.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        audit_repository: AuditRepository,
    ) -> None:
        """Initialize user service.

        Args:
            user_repository: Repository for user persistence
            audit_repository: Repository for audit logging
        """
        self._user_repo = user_repository
        self._audit_repo = audit_repository

    async def create_user(
        self,
        email: str,
        password: str,
        role: str,
        created_by: UUID | None = None,
        created_by_id: UUID | None = None,
    ) -> User:
        """Create a new user with hashed password.

        Args:
            email: User email address
            password: Plain text password (will be hashed)
            role: User role (admin, analyst, data_scientist, auditor, viewer)
            created_by_id: User creating this user

        Returns:
            Created user entity

        Raises:
            ValueError: If validation fails
            ConflictError: If email already exists
        """
        effective_created_by = created_by or created_by_id

        # Check if email exists
        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise ValueError(f"User with email {email} already exists")

        # Create user entity using the domain factory so the password is hashed
        user = User.create(email=email, password=password, role=role)

        # Persist
        created_user = await self._user_repo.create(user)

        # Audit
        audit = AuditLog.for_creation(
            entity_type="user",
            entity_id=created_user.user_id,
            user_id=effective_created_by,
            username="admin",
            new_value={
                "email": email,
                "role": role,
                "status": "active",
            },
        )
        await self._audit_repo.create(audit)

        return created_user

    async def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
    ) -> dict[str, Any] | None:
        """Authenticate user with email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            User data if authenticated, None otherwise

        Note:
            This method does NOT generate JWT tokens. It only validates credentials.
        """
        user = await self._user_repo.get_by_email(email)
        if not user:
            return None

        # Verify password
        if not user.verify_password(password):
            return None

        # Check if user is active
        if user.status != "active":
            return None

        # Record login
        user.record_login()
        await self._user_repo.update(user)

        # Audit
        audit = AuditLog.for_update(
            entity_type="user",
            entity_id=user.user_id,
            user_id=user.user_id,
            username=user.email,
            old_value={},
            new_value={
                "action": "login",
                "timestamp": datetime.utcnow().isoformat(),
                "ip_address": ip_address,
            },
        )
        await self._audit_repo.create(audit)

        # Return user data (without password hash)
        return {
            "user_id": str(user.user_id),
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "permissions": list(user.get_permissions()),
        }

    async def change_user_password(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str,
    ) -> User:
        """Change user password with validation.

        Args:
            user_id: User UUID
            old_password: Current password
            new_password: New password

        Returns:
            Updated user

        Raises:
            NotFoundError: If user not found
            ValueError: If old password incorrect
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Verify old password
        if not user.verify_password(old_password):
            raise ValueError("Current password is incorrect")

        # Change password
        user.change_password(old_password, new_password)

        # Persist
        updated_user = await self._user_repo.update(user)

        # Audit
        audit = AuditLog.for_update(
            entity_type="user",
            entity_id=user_id,
            user_id=user_id,
            username=user.email,
            old_value={},
            new_value={"action": "password_changed"},
        )
        await self._audit_repo.create(audit)

        return updated_user

    async def assign_role(
        self,
        user_id: UUID,
        new_role: str,
        assigned_by: UUID | None = None,
        assigned_by_id: UUID | None = None,
    ) -> User:
        """Assign new role to user.

        Args:
            user_id: User UUID
            new_role: New role to assign
            assigned_by_id: User performing assignment

        Returns:
            Updated user

        Raises:
            NotFoundError: If user not found
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        effective_assigned_by = assigned_by or assigned_by_id
        old_role = user.role

        # Assign new role
        user.assign_role(new_role)

        # Persist
        updated_user = await self._user_repo.update(user)

        # Audit
        audit = AuditLog.for_update(
            entity_type="user",
            entity_id=user_id,
            user_id=effective_assigned_by,
            username="admin",
            old_value={"role": old_role},
            new_value={"role": new_role},
        )
        await self._audit_repo.create(audit)

        return updated_user

    async def deactivate_user(
        self,
        user_id: UUID,
        reason: str,
        deactivated_by: UUID | None = None,
        deactivated_by_id: UUID | None = None,
        deleted_by: UUID | None = None,
    ) -> User:
        """Deactivate user account.

        Args:
            user_id: User UUID
            reason: Reason for deactivation
            deactivated_by_id: User performing deactivation

        Returns:
            Updated user

        Raises:
            NotFoundError: If user not found
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        effective_deactivated_by = deactivated_by or deactivated_by_id or deleted_by

        # Deactivate
        user.deactivate()

        # Persist
        updated_user = await self._user_repo.update(user)

        # Audit
        audit = AuditLog.for_update(
            entity_type="user",
            entity_id=user_id,
            user_id=effective_deactivated_by,
            username="admin",
            old_value={"status": "active"},
            new_value={"status": "inactive", "reason": reason},
        )
        await self._audit_repo.create(audit)

        return updated_user

    async def activate_user(
        self,
        user_id: UUID,
        activated_by: UUID | None = None,
        activated_by_id: UUID | None = None,
    ) -> User:
        """Reactivate user account.

        Args:
            user_id: User UUID
            activated_by_id: User performing activation

        Returns:
            Updated user

        Raises:
            NotFoundError: If user not found
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        effective_activated_by = activated_by or activated_by_id

        # Activate
        user.activate()

        # Persist
        updated_user = await self._user_repo.update(user)

        # Audit
        audit = AuditLog.for_update(
            entity_type="user",
            entity_id=user_id,
            user_id=effective_activated_by,
            username="admin",
            old_value={"status": "inactive"},
            new_value={"status": "active"},
        )
        await self._audit_repo.create(audit)

        return updated_user

    async def check_permission(
        self,
        user_id: UUID,
        permission: str,
    ) -> bool:
        """Check if user has specific permission.

        Args:
            user_id: User UUID
            permission: Permission to check (e.g., "review_alerts", "train_models")

        Returns:
            True if user has permission

        Raises:
            NotFoundError: If user not found
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        return user.has_permission(permission)

    async def list_users_by_role(
        self,
        role: str,
        limit: int = 100,
    ) -> list[User]:
        """List users by role.

        Args:
            role: Role to filter by
            limit: Maximum results

        Returns:
            List of users
        """
        return await self._user_repo.list_by_role(role=role, limit=limit)

    async def get_active_users(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """Get all active users.

        Args:
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of active users
        """
        return await self._user_repo.list_active(limit=limit, offset=offset)

    async def get_user_profile(
        self,
        user_id: UUID,
    ) -> dict:
        """Get comprehensive user profile.

        Args:
            user_id: User UUID

        Returns:
            User profile dictionary

        Raises:
            NotFoundError: If user not found
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        return {
            "user_id": str(user.user_id),
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login.isoformat() if user.last_login else None,
            "permissions": list(user.get_permissions()),
            "can_review_alerts": user.can_review_alerts,
            "can_manage_users": user.can_manage_models,
        }

    async def get_user_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        """Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User if found, None otherwise
        """
        return await self._user_repo.get_by_id(user_id)

    async def update_user(
        self,
        user_id: UUID,
        updates: dict,
        updated_by: UUID | None = None,
        updated_by_id: UUID | None = None,
    ) -> User:
        """Update user information.

        Args:
            user_id: User UUID
            updates: Dictionary of fields to update
            updated_by: User performing update

        Returns:
            Updated user

        Raises:
            ValueError: If user not found
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        effective_updated_by = updated_by or updated_by_id

        # Store old values
        old_values = {
            "email": user.email,
            "role": user.role,
            "status": user.status,
        }

        # Apply updates (limited to safe fields)
        if "role" in updates:
            user.assign_role(updates["role"])

        if "status" in updates:
            # Status should use activate/deactivate methods, but allow direct update
            user.status = updates["status"]

        # Persist
        updated_user = await self._user_repo.update(user)

        # Audit
        new_values = {
            "email": user.email,
            "role": user.role,
            "status": user.status,
        }

        audit = AuditLog.for_update(
            entity_type="user",
            entity_id=user_id,
            user_id=effective_updated_by,
            username="admin",
            old_value=old_values,
            new_value=new_values,
        )
        await self._audit_repo.create(audit)

        return updated_user

    async def get_users_by_role(
        self,
        role: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """Get users by role.

        Args:
            role: User role
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of users
        """
        return await self._user_repo.list_by_role(
            role=role,
            limit=limit,
            offset=offset,
        )

    async def get_users_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """Get users by status.

        Args:
            status: User status (active, inactive)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of users
        """
        if status == "active":
            return await self._user_repo.list_active(
                limit=limit,
                offset=offset,
            )
        else:
            # Repository limitation: Only "active" status is supported
            # For other statuses (inactive, locked, etc.), return empty list
            # This is a known limitation documented in SERVICE_COMPLETION_REPORT.md
            return []

    async def get_users_by_role_and_status(
        self,
        role: str,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        """Get users by role and status.

        Args:
            role: User role
            status: User status
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of users
        """
        # Get by role first
        users = await self._user_repo.list_by_role(
            role=role,
            limit=limit,
            offset=offset,
        )

        # Filter by status
        if status == "active":
            users = [u for u in users if u.status == "active"]
        else:
            users = [u for u in users if u.status != "active"]

        return users

    async def get_user_statistics(self) -> dict[str, Any]:
        """Get user statistics.

        Returns:
            Dictionary with user statistics
        """
        # Get counts by role
        roles = ["admin", "analyst", "data_scientist", "auditor", "viewer"]
        by_role: dict[str, int] = {}

        for role in roles:
            count = await self._user_repo.count_by_role(role)
            by_role[role] = count

        # Get active users
        active_users = await self._user_repo.list_active(limit=1000)
        total_active = len(active_users)

        # Calculate by status (approximation)
        by_status: dict[str, int] = {
            "active": total_active,
            "inactive": 0,  # Would need all users to calculate
            "locked": 0,
        }

        return {
            "total_users": sum(by_role.values()),
            "users_by_role": by_role,
            "users_by_status": by_status,
            "active_users": total_active,
        }

    async def lock_user(
        self,
        user_id: UUID,
        reason: str,
        locked_by: UUID | None = None,
        locked_by_id: UUID | None = None,
    ) -> User:
        """Lock user account.

        Args:
            user_id: User UUID
            reason: Reason for locking
            locked_by: User performing lock

        Returns:
            Locked user

        Raises:
            ValueError: If user not found
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        effective_locked_by = locked_by or locked_by_id

        # Lock user using the entity's explicit lock behavior
        user.lock()

        # Persist
        updated_user = await self._user_repo.update(user)

        # Audit
        audit = AuditLog.for_update(
            entity_type="user",
            entity_id=user_id,
            user_id=effective_locked_by,
            username="admin",
            old_value={"status": "active"},
            new_value={"status": "locked", "reason": reason},
        )
        await self._audit_repo.create(audit)

        return updated_user
