"""FastAPI Dependency Injection.

Provides dependency factories for services, repositories, and other
application components.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.alert_repository import AlertRepository
from src.application.interfaces.audit_repository import AuditRepository
from src.application.interfaces.customer_repository import CustomerRepository
from src.application.interfaces.merchant_repository import MerchantRepository
from src.application.interfaces.transaction_repository import TransactionRepository
from src.application.interfaces.user_repository import UserRepository
from src.application.services.alert_service import AlertService
from src.application.services.audit_service import AuditService
from src.application.services.customer_service import CustomerService
from src.application.services.merchant_service import MerchantService
from src.application.services.transaction_service import TransactionService
from src.application.services.user_service import UserService
from src.application.use_cases.alert_use_cases import (
    AssignAlertUseCase,
    CreateAlertUseCase,
    GetAlertUseCase,
    ListAlertsUseCase,
    ResolveAlertUseCase,
    UpdateAlertUseCase,
)
from src.application.use_cases.audit_use_cases import (
    CreateAuditLogUseCase,
    GetAuditLogUseCase,
    ListAuditLogsUseCase,
)
from src.application.use_cases.customer_use_cases import (
    CreateCustomerUseCase,
    DeleteCustomerUseCase,
    GetCustomerUseCase,
    UpdateCustomerUseCase,
)
from src.application.use_cases.merchant_use_cases import (
    CreateMerchantUseCase,
    DeleteMerchantUseCase,
    GetMerchantUseCase,
    ListMerchantsUseCase,
    SuspendMerchantUseCase,
    UpdateMerchantUseCase,
)
from src.application.use_cases.transaction_use_cases import (
    CreateTransactionUseCase,
    GetTransactionUseCase,
    SearchTransactionsUseCase,
    UpdateTransactionUseCase,
)
from src.application.use_cases.user_use_cases import (
    AuthenticateUserUseCase,
    ChangePasswordUseCase,
    CreateUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserUseCase,
)
from src.infrastructure.database.connection import get_async_session
from src.infrastructure.database.repositories.alert_repository_impl import AlertRepositoryImpl
from src.infrastructure.database.repositories.audit_repository_impl import AuditRepositoryImpl
from src.infrastructure.database.repositories.customer_repository_impl import CustomerRepositoryImpl
from src.infrastructure.database.repositories.merchant_repository_impl import MerchantRepositoryImpl
from src.infrastructure.database.repositories.transaction_repository_impl import (
    TransactionRepositoryImpl,
)
from src.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl


# Database Session Dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session.

    Yields:
        AsyncSession for database operations
    """
    async for session in get_async_session():
        yield session


# Repository Dependencies
def get_customer_repository(
    session: AsyncSession = Depends(get_db),
) -> CustomerRepository:
    """Get customer repository instance.

    Args:
        session: Database session

    Returns:
        Customer repository implementation
    """
    return CustomerRepositoryImpl(session)


def get_audit_repository(
    session: AsyncSession = Depends(get_db),
) -> AuditRepository:
    """Get audit repository instance.

    Args:
        session: Database session

    Returns:
        Audit repository implementation
    """
    return AuditRepositoryImpl(session)


def get_merchant_repository(
    session: AsyncSession = Depends(get_db),
) -> MerchantRepository:
    """Get merchant repository instance."""
    return MerchantRepositoryImpl(session)


def get_transaction_repository(
    session: AsyncSession = Depends(get_db),
) -> TransactionRepository:
    """Get transaction repository instance."""
    return TransactionRepositoryImpl(session)


def get_alert_repository(
    session: AsyncSession = Depends(get_db),
) -> AlertRepository:
    """Get alert repository instance."""
    return AlertRepositoryImpl(session)


def get_user_repository(
    session: AsyncSession = Depends(get_db),
) -> UserRepository:
    """Get user repository instance."""
    return UserRepositoryImpl(session)


async def get_database_health_status() -> bool:
    """Check whether the database is reachable for readiness probes."""
    async for session in get_async_session():
        try:
            await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
    return False


# Service Dependencies
def get_customer_service(
    customer_repo: CustomerRepository = Depends(get_customer_repository),
    audit_repo: AuditRepository = Depends(get_audit_repository),
) -> CustomerService:
    """Get customer service instance.

    Args:
        customer_repo: Customer repository
        audit_repo: Audit repository

    Returns:
        Customer service instance
    """
    return CustomerService(
        customer_repository=customer_repo,
        audit_repository=audit_repo,
    )


# Use Case Dependencies
def get_create_customer_use_case(
    service: CustomerService = Depends(get_customer_service),
) -> CreateCustomerUseCase:
    """Get create customer use case.

    Args:
        service: Customer service

    Returns:
        Create customer use case instance
    """
    return CreateCustomerUseCase(service)


def get_update_customer_use_case(
    service: CustomerService = Depends(get_customer_service),
) -> UpdateCustomerUseCase:
    """Get update customer use case.

    Args:
        service: Customer service

    Returns:
        Update customer use case instance
    """
    return UpdateCustomerUseCase(service)


def get_delete_customer_use_case(
    service: CustomerService = Depends(get_customer_service),
) -> DeleteCustomerUseCase:
    """Get delete customer use case.

    Args:
        service: Customer service

    Returns:
        Delete customer use case instance
    """
    return DeleteCustomerUseCase(service)


def get_get_customer_use_case(
    service: CustomerService = Depends(get_customer_service),
) -> GetCustomerUseCase:
    """Get customer use case.

    Args:
        service: Customer service

    Returns:
        Get customer use case instance
    """
    return GetCustomerUseCase(service)


def get_merchant_service(
    merchant_repo: MerchantRepository = Depends(get_merchant_repository),
    audit_repo: AuditRepository = Depends(get_audit_repository),
) -> MerchantService:
    """Get merchant service instance."""
    return MerchantService(merchant_repository=merchant_repo, audit_repository=audit_repo)


def get_transaction_service(
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
    customer_repo: CustomerRepository = Depends(get_customer_repository),
    merchant_repo: MerchantRepository = Depends(get_merchant_repository),
    audit_repo: AuditRepository = Depends(get_audit_repository),
) -> TransactionService:
    """Get transaction service instance."""
    return TransactionService(
        transaction_repository=transaction_repo,
        customer_repository=customer_repo,
        merchant_repository=merchant_repo,
        audit_repository=audit_repo,
    )


def get_alert_service(
    alert_repo: AlertRepository = Depends(get_alert_repository),
    audit_repo: AuditRepository = Depends(get_audit_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> AlertService:
    """Get alert service instance."""
    return AlertService(
        alert_repository=alert_repo,
        audit_repository=audit_repo,
        user_repository=user_repo,
    )


def get_audit_service(
    audit_repo: AuditRepository = Depends(get_audit_repository),
) -> AuditService:
    """Get audit service instance."""
    return AuditService(audit_repository=audit_repo)


def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
    audit_repo: AuditRepository = Depends(get_audit_repository),
) -> UserService:
    """Get user service instance."""
    return UserService(user_repository=user_repo, audit_repository=audit_repo)


def get_create_merchant_use_case(
    service: MerchantService = Depends(get_merchant_service),
) -> CreateMerchantUseCase:
    """Get create merchant use case."""
    return CreateMerchantUseCase(service)


def get_update_merchant_use_case(
    service: MerchantService = Depends(get_merchant_service),
) -> UpdateMerchantUseCase:
    """Get update merchant use case."""
    return UpdateMerchantUseCase(service)


def get_delete_merchant_use_case(
    service: MerchantService = Depends(get_merchant_service),
) -> DeleteMerchantUseCase:
    """Get delete merchant use case."""
    return DeleteMerchantUseCase(service)


def get_get_merchant_use_case(
    service: MerchantService = Depends(get_merchant_service),
) -> GetMerchantUseCase:
    """Get merchant use case."""
    return GetMerchantUseCase(service)


def get_list_merchants_use_case(
    service: MerchantService = Depends(get_merchant_service),
) -> ListMerchantsUseCase:
    """Get list merchants use case."""
    return ListMerchantsUseCase(service)


def get_suspend_merchant_use_case(
    service: MerchantService = Depends(get_merchant_service),
) -> SuspendMerchantUseCase:
    """Get suspend merchant use case."""
    return SuspendMerchantUseCase(service)


def get_create_transaction_use_case(
    service: TransactionService = Depends(get_transaction_service),
) -> CreateTransactionUseCase:
    """Get create transaction use case."""
    return CreateTransactionUseCase(service)


def get_update_transaction_use_case(
    service: TransactionService = Depends(get_transaction_service),
) -> UpdateTransactionUseCase:
    """Get update transaction use case."""
    return UpdateTransactionUseCase(service)


def get_get_transaction_use_case(
    service: TransactionService = Depends(get_transaction_service),
) -> GetTransactionUseCase:
    """Get transaction use case."""
    return GetTransactionUseCase(service)


def get_search_transactions_use_case(
    service: TransactionService = Depends(get_transaction_service),
) -> SearchTransactionsUseCase:
    """Get search transactions use case."""
    return SearchTransactionsUseCase(service)


def get_create_alert_use_case(
    service: AlertService = Depends(get_alert_service),
) -> CreateAlertUseCase:
    """Get create alert use case."""
    return CreateAlertUseCase(service)


def get_update_alert_use_case(
    service: AlertService = Depends(get_alert_service),
) -> UpdateAlertUseCase:
    """Get update alert use case."""
    return UpdateAlertUseCase(service)


def get_get_alert_use_case(
    service: AlertService = Depends(get_alert_service),
) -> GetAlertUseCase:
    """Get alert use case."""
    return GetAlertUseCase(service)


def get_list_alerts_use_case(
    service: AlertService = Depends(get_alert_service),
) -> ListAlertsUseCase:
    """Get list alerts use case."""
    return ListAlertsUseCase(service)


def get_assign_alert_use_case(
    service: AlertService = Depends(get_alert_service),
) -> AssignAlertUseCase:
    """Get assign alert use case."""
    return AssignAlertUseCase(service)


def get_resolve_alert_use_case(
    service: AlertService = Depends(get_alert_service),
) -> ResolveAlertUseCase:
    """Get resolve alert use case."""
    return ResolveAlertUseCase(service)


def get_create_audit_log_use_case(
    service: AuditService = Depends(get_audit_service),
) -> CreateAuditLogUseCase:
    """Get create audit log use case."""
    return CreateAuditLogUseCase(service)


def get_get_audit_log_use_case(
    service: AuditService = Depends(get_audit_service),
) -> GetAuditLogUseCase:
    """Get audit log use case."""
    return GetAuditLogUseCase(service)


def get_list_audit_logs_use_case(
    service: AuditService = Depends(get_audit_service),
) -> ListAuditLogsUseCase:
    """Get list audit logs use case."""
    return ListAuditLogsUseCase(service)


def get_create_user_use_case(
    service: UserService = Depends(get_user_service),
) -> CreateUserUseCase:
    """Get create user use case."""
    return CreateUserUseCase(service)


def get_update_user_use_case(
    service: UserService = Depends(get_user_service),
) -> UpdateUserUseCase:
    """Get update user use case."""
    return UpdateUserUseCase(service)


def get_get_user_use_case(
    service: UserService = Depends(get_user_service),
) -> GetUserUseCase:
    """Get user use case."""
    return GetUserUseCase(service)


def get_list_users_use_case(
    service: UserService = Depends(get_user_service),
) -> ListUsersUseCase:
    """Get list users use case."""
    return ListUsersUseCase(service)


def get_authenticate_user_use_case(
    service: UserService = Depends(get_user_service),
) -> AuthenticateUserUseCase:
    """Get authenticate user use case."""
    return AuthenticateUserUseCase(service)


def get_change_password_use_case(
    service: UserService = Depends(get_user_service),
) -> ChangePasswordUseCase:
    """Get change password use case."""
    return ChangePasswordUseCase(service)
