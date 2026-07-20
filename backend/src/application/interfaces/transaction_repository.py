"""Transaction Repository Interface (Port)."""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.entities.transaction import Transaction


class TransactionRepository(ABC):
    """Interface for transaction persistence operations.

    This is a port in hexagonal architecture - the infrastructure layer
    will provide the concrete implementation (adapter).
    """

    @abstractmethod
    async def create(self, transaction: Transaction) -> Transaction:
        """Persist a transaction.

        Args:
            transaction: Transaction entity to save

        Returns:
            Saved transaction with any generated fields populated
        """
        pass

    @abstractmethod
    async def update(self, transaction: Transaction) -> Transaction:
        """Update an existing transaction."""
        pass

    @abstractmethod
    async def search(
        self,
        *,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        currency: str | None = None,
        transaction_type: str | None = None,
        payment_channel: str | None = None,
        payment_method: str | None = None,
        status: str | None = None,
        is_fraud: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """Search transactions with filters."""
        pass

    @abstractmethod
    async def list_recent(self, *, limit: int = 100, offset: int = 0) -> list[Transaction]:
        """List recent transactions."""
        pass

    @abstractmethod
    async def list_by_customer(
        self,
        *,
        customer_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        """List transactions for a customer."""
        pass

    @abstractmethod
    async def list_by_merchant(
        self,
        *,
        merchant_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        """List transactions for a merchant."""
        pass

    @abstractmethod
    async def list_by_date_range(
        self,
        *,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        """List transactions within a date range."""
        pass

    @abstractmethod
    async def get_by_id(self, transaction_id: UUID) -> Transaction | None:
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
        start_date: datetime | None = None,
        end_date: datetime | None = None,
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
