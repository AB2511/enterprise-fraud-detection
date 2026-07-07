"""Transaction Repository Interface (Port)."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.domain.entities.transaction import Transaction


class TransactionRepository(ABC):
    """Interface for transaction persistence operations.

    This is a port in hexagonal architecture - the infrastructure layer
    will provide the concrete implementation (adapter).
    """

    @abstractmethod
    async def save(self, transaction: Transaction) -> Transaction:
        """Persist a transaction.

        Args:
            transaction: Transaction entity to save

        Returns:
            Saved transaction with any generated fields populated
        """
        pass

    @abstractmethod
    async def get_by_id(self, transaction_id: UUID) -> Optional[Transaction]:
        """Retrieve transaction by ID.

        Args:
            transaction_id: Unique identifier

        Returns:
            Transaction if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_user(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Transaction]:
        """Get transactions for a specific user.

        Args:
            user_id: User identifier
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of transactions to return

        Returns:
            List of transactions
        """
        pass

    @abstractmethod
    async def count_recent_transactions(
        self,
        user_id: str,
        minutes: int,
    ) -> int:
        """Count recent transactions for a user (for velocity features).

        Args:
            user_id: User identifier
            minutes: Time window in minutes

        Returns:
            Count of transactions in time window
        """
        pass

    @abstractmethod
    async def delete(self, transaction_id: UUID) -> bool:
        """Delete a transaction (soft delete).

        Args:
            transaction_id: Unique identifier

        Returns:
            True if deleted, False if not found
        """
        pass
