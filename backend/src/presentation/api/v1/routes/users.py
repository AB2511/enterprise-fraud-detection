"""User API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.application.dtos.user_dtos import (
    AuthenticationResponse,
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
    UpdateUserRequest,
    UserListRequest,
    UserResponse,
)
from src.application.use_cases.user_use_cases import (
    AuthenticateUserUseCase,
    ChangePasswordUseCase,
    CreateUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserUseCase,
)
from src.config.logging_config import get_logger
from src.domain.entities.user import User
from src.infrastructure.security.authorization import require_admin
from src.presentation.api.dependencies import (
    get_authenticate_user_use_case,
    get_change_password_use_case,
    get_create_user_use_case,
    get_get_user_use_case,
    get_list_users_use_case,
    get_update_user_use_case,
)
from src.presentation.api.response import APIResponse, success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
)
async def create_user(
    request: CreateUserRequest,
    current_user: Annotated[User, Depends(require_admin)],
    use_case: CreateUserUseCase = Depends(get_create_user_use_case),
) -> APIResponse[UserResponse]:
    """Create a user."""
    user = await use_case.execute(request)
    return success_response(data=user, message="User created successfully")


@router.get(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
)
async def get_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_admin)],
    use_case: GetUserUseCase = Depends(get_get_user_use_case),
) -> APIResponse[UserResponse]:
    """Retrieve a user by identifier."""
    user = await use_case.execute(user_id)
    return success_response(data=user, message="User retrieved successfully")


@router.get(
    "",
    response_model=APIResponse[list[UserResponse]],
    status_code=status.HTTP_200_OK,
    summary="List users",
)
async def list_users(
    current_user: Annotated[User, Depends(require_admin)],
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=1000),
    use_case: ListUsersUseCase = Depends(get_list_users_use_case),
) -> APIResponse[list[UserResponse]]:
    """List users with optional filters."""
    request = UserListRequest(role=role, status=status)
    result = await use_case.execute(request, limit=page_size, offset=(page - 1) * page_size)
    return success_response(data=result, message="Users retrieved successfully")


@router.put(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Update user",
)
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    current_user: Annotated[User, Depends(require_admin)],
    use_case: UpdateUserUseCase = Depends(get_update_user_use_case),
) -> APIResponse[UserResponse]:
    """Update a user."""
    user = await use_case.execute(user_id, request)
    return success_response(data=user, message="User updated successfully")


@router.post(
    "/login",
    response_model=APIResponse[AuthenticationResponse],
    status_code=status.HTTP_200_OK,
    summary="Authenticate user",
)
async def login(
    request: LoginRequest,
    use_case: AuthenticateUserUseCase = Depends(get_authenticate_user_use_case),
) -> APIResponse[AuthenticationResponse]:
    """Authenticate a user."""
    auth = await use_case.execute(request)
    return success_response(data=auth, message="Authentication successful")


@router.post(
    "/{user_id}/change-password",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Change password",
)
async def change_password(
    user_id: UUID,
    request: ChangePasswordRequest,
    current_user: Annotated[User, Depends(require_admin)],
    use_case: ChangePasswordUseCase = Depends(get_change_password_use_case),
) -> APIResponse[UserResponse]:
    """Change a user's password."""
    user = await use_case.execute(user_id, request)
    return success_response(data=user, message="Password changed successfully")
