"""Application Interfaces - Ports for dependency inversion."""

from src.application.interfaces.alert_repository import AlertRepository
from src.application.interfaces.audit_repository import AuditRepository
from src.application.interfaces.customer_repository import CustomerRepository
from src.application.interfaces.merchant_repository import MerchantRepository
from src.application.interfaces.transaction_repository import TransactionRepository
from src.application.interfaces.user_repository import UserRepository

__all__ = [
    "AlertRepository",
    "AuditRepository",
    "CustomerRepository",
    "MerchantRepository",
    "TransactionRepository",
    "UserRepository",
]
