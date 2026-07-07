"""User Use Cases (CQRS Pattern)."""

from uuid import UUID

from src.application.dtos.user_dtos import (
    AuthenticationResponse,
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    UpdateUserRequest,
    UserListRequest,
    UserResponse,
)
from src.application.exceptions.application_exceptions import (
    EntityNotFoundException,
)
from src.application.services.user_service import UserService
from src.domain.entities.user import User


class CreateUserUseCase:
    """Use case for creating a new user account."""

    def __init__(self, user_service: UserService) -> None:
        """Initialize use case.

        Args:
            user_service: User service instance
        """
        self._service = user_service

    async def execute(
        self,
        request: CreateUserRequest,
        created_by: UUID | None = None,
    ) -> UserResponse:
        """Execute create user use case.

        Args:
            request: Create user request DTO
            created_by: User performing the action

        Returns:
            User response DTO

        Raises:
            ValidationException: If validation fails
            ConflictException: If email already exists
        """
        user = await self._service.create_user(
            email=request.email,
            password=request.password,
            role=request.role,
            created_by=created_by,
        )

        return self._to_response(user)

    @staticmethod
    def _to_response(user: User) -> UserResponse:
        """Convert domain entity to response DTO."""
        return UserResponse(
            user_id=user.user_id,
            email=user.email,
            role=user.role,
            status=user.status,
            is_active=user.is_active,
            is_locked=user.is_locked,
            can_review_alerts=user.can_review_alerts,
            can_manage_models=user.can_manage_models,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class UpdateUserUseCase:
    """Use case for updating a user account."""

    def __init__(self, user_service: UserService) -> None:
        """Initialize use case.

        Args:
            user_service: User service instance
        """
        self._service = user_service

    async def execute(
        self,
        user_id: UUID,
        request: UpdateUserRequest,
        updated_by: UUID | None = None,
    ) -> UserResponse:
        """Execute update user use case.

        Args:
            user_id: User UUID
            request: Update user request DTO
            updated_by: User performing the action

        Returns:
            User response DTO

        Raises:
            EntityNotFoundException: If user not found
            ValidationException: If validation fails
        """
        updates = {}
        if request.role is not None:
            updates["role"] = request.role
        if request.status is not None:
            updates["status"] = request.status

        user = await self._service.update_user(
            user_id=user_id,
            updates=updates,
            updated_by=updated_by,
        )

        return CreateUserUseCase._to_response(user)


class DeleteUserUseCase:
    """Use case for deleting (soft delete) a user account."""

    def __init__(self, user_service: UserService) -> None:
        """Initialize use case.

        Args:
            user_service: User service instance
        """
        self._service = user_service

    async def execute(
        self,
        user_id: UUID,
        reason: str = "Account deletion requested",
        deleted_by: UUID | None = None,
    ) -> None:
        """Execute delete user use case.

        Args:
            user_id: User UUID
            reason: Reason for deletion
            deleted_by: User performing the action

        Raises:
            EntityNotFoundException: If user not found
        """
        await self._service.deactivate_user(
            user_id=user_id,
            reason=reason,
            deleted_by=deleted_by,
        )


class GetUserUseCase:
    """Use case for retrieving a user by ID."""

    def __init__(self, user_service: UserService) -> None:
        """Initialize use case.

        Args:
            user_service: User service instance
        """
        self._service = user_service

    async def execute(self, user_id: UUID) -> UserResponse:
        """Execute get user use case.

        Args:
            user_id: User UUID

        Returns:
            User response DTO

        Raises:
            EntityNotFoundException: If user not found
        """
        user = await self._service.get_user_by_id(user_id)
        if not user:
            raise EntityNotFoundException(f"User {user_id} not found")

        return CreateUserUseCase._to_response(user)


class ListUsersUseCase:
    """Use case for listing users with filtering."""

    def __init__(self, user_service: UserService) -> None:
        """Initialize use case.

        Args:
            user_service: User service instance
        """
        self._service = user_service

    async def execute(
        self,
        request: UserListRequest,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserResponse]:
        """Execute list users use case.

        Args:
            request: User list request with filters
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of user response DTOs
        """
        if request.role and request.status:
            # Filter by both role and status
            users = await self._service.get_users_by_role_and_status(
                role=request.role,
                status=request.status,
                limit=limit,
                offset=offset,
            )
        elif request.role:
            # Filter by role only
            users = await self._service.get_users_by_role(
                role=request.role,
                limit=limit,
                offset=offset,
            )
        elif request.status:
            # Filter by status only
            users = await self._service.get_users_by_status(
                status=request.status,
                limit=limit,
                offset=offset,
            )
        else:
            # No filters - get active users
            users = await self._service.get_active_users(
                limit=limit,
                offset=offset,
            )

        return [CreateUserUseCase._to_response(user) for user in users]


class AuthenticateUserUseCase:
    """Use case for user authentication."""

    def __init__(self, user_service: UserService) -> None:
        """Initialize use case.

        Args:
            user_service: User service instance
        """
        self._service = user_service

    async def execute(
        self,
        request: LoginRequest,
        ip_address: str | None = None,
    ) -> AuthenticationResponse:
        """Execute authenticate user use case.

        Args:
            request: Login request DTO
            ip_address: Client IP address

        Returns:
            Authentication response with token

        Raises:
            ValidationException: If credentials are invalid
        """
        result = await self._service.authenticate_user(
            email=request.email,
            password=request.password,
            ip_address=ip_address,
        )

        return AuthenticationResponse(
            access_token=result["access_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            user=CreateUserUseCase._to_response(result["user"]),
        )


class ChangePasswordUseCase:
    """Use case for changing user password."""

    def __init__(self, user_service: UserService) -> None:
        """Initialize use case.

        Args:
            user_service: User service instance
        """
        self._service = user_service

    async def execute(
        self,
        user_id: UUID,
        request: ChangePasswordRequest,
    ) -> None:
        """Execute change password use case.

        Args:
            user_id: User UUID
            request: Change password request DTO

        Raises:
            EntityNotFoundException: If user not found
            ValidationException: If current password is incorrect
        """
        await self._service.change_password(
            user_id=user_id,
            current_password=request.current_password,
            new_password=request.new_password,
        )


class GetUserStatisticsUseCase:
    """Use case for getting user statistics."""

    def __init__(self, user_service: UserService) -> None:
        """Initialize use case.

        Args:
            user_service: User service instance
        """
        self._service = user_service

    async def execute(self) -> dict[str, any]:
        """Execute get user statistics use case.

        Returns:
            Dictionary with user statistics
        """
        return await self._service.get_user_statistics()


class ActivateUserUseCase:
    """Use case for activating a user account."""

    def __init__(self, user_service: UserService) -> None:
        """Initialize use case.

        Args:
            user_service: User service instance
        """
        self._service = user_service

    async def execute(
        self,
        user_id: UUID,
        activated_by: UUID | None = None,
    ) -> UserResponse:
        """Execute activate user use case.

        Args:
            user_id: User UUID
            activated_by: User performing the action

        Returns:
            User response DTO

        Raises:
            EntityNotFoundException: If user not found
        """
        user = await self._service.activate_user(
            user_id=user_id,
            activated_by=activated_by,
        )

        return CreateUserUseCase._to_response(user)


class LockUserUseCase:
    """Use case for locking a user account."""

    def __init__(self, user_service: UserService) -> None:
        """Initialize use case.

        Args:
            user_service: User service instance
        """
        self._service = user_service

    async def execute(
        self,
        user_id: UUID,
        reason: str,
        locked_by: UUID | None = None,
    ) -> UserResponse:
        """Execute lock user use case.

        Args:
            user_id: User UUID
            reason: Reason for locking
            locked_by: User performing the action

        Returns:
            User response DTO

        Raises:
            EntityNotFoundException: If user not found
        """
        user = await self._service.lock_user(
            user_id=user_id,
            reason=reason,
            locked_by=locked_by,
        )

        return CreateUserUseCase._to_response(user)
