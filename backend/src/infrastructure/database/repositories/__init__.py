"""Repository Implementations.

This package contains concrete implementations of repository interfaces
using SQLAlchemy for database persistence.

All repositories provide:
- Full CRUD operations with proper error handling
- Pagination and filtering support
- Soft delete capabilities (where applicable)
- Bulk operations and optimistic locking
- Comprehensive business validation
- Async/await patterns throughout
"""

from .alert_repository_impl import AlertRepositoryImpl
from .audit_repository_impl import AuditRepositoryImpl
from .customer_repository_impl import CustomerRepositoryImpl
from .merchant_repository_impl import MerchantRepositoryImpl
from .model_repository_impl import ModelRepositoryImpl
from .prediction_repository_impl import PredictionRepositoryImpl
from .transaction_repository_impl import TransactionRepositoryImpl
from .user_repository_impl import UserRepositoryImpl

__all__ = [
    "AlertRepositoryImpl",
    "AuditRepositoryImpl",
    "CustomerRepositoryImpl",
    "MerchantRepositoryImpl",
    "ModelRepositoryImpl",
    "PredictionRepositoryImpl",
    "TransactionRepositoryImpl",
    "UserRepositoryImpl",
]
