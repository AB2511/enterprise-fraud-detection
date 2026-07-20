"""Transaction Service - Business workflows for transaction management."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from src.application.interfaces.audit_repository import AuditRepository
from src.application.interfaces.customer_repository import CustomerRepository
from src.application.interfaces.merchant_repository import MerchantRepository
from src.application.interfaces.transaction_repository import TransactionRepository
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.transaction import Transaction


class TransactionSearchCriteria(TypedDict, total=False):
    """Typed filters for transaction search."""

    customer_id: UUID
    merchant_id: UUID
    min_amount: Decimal
    max_amount: Decimal
    currency: str
    transaction_type: str
    payment_channel: str
    payment_method: str
    status: str
    is_fraud: bool
    start_date: datetime
    end_date: datetime


class TransactionService:
    """Service for transaction management business workflows.

    This service handles transaction validation, creation, updates,
    history retrieval, velocity calculation, and feature preparation.
    """

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        customer_repository: CustomerRepository,
        merchant_repository: MerchantRepository,
        audit_repository: AuditRepository,
    ) -> None:
        """Initialize transaction service.

        Args:
            transaction_repository: Repository for transaction persistence
            customer_repository: Repository for customer data
            merchant_repository: Repository for merchant data
            audit_repository: Repository for audit logging
        """
        self._transaction_repo = transaction_repository
        self._customer_repo = customer_repository
        self._merchant_repo = merchant_repository
        self._audit_repo = audit_repository

    async def validate_transaction(
        self,
        customer_id: UUID,
        merchant_id: UUID,
        amount: Decimal,
        currency: str,
    ) -> dict[str, object]:
        """Validate transaction eligibility.

        Args:
            customer_id: Customer UUID
            merchant_id: Merchant UUID
            amount: Transaction amount
            currency: Currency code

        Returns:
            Validation result with eligible flag and reasons

        Raises:
            NotFoundError: If customer or merchant not found
        """
        customer = await self._customer_repo.get_by_id(customer_id)
        if not customer:
            return {"eligible": False, "reason": "Customer not found"}

        merchant = await self._merchant_repo.get_by_id(merchant_id)
        if not merchant:
            return {"eligible": False, "reason": "Merchant not found"}

        # Check customer eligibility
        if not customer.can_transact:
            return {
                "eligible": False,
                "reason": f"Customer cannot transact: kyc={customer.kyc_status}, status={customer.is_active}, risk={customer.customer_risk_category}",
            }

        # Check merchant status
        if not merchant.is_active:
            return {"eligible": False, "reason": "Merchant is suspended"}

        # Check amount
        if amount <= Decimal("0"):
            return {"eligible": False, "reason": "Amount must be positive"}

        return {
            "eligible": True,
            "customer_risk": customer.customer_risk_category,
            "merchant_risk": merchant.get_risk_level(),
        }

    async def create_transaction(
        self,
        customer_id: UUID,
        merchant_id: UUID,
        amount: Decimal,
        currency: str,
        transaction_type: str = "purchase",
        payment_channel: str = "online",
        payment_method: str = "credit_card",
        device_id: str | None = None,
        ip_address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        user_id: UUID | None = None,
    ) -> Transaction:
        """Create a new transaction.

        Args:
            customer_id: Customer UUID
            merchant_id: Merchant UUID
            amount: Transaction amount
            currency: Currency code
            transaction_type: Type of transaction
            payment_channel: Payment channel
            payment_method: Payment method
            device_id: Device identifier
            ip_address: IP address
            latitude: Geolocation latitude
            longitude: Geolocation longitude
            user_id: User creating transaction

        Returns:
            Created transaction

        Raises:
            ValueError: If validation fails
        """
        # Validate transaction
        validation = await self.validate_transaction(customer_id, merchant_id, amount, currency)
        if not validation["eligible"]:
            raise ValueError(f"Transaction validation failed: {validation['reason']}")

        # Calculate velocity
        velocity = await self.calculate_velocity(customer_id)

        # Create transaction entity
        transaction = Transaction(
            customer_id=customer_id,
            merchant_id=merchant_id,
            amount=amount,
            currency=currency,
            transaction_type=transaction_type,
            payment_channel=payment_channel,
            payment_method=payment_method,
            device_id=device_id,
            ip_address=ip_address,
            latitude=latitude,
            longitude=longitude,
            velocity_1h=velocity["velocity_1h"],
            velocity_24h=velocity["velocity_24h"],
            velocity_7d=velocity["velocity_7d"],
        )

        # Persist transaction
        created_transaction = await self._transaction_repo.create(transaction)

        # Audit
        audit = AuditLog.for_creation(
            entity_type="transaction",
            entity_id=created_transaction.transaction_id,
            user_id=user_id,
            username="system",
            new_value={
                "customer_id": str(customer_id),
                "merchant_id": str(merchant_id),
                "amount": float(amount),
                "currency": currency,
                "type": transaction_type,
            },
        )
        await self._audit_repo.create(audit)

        return created_transaction

    async def update_transaction(
        self,
        transaction_id: UUID,
        updates: dict[str, object],
        user_id: UUID | None = None,
    ) -> Transaction:
        """Update transaction information.

        Args:
            transaction_id: Transaction UUID
            updates: Dictionary of fields to update
            user_id: User performing update

        Returns:
            Updated transaction

        Raises:
            NotFoundError: If transaction not found
        """
        transaction = await self._transaction_repo.get_by_id(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")

        # Store old values
        old_values = {
            "status": transaction.status,
            "is_fraud": transaction.is_fraud,
        }

        # Apply updates
        if "status" in updates and isinstance(updates["status"], str):
            transaction.status = updates["status"]
        if "is_fraud" in updates and isinstance(updates["is_fraud"], bool) and updates["is_fraud"]:
            transaction.mark_as_fraud()

        transaction.updated_at = datetime.utcnow()

        # Persist
        updated_transaction = await self._transaction_repo.update(transaction)

        # Audit
        new_values = {
            "status": transaction.status,
            "is_fraud": transaction.is_fraud,
        }

        audit = AuditLog.for_update(
            entity_type="transaction",
            entity_id=transaction_id,
            user_id=user_id,
            username="system",
            old_value=old_values,
            new_value=new_values,
        )
        await self._audit_repo.create(audit)

        return updated_transaction

    async def get_transaction_history(
        self,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        """Get transaction history with filters.

        Args:
            customer_id: Filter by customer
            merchant_id: Filter by merchant
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of transactions
        """
        if customer_id:
            return await self._transaction_repo.list_by_customer(
                customer_id=customer_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset,
            )
        elif merchant_id:
            return await self._transaction_repo.list_by_merchant(
                merchant_id=merchant_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset,
            )
        else:
            # Get all transactions in date range
            if start_date and end_date:
                return await self._transaction_repo.list_by_date_range(
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    offset=offset,
                )
            else:
                # Get recent transactions
                return await self._transaction_repo.list_recent(
                    limit=limit,
                    offset=offset,
                )

    async def search_transactions(
        self,
        criteria: TransactionSearchCriteria,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """Search transactions with multiple criteria.

        Args:
            search_criteria: Dictionary of search parameters
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of matching transactions
        """
        customer_id = criteria["customer_id"] if "customer_id" in criteria else None
        merchant_id = criteria["merchant_id"] if "merchant_id" in criteria else None
        min_amount = criteria["min_amount"] if "min_amount" in criteria else None
        max_amount = criteria["max_amount"] if "max_amount" in criteria else None
        currency = criteria["currency"] if "currency" in criteria else None
        transaction_type = criteria["transaction_type"] if "transaction_type" in criteria else None
        payment_channel = criteria["payment_channel"] if "payment_channel" in criteria else None
        payment_method = criteria["payment_method"] if "payment_method" in criteria else None
        status = criteria["status"] if "status" in criteria else None
        is_fraud = criteria["is_fraud"] if "is_fraud" in criteria else None
        start_date = criteria["start_date"] if "start_date" in criteria else None
        end_date = criteria["end_date"] if "end_date" in criteria else None

        return await self._transaction_repo.search(
            customer_id=customer_id,
            merchant_id=merchant_id,
            min_amount=min_amount,
            max_amount=max_amount,
            currency=currency,
            transaction_type=transaction_type,
            payment_channel=payment_channel,
            payment_method=payment_method,
            status=status,
            is_fraud=is_fraud,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

    async def calculate_velocity(
        self,
        customer_id: UUID,
    ) -> dict[str, int]:
        """Calculate transaction velocity metrics for customer.

        Args:
            customer_id: Customer UUID

        Returns:
            Dictionary with velocity metrics
        """
        now = datetime.utcnow()

        # Get transactions in last hour
        txns_1h = await self._transaction_repo.list_by_customer(
            customer_id=customer_id,
            start_date=now - timedelta(hours=1),
            end_date=now,
            limit=1000,
        )

        # Get transactions in last 24 hours
        txns_24h = await self._transaction_repo.list_by_customer(
            customer_id=customer_id,
            start_date=now - timedelta(hours=24),
            end_date=now,
            limit=1000,
        )

        # Get transactions in last 7 days
        txns_7d = await self._transaction_repo.list_by_customer(
            customer_id=customer_id,
            start_date=now - timedelta(days=7),
            end_date=now,
            limit=1000,
        )

        return {
            "velocity_1h": len(txns_1h),
            "velocity_24h": len(txns_24h),
            "velocity_7d": len(txns_7d),
        }

    async def detect_duplicate(
        self,
        customer_id: UUID,
        merchant_id: UUID,
        amount: Decimal,
        window_minutes: int = 5,
    ) -> bool:
        """Detect potential duplicate transaction.

        Args:
            customer_id: Customer UUID
            merchant_id: Merchant UUID
            amount: Transaction amount
            window_minutes: Time window for duplicate check

        Returns:
            True if potential duplicate found
        """
        now = datetime.utcnow()
        start_time = now - timedelta(minutes=window_minutes)

        # Get recent transactions
        recent_txns = await self._transaction_repo.list_by_customer(
            customer_id=customer_id,
            start_date=start_time,
            end_date=now,
            limit=100,
        )

        # Check for duplicate
        for txn in recent_txns:
            if (
                txn.merchant_id == merchant_id
                and txn.amount == amount
                and txn.status != "failed"
            ):
                return True

        return False

    async def prepare_features(
        self,
        transaction: Transaction,
    ) -> dict[str, object]:
        """Prepare business features for ML inference.

        This method extracts and calculates business features from a transaction
        without performing any ML predictions.

        Args:
            transaction: Transaction entity

        Returns:
            Dictionary of features ready for ML model

        Note:
            This method does NOT call ML models. It only prepares features.
        """
        # Get customer and merchant data
        customer = await self._customer_repo.get_by_id(transaction.customer_id)
        merchant = await self._merchant_repo.get_by_id(transaction.merchant_id)

        if not customer or not merchant:
            raise ValueError("Customer or merchant not found")

        # Calculate derived features
        customer_country = customer.country
        merchant_country = merchant.country
        country_match = customer_country == merchant_country

        # Is this a high-value transaction?
        is_high_value = transaction.amount >= Decimal("1000.00")

        # Transaction features
        features = {
            # Transaction basics
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "transaction_type": transaction.transaction_type,
            "payment_channel": transaction.payment_channel,
            "payment_method": transaction.payment_method,
            # Customer features
            "customer_risk_score": self._risk_category_to_score(customer.customer_risk_category),
            "customer_credit_score": customer.credit_score,
            "customer_account_age_days": customer.account_age_days,
            "customer_historical_fraud_count": customer.historical_fraud_count,
            "customer_lifetime_volume": float(customer.lifetime_transaction_volume),
            "customer_kyc_verified": customer.is_verified,
            # Merchant features
            "merchant_risk_rating": merchant.risk_rating,
            "merchant_fraud_rate": float(merchant.historical_fraud_rate),
            "merchant_total_transactions": merchant.total_transactions,
            "merchant_is_new": merchant.is_new_merchant,
            "mcc": merchant.mcc,
            # Velocity features
            "transactions_last_hour": transaction.velocity_1h if transaction.velocity_1h else 0.0,
            "transactions_last_day": transaction.velocity_24h if transaction.velocity_24h else 0.0,
            "transactions_last_week": transaction.velocity_7d if transaction.velocity_7d else 0.0,
            # Geographic features
            "country_match": country_match,
            "customer_country": customer_country,
            "merchant_country": merchant_country,
            "has_geolocation": transaction.latitude is not None,
            # Device features
            "has_device_id": transaction.device_id is not None,
            "has_ip_address": transaction.ip_address is not None,
            # Derived features
            "is_high_value": is_high_value,
            "is_online": transaction.payment_channel in ["online", "mobile"],
            # Time features
            "hour_of_day": transaction.timestamp.hour,
            "day_of_week": transaction.timestamp.weekday(),
            "is_weekend": transaction.timestamp.weekday() >= 5,
        }

        return features

    async def get_transaction_by_id(
        self,
        transaction_id: UUID,
    ) -> Transaction | None:
        """Get transaction by ID.

        Args:
            transaction_id: Transaction UUID

        Returns:
            Transaction if found, None otherwise
        """
        return await self._transaction_repo.get_by_id(transaction_id)

    async def get_customer_transactions(
        self,
        customer_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """Get transactions for a customer.

        Args:
            customer_id: Customer UUID
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Tuple of (list of transactions, total count)
        """
        transactions = await self._transaction_repo.list_by_customer(
            customer_id=customer_id,
            limit=limit,
            offset=offset,
        )

        # TODO: Implement actual count - for now return len(transactions)
        total = len(transactions)

        return transactions, total

    def _risk_category_to_score(self, category: str) -> int:
        """Convert risk category to numeric score.

        Args:
            category: Risk category (low, medium, high, critical)

        Returns:
            Numeric score (0-100)
        """
        mapping = {
            "low": 25,
            "medium": 50,
            "high": 75,
            "critical": 95,
        }
        return mapping.get(category, 50)
