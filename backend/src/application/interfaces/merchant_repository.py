"""Merchant Repository Interface."""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.domain.entities.merchant import Merchant


class MerchantRepository(ABC):
    """Repository interface for Merchant entity."""

    @abstractmethod
    async def create(self, merchant: Merchant) -> Merchant:
        """Create a new merchant.

        Args:
            merchant: Merchant entity to create

        Returns:
            Created merchant with generated ID

        Raises:
            RepositoryError: If creation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, merchant_id: UUID) -> Optional[Merchant]:
        """Retrieve merchant by ID.

        Args:
            merchant_id: Merchant UUID

        Returns:
            Merchant if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_name(self, merchant_name: str) -> Optional[Merchant]:
        """Retrieve merchant by name.

        Args:
            merchant_name: Merchant business name

        Returns:
            Merchant if found, None otherwise
        """
        pass

    @abstractmethod
    async def update(self, merchant: Merchant) -> Merchant:
        """Update existing merchant.

        Args:
            merchant: Merchant entity with updated data

        Returns:
            Updated merchant

        Raises:
            RepositoryError: If update fails
            NotFoundError: If merchant doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, merchant_id: UUID) -> bool:
        """Soft delete merchant.

        Args:
            merchant_id: Merchant UUID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        pass

    @abstractmethod
    async def list_by_mcc(
        self,
        mcc: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Merchant]:
        """List merchants by MCC code.

        Args:
            mcc: Merchant category code
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of merchants
        """
        pass

    @abstractmethod
    async def list_by_risk_level(
        self,
        min_risk: int,
        max_risk: int,
        limit: int = 100,
    ) -> list[Merchant]:
        """List merchants by risk rating range.

        Args:
            min_risk: Minimum risk rating (0-100)
            max_risk: Maximum risk rating (0-100)
            limit: Maximum number of results

        Returns:
            List of merchants
        """
        pass

    @abstractmethod
    async def list_high_risk(self, limit: int = 100) -> list[Merchant]:
        """List high-risk merchants (rating >= 70).

        Args:
            limit: Maximum number of results

        Returns:
            List of high-risk merchants
        """
        pass

    @abstractmethod
    async def get_by_country(
        self,
        country: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Merchant]:
        """List merchants by country.

        Args:
            country: Country code
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of merchants
        """
        pass
