from decimal import Decimal
from uuid import UUID

import pytest

from src.application.services.merchant_service import MerchantService
from src.domain.entities.merchant import Merchant


class FakeAuditRepository:
    async def create(self, audit_log):
        return None


class FakeMerchantRepository:
    def __init__(self, merchant: Merchant) -> None:
        self._merchant = merchant

    async def create(self, merchant: Merchant) -> Merchant:
        return merchant

    async def get_by_id(self, merchant_id: UUID) -> Merchant | None:
        return self._merchant

    async def update(self, merchant: Merchant) -> Merchant:
        self._merchant = merchant
        return merchant

    async def get_by_name(self, merchant_name: str) -> Merchant | None:
        return self._merchant

    async def delete(self, merchant_id: UUID) -> bool:
        return True

    async def list_by_mcc(self, mcc: str, limit: int = 100, offset: int = 0) -> list[Merchant]:
        return [self._merchant]

    async def list_by_risk_level(
        self,
        min_risk: int,
        max_risk: int,
        limit: int = 100,
    ) -> list[Merchant]:
        return [self._merchant]

    async def list_high_risk(self, limit: int = 100) -> list[Merchant]:
        return [self._merchant]

    async def get_by_country(self, country: str, limit: int = 100, offset: int = 0) -> list[Merchant]:
        return [self._merchant]


@pytest.mark.asyncio
async def test_reactivate_merchant_accepts_reason_argument() -> None:
    merchant = Merchant(
        merchant_name="Example Merchant",
        mcc="5411",
        merchant_category="Grocery",
        country="USA",
    )
    merchant.is_active = False
    merchant.historical_fraud_rate = Decimal("5.0")

    service = MerchantService(FakeMerchantRepository(merchant), FakeAuditRepository())

    reactivated = await service.reactivate_merchant(
        merchant_id=merchant.merchant_id,
        reason="Suspension review completed",
        user_id=None,
    )

    assert reactivated.is_active is True
