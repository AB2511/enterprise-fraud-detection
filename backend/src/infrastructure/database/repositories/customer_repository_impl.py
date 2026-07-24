"""Customer Repository Implementation using SQLAlchemy Async."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.customer_repository import CustomerRepository
from src.domain.entities.customer import Customer
from src.domain.exceptions.base import (
    ConflictError,
    DomainException,
    NotFoundError,
    RepositoryError,
)
from src.infrastructure.database.models import CustomerModel


class CustomerNotFoundError(DomainException):
    """Raised when customer is not found."""

    def __init__(self, customer_id: UUID) -> None:
        super().__init__(f"Customer with ID {customer_id} not found", "CUSTOMER_NOT_FOUND")


class CustomerEmailExistsError(DomainException):
    """Raised when customer email already exists."""

    def __init__(self, email: str) -> None:
        super().__init__(f"Customer with email {email} already exists", "CUSTOMER_EMAIL_EXISTS")


class CustomerRepositoryImpl(CustomerRepository):
    """SQLAlchemy implementation of CustomerRepository.

    Provides async database operations for Customer entities using
    SQLAlchemy ORM with proper error handling and domain mapping.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, customer: Customer) -> Customer:
        """Create a new customer.

        Args:
            customer: Customer entity to create

        Returns:
            Created customer with generated ID

        Raises:
            CustomerEmailExistsError: If email already exists
            RepositoryError: If creation fails
        """
        try:
            # Check if email already exists (case-insensitive)
            existing = await self._session.execute(
                select(CustomerModel).where(
                    and_(
                        func.lower(CustomerModel.email) == func.lower(customer.email),
                        CustomerModel.deleted_at.is_(None),
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise CustomerEmailExistsError(customer.email)

            # Convert domain entity to database model
            customer_model = CustomerModel(
                id=customer.customer_id,
                customer_name=customer.customer_name,
                email=customer.email.lower(),  # Normalize email
                date_of_birth=customer.date_of_birth,
                country=customer.country,
                kyc_status=customer.kyc_status,
                customer_risk_category=customer.customer_risk_category,
                historical_fraud_count=customer.historical_fraud_count,
                credit_score=customer.credit_score,
                lifetime_transaction_volume=float(customer.lifetime_transaction_volume),
                account_age_days=customer.account_age_days,
                is_active=customer.is_active,
                created_at=customer.created_at,
                updated_at=customer.updated_at,
            )

            self._session.add(customer_model)
            await self._session.flush()
            await self._session.refresh(customer_model)

            # Convert back to domain entity
            return self._model_to_entity(customer_model)

        except CustomerEmailExistsError:
            raise ConflictError(f"Customer with email {customer.email} already exists") from None
        except IntegrityError as e:
            await self._session.rollback()
            if "unique" in str(e).lower():
                raise ConflictError(f"Customer with email {customer.email} already exists") from e
            raise DomainException(
                f"Database constraint violation: {e}", "DB_CONSTRAINT_ERROR"
            ) from e

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to create customer: {e}", "REPOSITORY_ERROR") from e

    async def get_by_id(self, customer_id: UUID) -> Customer | None:
        """Retrieve customer by ID.

        Args:
            customer_id: Customer UUID

        Returns:
            Customer if found, None otherwise
        """
        try:
            result = await self._session.execute(
                select(CustomerModel).where(
                    and_(CustomerModel.id == customer_id, CustomerModel.deleted_at.is_(None))
                )
            )
            customer_model = result.scalar_one_or_none()

            if customer_model:
                return self._model_to_entity(customer_model)
            return None

        except Exception as e:
            raise DomainException(f"Failed to get customer by ID: {e}", "REPOSITORY_ERROR") from e

    async def get_by_email(self, email: str) -> Customer | None:
        """Retrieve customer by email (case-insensitive).

        Args:
            email: Customer email address

        Returns:
            Customer if found, None otherwise
        """
        try:
            result = await self._session.execute(
                select(CustomerModel).where(
                    and_(
                        func.lower(CustomerModel.email) == func.lower(email),
                        CustomerModel.deleted_at.is_(None),
                    )
                )
            )
            customer_model = result.scalar_one_or_none()

            if customer_model:
                return self._model_to_entity(customer_model)
            return None

        except Exception as e:
            raise DomainException(
                f"Failed to get customer by email: {e}", "REPOSITORY_ERROR"
            ) from e

    async def update(self, customer: Customer) -> Customer:
        """Update existing customer.

        Args:
            customer: Customer entity with updated data

        Returns:
            Updated customer

        Raises:
            CustomerNotFoundError: If customer doesn't exist
            RepositoryError: If update fails
        """
        try:
            # Check if customer exists
            existing = await self._session.execute(
                select(CustomerModel).where(
                    and_(
                        CustomerModel.id == customer.customer_id, CustomerModel.deleted_at.is_(None)
                    )
                )
            )
            existing_customer = existing.scalar_one_or_none()
            if not existing_customer:
                raise NotFoundError(f"Customer {customer.customer_id} not found")

            # Check if email already exists for another customer
            if existing_customer.email.lower() != customer.email.lower():
                email_check = await self._session.execute(
                    select(CustomerModel).where(
                        and_(
                            func.lower(CustomerModel.email) == func.lower(customer.email),
                            CustomerModel.id != customer.customer_id,
                            CustomerModel.deleted_at.is_(None),
                        )
                    )
                )
                if email_check.scalar_one_or_none():
                    raise ConflictError(f"Customer with email {customer.email} already exists")

            # Update fields
            await self._session.execute(
                update(CustomerModel)
                .where(CustomerModel.id == customer.customer_id)
                .values(
                    customer_name=customer.customer_name,
                    email=customer.email.lower(),  # Normalize email
                    date_of_birth=customer.date_of_birth,
                    country=customer.country,
                    kyc_status=customer.kyc_status,
                    customer_risk_category=customer.customer_risk_category,
                    historical_fraud_count=customer.historical_fraud_count,
                    credit_score=customer.credit_score,
                    lifetime_transaction_volume=float(customer.lifetime_transaction_volume),
                    account_age_days=customer.account_age_days,
                    is_active=customer.is_active,
                    updated_at=datetime.now(UTC),
                )
            )

            # Fetch updated record
            result = await self._session.execute(
                select(CustomerModel).where(CustomerModel.id == customer.customer_id)
            )
            updated_model = result.scalar_one()

            return self._model_to_entity(updated_model)

        except (NotFoundError, ConflictError):
            raise
        except IntegrityError as e:
            await self._session.rollback()
            if "unique" in str(e).lower():
                raise CustomerEmailExistsError(customer.email) from e
            raise DomainException(
                f"Database constraint violation: {e}", "DB_CONSTRAINT_ERROR"
            ) from e
        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to update customer: {e}", "REPOSITORY_ERROR") from e

    async def delete(self, customer_id: UUID) -> bool:
        """Soft delete customer.

        Args:
            customer_id: Customer UUID

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        try:
            result = await self._session.execute(
                update(CustomerModel)
                .where(and_(CustomerModel.id == customer_id, CustomerModel.deleted_at.is_(None)))
                .values(deleted_at=datetime.now(UTC))
            )

            return result.rowcount > 0

        except Exception as e:
            await self._session.rollback()
            raise DomainException(f"Failed to delete customer: {e}", "REPOSITORY_ERROR") from e

    async def list_by_risk_category(
        self,
        risk_category: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Customer]:
        """List customers by risk category with pagination.

        Args:
            risk_category: Risk category to filter by
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of customers
        """
        try:
            result = await self._session.execute(
                select(CustomerModel)
                .where(
                    and_(
                        CustomerModel.customer_risk_category == risk_category,
                        CustomerModel.deleted_at.is_(None),
                        CustomerModel.is_active,
                    )
                )
                .order_by(desc(CustomerModel.updated_at))
                .limit(limit)
                .offset(offset)
            )

            customers = result.scalars().all()
            return [self._model_to_entity(customer) for customer in customers]

        except Exception as e:
            raise DomainException(
                f"Failed to list customers by risk category: {e}", "REPOSITORY_ERROR"
            ) from e

    async def list_by_kyc_status(
        self,
        kyc_status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Customer]:
        """List customers by KYC status with pagination.

        Args:
            kyc_status: KYC status to filter by
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of customers
        """
        try:
            result = await self._session.execute(
                select(CustomerModel)
                .where(
                    and_(CustomerModel.kyc_status == kyc_status, CustomerModel.deleted_at.is_(None))
                )
                .order_by(desc(CustomerModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            customers = result.scalars().all()
            return [self._model_to_entity(customer) for customer in customers]

        except Exception as e:
            raise DomainException(
                f"Failed to list customers by KYC status: {e}", "REPOSITORY_ERROR"
            ) from e

    async def count_by_risk_category(self, risk_category: str) -> int:
        """Count customers in risk category.

        Args:
            risk_category: Risk category to count

        Returns:
            Number of customers
        """
        try:
            result = await self._session.execute(
                select(func.count(CustomerModel.id)).where(
                    and_(
                        CustomerModel.customer_risk_category == risk_category,
                        CustomerModel.deleted_at.is_(None),
                        CustomerModel.is_active,
                    )
                )
            )

            return result.scalar() or 0

        except Exception as e:
            raise DomainException(
                f"Failed to count customers by risk category: {e}", "REPOSITORY_ERROR"
            ) from e

    async def list_high_risk(self, limit: int = 100) -> list[Customer]:
        """List high and critical risk customers.

        Args:
            limit: Maximum number of results

        Returns:
            List of high-risk customers
        """
        try:
            result = await self._session.execute(
                select(CustomerModel)
                .where(
                    and_(
                        CustomerModel.customer_risk_category.in_(["high", "critical"]),
                        CustomerModel.deleted_at.is_(None),
                        CustomerModel.is_active,
                    )
                )
                .order_by(
                    desc(CustomerModel.customer_risk_category),
                    desc(CustomerModel.historical_fraud_count),
                    CustomerModel.credit_score.asc(),
                )
                .limit(limit)
            )

            customers = result.scalars().all()
            return [self._model_to_entity(customer) for customer in customers]

        except Exception as e:
            raise DomainException(
                f"Failed to list high-risk customers: {e}", "REPOSITORY_ERROR"
            ) from e

    async def find_by_criteria(
        self,
        email_pattern: str | None = None,
        country: str | None = None,
        kyc_status: str | None = None,
        risk_category: str | None = None,
        min_credit_score: int | None = None,
        max_credit_score: int | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Customer]:
        """Find customers by multiple criteria.

        Args:
            email_pattern: Email pattern (LIKE search)
            country: Country filter
            kyc_status: KYC status filter
            risk_category: Risk category filter
            min_credit_score: Minimum credit score
            max_credit_score: Maximum credit score
            is_active: Active status filter
            limit: Maximum results
            offset: Results offset

        Returns:
            List of matching customers
        """
        try:
            query = select(CustomerModel).where(CustomerModel.deleted_at.is_(None))

            # Add filters dynamically
            if email_pattern:
                query = query.where(CustomerModel.email.ilike(f"%{email_pattern}%"))
            if country:
                query = query.where(CustomerModel.country == country)
            if kyc_status:
                query = query.where(CustomerModel.kyc_status == kyc_status)
            if risk_category:
                query = query.where(CustomerModel.customer_risk_category == risk_category)
            if min_credit_score is not None:
                query = query.where(CustomerModel.credit_score >= min_credit_score)
            if max_credit_score is not None:
                query = query.where(CustomerModel.credit_score <= max_credit_score)
            if is_active is not None:
                query = query.where(CustomerModel.is_active == is_active)

            query = query.order_by(desc(CustomerModel.updated_at)).limit(limit).offset(offset)

            result = await self._session.execute(query)
            customers = result.scalars().all()

            return [self._model_to_entity(customer) for customer in customers]

        except Exception as e:
            raise DomainException(
                f"Failed to find customers by criteria: {e}", "REPOSITORY_ERROR"
            ) from e

    async def bulk_update_risk_category(self, customer_ids: list[UUID], new_category: str) -> int:
        """Bulk update risk category for multiple customers.

        Args:
            customer_ids: List of customer IDs to update
            new_category: New risk category

        Returns:
            Number of customers updated
        """
        try:
            if not customer_ids:
                return 0

            result = await self._session.execute(
                update(CustomerModel)
                .where(and_(CustomerModel.id.in_(customer_ids), CustomerModel.deleted_at.is_(None)))
                .values(customer_risk_category=new_category, updated_at=datetime.now(UTC))
            )

            return result.rowcount

        except Exception as e:
            await self._session.rollback()
            raise DomainException(
                f"Failed to bulk update risk category: {e}", "REPOSITORY_ERROR"
            ) from e

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        try:
            result = await self._session.execute(
                select(func.count(CustomerModel.id)).where(
                    and_(
                        func.lower(CustomerModel.email) == func.lower(email),
                        CustomerModel.deleted_at.is_(None),
                    )
                )
            )
            count = result.scalar() or 0
            return count > 0

        except Exception as e:
            raise DomainException(
                f"Failed to check email existence: {e}", "REPOSITORY_ERROR"
            ) from e

    def _model_to_entity(self, model: CustomerModel) -> Customer:
        """Convert database model to domain entity.

        Args:
            model: SQLAlchemy model instance

        Returns:
            Domain entity
        """
        from decimal import Decimal

        # Ensure datetimes are timezone-aware
        created_at = model.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        updated_at = model.updated_at
        if updated_at and updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)

        return Customer(
            customer_id=UUID(str(model.id)),
            customer_name=model.customer_name,
            email=model.email,
            date_of_birth=model.date_of_birth,
            country=model.country,
            kyc_status=model.kyc_status,
            customer_risk_category=model.customer_risk_category,
            historical_fraud_count=model.historical_fraud_count,
            credit_score=model.credit_score,
            lifetime_transaction_volume=Decimal(str(model.lifetime_transaction_volume)),
            account_age_days=model.account_age_days,
            is_active=model.is_active,
            created_at=created_at,
            updated_at=updated_at,
        )
