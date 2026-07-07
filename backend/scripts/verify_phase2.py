"""Verification script for Phase 2 implementation.

This script tests that all domain components are properly implemented
and can be imported and used without errors.
"""

import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Add backend/src to Python path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src.parent))


def test_imports():
    """Test that all modules can be imported."""
    print("🔹 Testing imports...")

    try:
        # Entities
        # Repository Interfaces
        from src.application.interfaces import (
            AlertRepository,
            AuditRepository,
            CustomerRepository,
            MerchantRepository,
            TransactionRepository,
            UserRepository,
        )
        from src.domain.entities import (
            Alert,
            AuditLog,
            Customer,
            Merchant,
            Prediction,
            Transaction,
            User,
        )

        # Enumerations
        from src.domain.enums import (
            AlertSeverity,
            AlertStatus,
            CustomerStatus,
            KYCStatus,
            ModelStatus,
            PaymentChannel,
            PaymentMethod,
            PredictionClass,
            TransactionStatus,
            UserRole,
        )

        # Value Objects
        from src.domain.value_objects import (
            DeviceID,
            IPAddress,
            ModelVersion,
            Money,
            RiskScore,
        )

        print("   ✅ All imports successful!")
        return True

    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False


def test_value_objects():
    """Test value object creation and validation."""
    print("\n🔹 Testing value objects...")

    try:
        # Test Money
        money = Money(amount=Decimal("100.00"), currency="USD")
        assert str(money) == "100.00 USD"

        # Test IPAddress
        ip = IPAddress(address="192.168.1.100")
        assert ip.is_private() == True
        anonymized = ip.anonymize()
        assert anonymized.address == "192.168.1.0"

        # Test DeviceID
        device = DeviceID(device_id="mobile-android-12345678")
        assert device.is_mobile() == True
        assert len(device.hash()) == 64

        # Test RiskScore
        risk = RiskScore(score=75.5)
        assert risk.get_level() == "high"
        assert risk.is_high_risk() == True

        # Test ModelVersion
        version = ModelVersion(version="1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        newer = version.bump_minor()
        assert newer.version == "1.3.0"

        print("   ✅ All value objects working correctly!")
        return True

    except Exception as e:
        print(f"   ❌ Value object test failed: {e}")
        return False


def test_enumerations():
    """Test enumeration functionality."""
    print("\n🔹 Testing enumerations...")

    try:
        from src.domain.enums import (
            AlertSeverity,
            KYCStatus,
            PaymentMethod,
            TransactionStatus,
            UserRole,
        )

        # Test AlertSeverity
        severity = AlertSeverity.CRITICAL
        assert severity.get_sla_hours() == 1
        assert severity.get_priority_score() == 4

        # Test KYCStatus
        kyc = KYCStatus.VERIFIED
        assert kyc.is_valid() == True
        assert kyc.blocks_transactions() == False

        # Test PaymentMethod
        method = PaymentMethod.CREDIT_CARD
        assert method.is_reversible() == True
        assert method.get_risk_level() == "medium"

        # Test TransactionStatus
        status = TransactionStatus.APPROVED
        assert status.is_final() == True
        assert status.is_successful() == True

        # Test UserRole
        role = UserRole.ANALYST
        assert role.can_review_alerts() == True
        assert role.can_train_models() == False
        assert "review_alerts" in role.get_permissions()

        print("   ✅ All enumerations working correctly!")
        return True

    except Exception as e:
        print(f"   ❌ Enumeration test failed: {e}")
        return False


def test_customer_entity():
    """Test Customer entity business logic."""
    print("\n🔹 Testing Customer entity...")

    try:
        from src.domain.entities import Customer

        # Create customer
        customer = Customer(
            customer_name="John Doe",
            email="john.doe@example.com",
            country="USA",
            kyc_status="verified",
            credit_score=720,
            account_age_days=365,
        )

        # Test initial state
        assert customer.is_verified == True
        assert customer.can_transact == True
        assert customer.is_high_risk == False

        # Test fraud counter
        customer.increment_fraud_counter()
        assert customer.historical_fraud_count == 1

        # Test credit score update
        customer.update_credit_score(450)
        assert customer.credit_score == 450
        # Risk should recalculate
        assert customer.customer_risk_category in ["low", "medium", "high", "critical"]

        # Test transaction volume
        customer.add_transaction_volume(Decimal("100.50"))
        assert customer.lifetime_transaction_volume == Decimal("100.50")

        # Test age calculation
        from datetime import date

        customer.date_of_birth = date(1990, 1, 1)
        age = customer.age_years
        assert age is not None and age > 0

        print("   ✅ Customer entity working correctly!")
        return True

    except Exception as e:
        print(f"   ❌ Customer entity test failed: {e}")
        return False


def test_merchant_entity():
    """Test Merchant entity business logic."""
    print("\n🔹 Testing Merchant entity...")

    try:
        from src.domain.entities import Merchant

        # Create merchant
        merchant = Merchant(
            merchant_name="Test Store",
            mcc="5411",
            merchant_category="grocery",
            country="USA",
            risk_rating=30,
        )

        # Test initial state
        assert merchant.is_high_risk == False
        assert merchant.is_new_merchant == True

        # Test risk calculation
        calculated_risk = merchant.calculate_risk()
        assert 0 <= calculated_risk <= 100

        # Test transaction recording
        merchant.record_transaction(Decimal("50.00"), is_fraud=False)
        assert merchant.total_transactions == 1
        assert merchant.total_volume == Decimal("50.00")

        # Test fraud transaction
        merchant.record_transaction(Decimal("100.00"), is_fraud=True)
        assert merchant.total_transactions == 2
        assert merchant.historical_fraud_rate > 0

        # Test average
        avg = merchant.average_transaction_amount
        assert avg == Decimal("75.00")

        # Test risk level
        level = merchant.get_risk_level()
        assert level in ["low", "medium", "high", "critical"]

        print("   ✅ Merchant entity working correctly!")
        return True

    except Exception as e:
        print(f"   ❌ Merchant entity test failed: {e}")
        return False


def test_user_entity():
    """Test User entity business logic."""
    print("\n🔹 Testing User entity...")

    try:
        from src.domain.entities import User

        # Create user
        user = User(
            email="analyst@example.com",
            password="SecurePassword123!",
            role="analyst",
        )

        # Test password verification
        assert user.verify_password("SecurePassword123!") == True
        assert user.verify_password("WrongPassword") == False

        # Test role permissions
        assert user.can_review_alerts() == True
        assert user.can_manage_users() == False
        assert user.has_permission("review_alerts") == True

        # Test activation
        user.deactivate()
        assert user.status == "inactive"
        user.activate()
        assert user.status == "active"

        # Test role change
        user.assign_role("admin")
        assert user.role == "admin"
        assert user.can_manage_users() == True

        print("   ✅ User entity working correctly!")
        return True

    except Exception as e:
        print(f"   ❌ User entity test failed: {e}")
        return False


def test_alert_entity():
    """Test Alert entity business logic."""
    print("\n🔹 Testing Alert entity...")

    try:
        from src.domain.entities import Alert

        # Create alert
        alert = Alert(
            transaction_id=uuid4(),
            prediction_id=uuid4(),
            alert_type="high_amount",
            severity="high",
        )

        # Test initial state
        assert alert.status == "open"
        assert alert.is_open() == True
        assert alert.requires_action() == True

        # Test SLA calculation
        sla_hours = alert.calculate_sla_hours()
        assert sla_hours == 4  # High severity = 4 hours

        # Test assignment
        analyst_id = uuid4()
        alert.assign_to_analyst(analyst_id)
        assert alert.assigned_analyst_id == analyst_id
        assert alert.status == "in_review"

        # Test resolution
        alert.resolve(resolution="false_positive", resolved_by_id=analyst_id)
        assert alert.status == "false_positive"
        assert alert.is_resolved() == True
        assert alert.requires_action() == False

        print("   ✅ Alert entity working correctly!")
        return True

    except Exception as e:
        print(f"   ❌ Alert entity test failed: {e}")
        return False


def test_audit_log_entity():
    """Test AuditLog entity."""
    print("\n🔹 Testing AuditLog entity...")

    try:
        from src.domain.entities import AuditLog

        # Test factory method for creation
        audit = AuditLog.for_creation(
            entity_type="customer",
            entity_id=uuid4(),
            user_id=uuid4(),
            username="admin@example.com",
            new_value={"name": "John Doe", "email": "john@example.com"},
        )

        assert audit.action == "created"
        assert audit.old_value is None
        assert audit.new_value is not None

        # Test factory method for update
        audit2 = AuditLog.for_update(
            entity_type="customer",
            entity_id=uuid4(),
            user_id=uuid4(),
            username="admin@example.com",
            old_value={"status": "inactive"},
            new_value={"status": "active"},
        )

        assert audit2.action == "updated"
        assert audit2.old_value is not None
        assert audit2.new_value is not None

        print("   ✅ AuditLog entity working correctly!")
        return True

    except Exception as e:
        print(f"   ❌ AuditLog entity test failed: {e}")
        return False


def test_database_models():
    """Test that SQLAlchemy models can be imported."""
    print("\n🔹 Testing SQLAlchemy models...")

    try:
        from src.infrastructure.database.models import (
            AlertModel,
            AnalystFeedbackModel,
            AuditLogModel,
            CustomerModel,
            MerchantModel,
            PredictionModel,
            TransactionModel,
            UserModel,
        )

        # Test that models have expected attributes
        assert hasattr(UserModel, "__tablename__")
        assert hasattr(CustomerModel, "__tablename__")
        assert hasattr(MerchantModel, "__tablename__")
        assert hasattr(TransactionModel, "__tablename__")
        assert hasattr(PredictionModel, "__tablename__")
        assert hasattr(AlertModel, "__tablename__")
        assert hasattr(AuditLogModel, "__tablename__")
        assert hasattr(AnalystFeedbackModel, "__tablename__")

        print("   ✅ All SQLAlchemy models imported successfully!")
        return True

    except Exception as e:
        print(f"   ❌ SQLAlchemy model test failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("=" * 80)
    print("PHASE 2 VERIFICATION - Domain Model & Database Design")
    print("=" * 80)
    print()

    results = {
        "Imports": test_imports(),
        "Value Objects": test_value_objects(),
        "Enumerations": test_enumerations(),
        "Customer Entity": test_customer_entity(),
        "Merchant Entity": test_merchant_entity(),
        "User Entity": test_user_entity(),
        "Alert Entity": test_alert_entity(),
        "AuditLog Entity": test_audit_log_entity(),
        "Database Models": test_database_models(),
    }

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All verification tests passed! Phase 2 implementation is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
