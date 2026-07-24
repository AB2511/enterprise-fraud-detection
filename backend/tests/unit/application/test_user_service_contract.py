from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID, uuid4

from src.application.interfaces.audit_repository import AuditRepository
from src.application.interfaces.user_repository import UserRepository
from src.application.services.user_service import UserService
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.user import User


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.created: list[User] = []

    async def create(self, user: User) -> User:
        user.user_id = user.user_id or uuid4()
        self.users[str(user.user_id)] = user
        self.created.append(user)
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(str(user_id))

    async def get_by_email(self, email: str) -> User | None:
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    async def update(self, user: User) -> User:
        self.users[str(user.user_id)] = user
        return user

    async def delete(self, user_id: UUID) -> bool:
        return False

    async def list_by_role(self, role: str, limit: int = 100, offset: int = 0) -> list[User]:
        return [u for u in self.users.values() if u.role == role]

    async def list_active(self, limit: int = 100, offset: int = 0) -> list[User]:
        return [u for u in self.users.values() if u.status == "active"]

    async def count_by_role(self, role: str) -> int:
        return sum(1 for u in self.users.values() if u.role == role)

    async def email_exists(self, email: str) -> bool:
        return any(u.email == email for u in self.users.values())


class FakeAuditRepository(AuditRepository):
    def __init__(self) -> None:
        self.entries: list[AuditLog] = []

    async def create(self, audit_log: AuditLog) -> AuditLog:
        self.entries.append(audit_log)
        return audit_log

    async def get_by_id(self, log_id: UUID) -> AuditLog | None:
        return None

    async def list_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        return []

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        return []

    async def list_by_action(
        self,
        action: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        return []

    async def list_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[AuditLog]:
        return []

    async def search(
        self,
        entity_type: str | None = None,
        action: str | None = None,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        return []

    async def count_by_entity(self, entity_type: str, entity_id: UUID) -> int:
        return 0


def test_create_user_accepts_created_by_keyword_and_persists_entity() -> None:
    user_repo = FakeUserRepository()
    audit_repo = FakeAuditRepository()
    service = UserService(user_repo, audit_repo)

    created_by = uuid4()

    async def run_test() -> None:
        user = await service.create_user(
            email="analyst@example.com",
            password="SecurePass123!",
            role="analyst",
            created_by=created_by,
        )

        assert user.user_id is not None
        assert user.email == "analyst@example.com"
        assert user.hashed_password != "SecurePass123!"
        assert len(audit_repo.entries) == 1

    asyncio.run(run_test())


def test_change_password_uses_expected_entity_contract() -> None:
    user_repo = FakeUserRepository()
    audit_repo = FakeAuditRepository()
    service = UserService(user_repo, audit_repo)

    async def run_test() -> None:
        created_user = await service.create_user(
            email="analyst2@example.com",
            password="SecurePass123!",
            role="analyst",
        )

        updated_user = await service.change_user_password(
            user_id=created_user.user_id,
            old_password="SecurePass123!",
            new_password="NewSecurePass456!",
        )

        assert updated_user.hashed_password != created_user.hashed_password
        assert updated_user.verify_password("NewSecurePass456!") is True

    asyncio.run(run_test())
