"""FastAPI Dependency Injection.

Provides dependency factories for services, repositories, and other
application components.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.audit_repository import AuditRepository
from src.application.interfaces.customer_repository import CustomerRepository
from src.application.services.customer_service import CustomerService
from src.application.use_cases.customer_use_cases import (
    CreateCustomerUseCase,
    DeleteCustomerUseCase,
    GetCustomerUseCase,
    UpdateCustomerUseCase,
)
from src.infrastructure.database.connection import get_async_session
from src.infrastructure.database.repositories.audit_repository_impl import AuditRepositoryImpl
from src.infrastructure.database.repositories.customer_repository_impl import CustomerRepositoryImpl


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
