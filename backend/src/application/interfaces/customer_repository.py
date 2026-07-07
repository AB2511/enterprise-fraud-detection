"""Customer Repository Interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.customer import Customer


class CustomerRepository(ABC):
    """Repository interface for Customer entity.

    Defines persistence operations for customer data without
    exposing database implementation details.
    """

    @abstractmethod
    async def create(self, customer: Customer) -> Customer:
        """Create a new customer.

        Args:
            customer: Customer entity to create

        Returns:
            Created customer with generated ID

        Raises:
            RepositoryError: If creation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        """Retrieve customer by ID.

        Args:
            customer_id: Customer UUID

        Returns:
            Customer if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Customer | None:
        """Retrieve customer by email.

        Args:
            email: Customer email address

        Returns:
            Customer if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, customer: Customer) -> Customer:
        """Update existing customer.

        Args:
            customer: Customer entity with updated data

        Returns:
            Updated customer

        Raises:
            RepositoryError: If update fails
            NotFoundError: If customer doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, customer_id: UUID) -> bool:
        """Soft delete customer.

        Args:
            customer_id: Customer UUID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        pass

    @abstractmethod
    async def list_by_risk_category(
        self,
        risk_category: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Customer]:
        """List customers by risk category.

        Args:
            risk_category: Risk category to filter by
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of customers
        """
        pass

    @abstractmethod
    async def list_by_kyc_status(
        self,
        kyc_status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Customer]:
        """List customers by KYC status.

        Args:
            kyc_status: KYC status to filter by
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of customers
        """
        pass

    @abstractmethod
    async def count_by_risk_category(self, risk_category: str) -> int:
        """Count customers in risk category.

        Args:
            risk_category: Risk category to count

        Returns:
            Number of customers
        """
        pass

    @abstractmethod
    async def list_high_risk(self, limit: int = 100) -> list[Customer]:
        """List high and critical risk customers.

        Args:
            limit: Maximum number of results

        Returns:
            List of high-risk customers
        """
        pass

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        pass
