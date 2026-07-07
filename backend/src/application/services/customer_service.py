"""Customer Service - Business workflows for customer management."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.application.exceptions.application_exceptions import (
    ConflictException,
    EntityNotFoundException,
)
from src.application.interfaces.audit_repository import AuditRepository
from src.application.interfaces.customer_repository import CustomerRepository
from src.domain.entities.audit_log import AuditLog
from src.domain.entities.customer import Customer


class CustomerService:
    """Service for customer management business workflows.

    This service orchestrates customer operations, ensuring business rules
    are enforced and audit trails are maintained.
    """

    def __init__(
        self,
        customer_repository: CustomerRepository,
        audit_repository: AuditRepository,
    ) -> None:
        """Initialize customer service.

        Args:
            customer_repository: Repository for customer persistence
            audit_repository: Repository for audit logging
        """
        self._customer_repo = customer_repository
        self._audit_repo = audit_repository

    async def create_customer(
        self,
        customer_name: str,
        email: str,
        country: str,
        date_of_birth: datetime | None = None,
        user_id: UUID | None = None,
    ) -> Customer:
        """Create a new customer with validation and audit.

        Args:
            customer_name: Customer full name
            email: Customer email address
            country: Customer country code
            date_of_birth: Customer date of birth
            user_id: User performing the action

        Returns:
            Created customer entity

        Raises:
            ValueError: If validation fails
            ConflictError: If email already exists
        """
        # Check if email already exists
        existing = await self._customer_repo.get_by_email(email)
        if existing:
            raise ConflictException(
                message=f"Customer with email {email} already exists",
                resource_type="Customer",
                conflicting_field="email",
                conflicting_value=email,
            )

        # Create customer entity
        customer = Customer(
            customer_name=customer_name,
            email=email,
            country=country,
            date_of_birth=date_of_birth,
            kyc_status="pending",
            customer_risk_category="medium",
        )

        # Persist customer
        created_customer = await self._customer_repo.create(customer)

        # Create audit log
        audit = AuditLog.for_creation(
            entity_type="customer",
            entity_id=created_customer.customer_id,
            user_id=user_id,
            username="system",
            new_value={
                "name": customer_name,
                "email": email,
                "country": country,
            },
        )
        await self._audit_repo.create(audit)

        return created_customer

    async def update_customer(
        self,
        customer_id: UUID,
        updates: dict,
        user_id: UUID | None = None,
    ) -> Customer:
        """Update customer information.

        Args:
            customer_id: Customer UUID
            updates: Dictionary of fields to update
            user_id: User performing the action

        Returns:
            Updated customer

        Raises:
            NotFoundError: If customer doesn't exist
        """
        # Retrieve existing customer
        customer = await self._customer_repo.get_by_id(customer_id)
        if not customer:
            raise EntityNotFoundException(
                entity_type="Customer",
                entity_id=customer_id,
            )

        # Store old values for audit
        old_values = {
            "name": customer.customer_name,
            "email": customer.email,
            "kyc_status": customer.kyc_status,
            "risk_category": customer.customer_risk_category,
        }

        # Apply updates
        if "customer_name" in updates:
            customer.customer_name = updates["customer_name"]
        if "credit_score" in updates:
            customer.update_credit_score(updates["credit_score"])

        # Update timestamp
        customer.updated_at = datetime.utcnow()

        # Persist changes
        updated_customer = await self._customer_repo.update(customer)

        # Create audit log
        new_values = {
            "name": customer.customer_name,
            "email": customer.email,
            "kyc_status": customer.kyc_status,
            "risk_category": customer.customer_risk_category,
        }

        audit = AuditLog.for_update(
            entity_type="customer",
            entity_id=customer_id,
            user_id=user_id,
            username="system",
            old_value=old_values,
            new_value=new_values,
        )
        await self._audit_repo.create(audit)

        return updated_customer

    async def deactivate_customer(
        self,
        customer_id: UUID,
        reason: str,
        user_id: UUID | None = None,
    ) -> None:
        """Deactivate customer account (soft delete).

        Args:
            customer_id: Customer UUID
            reason: Reason for deactivation
            user_id: User performing the action

        Raises:
            NotFoundError: If customer doesn't exist
        """
        # Verify customer exists and capture state before deletion
        customer = await self._customer_repo.get_by_id(customer_id)
        if not customer:
            raise EntityNotFoundException(
                entity_type="Customer",
                entity_id=customer_id,
            )

        # Capture old state for audit
        old_state = {
            "customer_id": str(customer.customer_id),
            "customer_name": customer.customer_name,
            "email": customer.email,
            "is_active": customer.is_active,
            "kyc_status": customer.kyc_status,
        }

        # Soft delete via repository (sets deleted_at timestamp)
        deleted = await self._customer_repo.delete(customer_id)

        if not deleted:
            raise EntityNotFoundException(
                entity_type="Customer",
                entity_id=customer_id,
            )

        # Audit the deletion
        audit = AuditLog.for_deletion(
            entity_type="customer",
            entity_id=customer_id,
            old_value=old_state,
            user_id=user_id,
            username="system",
            description=reason,
        )
        await self._audit_repo.create(audit)

    async def calculate_customer_profile(
        self,
        customer_id: UUID,
    ) -> dict:
        """Calculate comprehensive customer profile.

        Args:
            customer_id: Customer UUID

        Returns:
            Customer profile dictionary with risk metrics

        Raises:
            NotFoundError: If customer doesn't exist
        """
        customer = await self._customer_repo.get_by_id(customer_id)
        if not customer:
            raise EntityNotFoundException(
                entity_type="Customer",
                entity_id=customer_id,
            )

        # Calculate profile
        profile = {
            "customer_id": str(customer.customer_id),
            "customer_name": customer.customer_name,
            "email": customer.email,
            "country": customer.country,
            "account_age_days": customer.account_age_days,
            "is_verified": customer.is_verified,
            "can_transact": customer.can_transact,
            "risk_category": customer.customer_risk_category,
            "is_high_risk": customer.is_high_risk,
            "credit_score": customer.credit_score,
            "historical_fraud_count": customer.historical_fraud_count,
            "lifetime_transaction_volume": float(customer.lifetime_transaction_volume),
            "kyc_status": customer.kyc_status,
            "age_years": customer.age_years,
            "created_at": customer.created_at,
            "updated_at": customer.updated_at,
            "is_active": customer.is_active,
        }

        return profile

    async def retrieve_customer_history(
        self,
        customer_id: UUID,
        limit: int = 100,
    ) -> dict:
        """Retrieve customer history including audit logs.

        Args:
            customer_id: Customer UUID
            limit: Maximum number of audit records

        Returns:
            Dictionary with customer data and audit history

        Raises:
            NotFoundError: If customer doesn't exist
        """
        customer = await self._customer_repo.get_by_id(customer_id)
        if not customer:
            raise EntityNotFoundException(
                entity_type="Customer",
                entity_id=customer_id,
            )

        # Get audit logs
        audit_logs = await self._audit_repo.list_by_entity(
            entity_type="customer",
            entity_id=customer_id,
            limit=limit,
        )

        return {
            "customer": await self.calculate_customer_profile(customer_id),
            "audit_history": [
                {
                    "action": log.action,
                    "timestamp": log.created_at.isoformat(),
                    "user_id": str(log.user_id) if log.user_id else None,
                    "old_value": log.old_value,
                    "new_value": log.new_value,
                }
                for log in audit_logs
            ],
        }

    async def verify_customer_kyc(
        self,
        customer_id: UUID,
        user_id: UUID | None = None,
    ) -> Customer:
        """Verify customer KYC status.

        Args:
            customer_id: Customer UUID
            user_id: User performing verification

        Returns:
            Updated customer

        Raises:
            NotFoundError: If customer doesn't exist
        """
        customer = await self._customer_repo.get_by_id(customer_id)
        if not customer:
            raise EntityNotFoundException(
                entity_type="Customer",
                entity_id=customer_id,
            )

        # Verify KYC
        old_status = customer.kyc_status
        customer.verify_kyc()

        # Persist
        updated_customer = await self._customer_repo.update(customer)

        # Audit
        audit = AuditLog.for_update(
            entity_type="customer",
            entity_id=customer_id,
            user_id=user_id,
            username="system",
            old_value={"kyc_status": old_status},
            new_value={"kyc_status": "verified"},
        )
        await self._audit_repo.create(audit)

        return updated_customer

    async def record_fraud_incident(
        self,
        customer_id: UUID,
        user_id: UUID | None = None,
    ) -> Customer:
        """Record a confirmed fraud incident for customer.

        Args:
            customer_id: Customer UUID
            user_id: User recording the incident

        Returns:
            Updated customer

        Raises:
            NotFoundError: If customer doesn't exist
        """
        customer = await self._customer_repo.get_by_id(customer_id)
        if not customer:
            raise EntityNotFoundException(
                entity_type="Customer",
                entity_id=customer_id,
            )

        # Increment fraud counter
        old_count = customer.historical_fraud_count
        customer.increment_fraud_counter()

        # Persist
        updated_customer = await self._customer_repo.update(customer)

        # Audit
        audit = AuditLog.for_update(
            entity_type="customer",
            entity_id=customer_id,
            user_id=user_id,
            username="system",
            old_value={"fraud_count": old_count},
            new_value={"fraud_count": customer.historical_fraud_count},
        )
        await self._audit_repo.create(audit)

        return updated_customer

    async def add_transaction_to_customer(
        self,
        customer_id: UUID,
        amount: Decimal,
    ) -> Customer:
        """Add transaction volume to customer lifetime total.

        Args:
            customer_id: Customer UUID
            amount: Transaction amount

        Returns:
            Updated customer

        Raises:
            NotFoundError: If customer doesn't exist
        """
        customer = await self._customer_repo.get_by_id(customer_id)
        if not customer:
            raise EntityNotFoundException(
                entity_type="Customer",
                entity_id=customer_id,
            )

        # Add volume
        customer.add_transaction_volume(amount)

        # Persist
        updated_customer = await self._customer_repo.update(customer)

        return updated_customer
