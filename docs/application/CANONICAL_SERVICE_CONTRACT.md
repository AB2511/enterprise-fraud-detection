# CANONICAL SERVICE CONTRACT
## Enterprise AI Risk & Fraud Detection Platform

**Generated**: Application Contract Stabilization Sprint  
**Status**: SINGLE SOURCE OF TRUTH for Application Layer

---

## CUSTOMER SERVICE

**Location**: `src/application/services/customer_service.py`

| Method | Parameters | Return Type | Status |
|--------|-----------|--------------|--------|
| `create_customer` | `customer_name: str, email: str, country: str, date_of_birth: datetime \| None, user_id: UUID \| None` | `Customer` | ✅ IMPLEMENTED |
| `update_customer` | `customer_id: UUID, updates: dict, user_id: UUID \| None` | `Customer` | ✅ IMPLEMENTED |
| `deactivate_customer` | `customer_id: UUID, reason: str, user_id: UUID \| None` | `None` | ✅ IMPLEMENTED |
| `calculate_customer_profile` | `customer_id: UUID` | `dict` | ✅ IMPLEMENTED |
| `retrieve_customer_history` | `customer_id: UUID, limit: int` | `dict` | ✅ IMPLEMENTED |
| `verify_customer_kyc` | `customer_id: UUID, user_id: UUID \| None` | `Customer` | ✅ IMPLEMENTED |
| `record_fraud_incident` | `customer_id: UUID, user_id: UUID \| None` | `Customer` | ✅ IMPLEMENTED |
| `add_transaction_to_customer` | `customer_id: UUID, amount: Decimal` | `Customer` | ✅ IMPLEMENTED |

**Total Methods**: 8 | **Implemented**: 8 | **Coverage**: 100%

---

## MERCHANT SERVICE

**Location**: `src/application/services/merchant_service.py`

| Method | Parameters | Return Type | Status |
|--------|-----------|--------------|--------|
| `onboard_merchant` | `merchant_name: str, mcc: str, merchant_category: str, country: str, user_id: UUID \| None` | `Merchant` | ✅ IMPLEMENTED |
| `calculate_merchant_risk` | `merchant_id: UUID` | `dict` | ✅ IMPLEMENTED |
| `update_merchant_profile` | `merchant_id: UUID, updates: dict, user_id: UUID \| None` | `Merchant` | ✅ IMPLEMENTED |
| `lookup_merchant` | `merchant_id: UUID \| None, merchant_name: str \| None` | `Merchant \| None` | ✅ IMPLEMENTED |
| `record_merchant_transaction` | `merchant_id: UUID, amount: Decimal, is_fraud: bool, user_id: UUID \| None` | `Merchant` | ✅ IMPLEMENTED |
| `suspend_merchant` | `merchant_id: UUID, reason: str, user_id: UUID \| None` | `Merchant` | ✅ IMPLEMENTED |
| `reactivate_merchant` | `merchant_id: UUID, user_id: UUID \| None` | `Merchant` | ✅ IMPLEMENTED |
| `get_high_risk_merchants` | `limit: int` | `list[dict]` | ✅ IMPLEMENTED |

**Total Methods**: 8 | **Implemented**: 8 | **Coverage**: 100%

---

## TRANSACTION SERVICE

**Location**: `src/application/services/transaction_service.py`

| Method | Parameters | Return Type | Status |
|--------|-----------|--------------|--------|
| `validate_transaction` | `customer_id: UUID, merchant_id: UUID, amount: Decimal, currency: str` | `dict` | ✅ IMPLEMENTED |
| `create_transaction` | `customer_id: UUID, merchant_id: UUID, amount: Decimal, currency: str, transaction_type: str, payment_channel: str, payment_method: str, device_id: str \| None, ip_address: str \| None, latitude: float \| None, longitude: float \| None, user_id: UUID \| None` | `Transaction` | ✅ IMPLEMENTED |
| `update_transaction` | `transaction_id: UUID, updates: dict, user_id: UUID \| None` | `Transaction` | ✅ IMPLEMENTED |
| `get_transaction_history` | `customer_id: UUID \| None, merchant_id: UUID \| None, start_date: datetime \| None, end_date: datetime \| None, limit: int, offset: int` | `list[Transaction]` | ✅ IMPLEMENTED |
| `search_transactions` | `search_criteria: dict, limit: int, offset: int` | `list[Transaction]` | ✅ IMPLEMENTED |
| `calculate_velocity` | `customer_id: UUID` | `dict` | ✅ IMPLEMENTED |
| `detect_duplicate` | `customer_id: UUID, merchant_id: UUID, amount: Decimal, window_minutes: int` | `bool` | ✅ IMPLEMENTED |
| `prepare_features` | `transaction: Transaction` | `dict` | ✅ IMPLEMENTED |

**Total Methods**: 8 | **Implemented**: 8 | **Coverage**: 100%

---

## PREDICTION SERVICE

**Location**: `src/application/services/prediction_service.py`

| Method | Parameters | Return Type | Status |
|--------|-----------|--------------|--------|
| `store_prediction` | `transaction_id: UUID, model_id: UUID, model_version: str, prediction_class: str, fraud_probability: float, confidence: float, explanation_data: dict \| None, latency_ms: float \| None, user_id: UUID \| None` | `dict` | ✅ IMPLEMENTED |
| `update_prediction_status` | `prediction_id: UUID, new_status: str, user_id: UUID \| None` | `dict` | ✅ IMPLEMENTED |
| `store_model_metadata` | `model_id: UUID, model_version: str, model_type: str, training_date: datetime, metrics: dict, user_id: UUID \| None` | `dict` | ✅ IMPLEMENTED |
| `store_explanation` | `prediction_id: UUID, explanation_type: str, explanation_data: dict, user_id: UUID \| None` | `dict` | ✅ IMPLEMENTED |
| `validate_prediction_data` | `fraud_probability: float, confidence: float` | `dict` | ✅ IMPLEMENTED |

**Total Methods**: 5 | **Implemented**: 5 | **Coverage**: 100%

**NOTE**: PredictionService returns `dict` (not domain entities) because it does NOT persist via repository. It's a temporary storage service pending full prediction repository implementation.

---

## ALERT SERVICE

**Location**: `src/application/services/alert_service.py`

| Method | Parameters | Return Type | Status |
|--------|-----------|--------------|--------|
| `create_alert` | `transaction_id: UUID, prediction_id: UUID, alert_type: str, severity: str, user_id: UUID \| None` | `Alert` | ✅ IMPLEMENTED |
| `assign_alert` | `alert_id: UUID, analyst_id: UUID, user_id: UUID \| None` | `Alert` | ✅ IMPLEMENTED |
| `close_alert` | `alert_id: UUID, resolution: str, resolved_by_id: UUID, user_id: UUID \| None` | `Alert` | ✅ IMPLEMENTED |
| `escalate_alert` | `alert_id: UUID, user_id: UUID \| None` | `Alert` | ✅ IMPLEMENTED |
| `track_sla` | `alert_id: UUID` | `dict` | ✅ IMPLEMENTED |
| `get_priority_queue` | `limit: int` | `list[dict]` | ✅ IMPLEMENTED |
| `get_analyst_workload` | `analyst_id: UUID` | `dict` | ✅ IMPLEMENTED |
| `get_sla_breached_alerts` | `limit: int` | `list[Alert]` | ✅ IMPLEMENTED |

**Total Methods**: 8 | **Implemented**: 8 | **Coverage**: 100%

---

## AUDIT SERVICE

**Location**: `src/application/services/audit_service.py`

| Method | Parameters | Return Type | Status |
|--------|-----------|--------------|--------|
| `search_audit_logs` | `entity_type: str \| None, entity_id: UUID \| None, action: str \| None, user_id: UUID \| None, start_date: datetime \| None, end_date: datetime \| None, limit: int, offset: int` | `list[AuditLog]` | ✅ IMPLEMENTED |
| `get_entity_history` | `entity_type: str, entity_id: UUID, limit: int` | `list[dict]` | ✅ IMPLEMENTED |
| `get_user_activity` | `user_id: UUID, start_date: datetime \| None, end_date: datetime \| None, limit: int` | `list[dict]` | ✅ IMPLEMENTED |
| `export_compliance_report` | `start_date: datetime, end_date: datetime, entity_types: list[str] \| None` | `dict` | ✅ IMPLEMENTED |
| `get_audit_statistics` | `start_date: datetime \| None, end_date: datetime \| None` | `dict` | ✅ IMPLEMENTED |
| `verify_audit_integrity` | `entity_type: str, entity_id: UUID` | `dict` | ✅ IMPLEMENTED |

**Total Methods**: 6 | **Implemented**: 6 | **Coverage**: 100%

---

## USER SERVICE

**Location**: `src/application/services/user_service.py`

| Method | Parameters | Return Type | Status |
|--------|-----------|--------------|--------|
| `create_user` | `email: str, password: str, role: str, created_by_id: UUID \| None` | `User` | ✅ IMPLEMENTED |
| `authenticate_user` | `email: str, password: str` | `dict \| None` | ✅ IMPLEMENTED |
| `change_user_password` | `user_id: UUID, old_password: str, new_password: str` | `User` | ✅ IMPLEMENTED |
| `assign_role` | `user_id: UUID, new_role: str, assigned_by_id: UUID \| None` | `User` | ✅ IMPLEMENTED |
| `deactivate_user` | `user_id: UUID, reason: str, deactivated_by_id: UUID \| None` | `User` | ✅ IMPLEMENTED |
| `activate_user` | `user_id: UUID, activated_by_id: UUID \| None` | `User` | ✅ IMPLEMENTED |
| `check_permission` | `user_id: UUID, permission: str` | `bool` | ✅ IMPLEMENTED |
| `list_users_by_role` | `role: str, limit: int` | `list[User]` | ✅ IMPLEMENTED |
| `get_active_users` | `limit: int` | `list[User]` | ✅ IMPLEMENTED |
| `get_user_profile` | `user_id: UUID` | `dict` | ✅ IMPLEMENTED |

**Total Methods**: 10 | **Implemented**: 10 | **Coverage**: 100%

---

## MODEL SERVICE

**Location**: NOT IMPLEMENTED

| Method | Parameters | Return Type | Status |
|--------|-----------|--------------|--------|
| N/A | N/A | N/A | ❌ SERVICE NOT IMPLEMENTED |

**NOTE**: ModelService does not exist. All model-related use cases are NOT IMPLEMENTABLE.

---

## SUMMARY

| Service | Methods | Implemented | Coverage |
|---------|---------|-------------|----------|
| Customer | 8 | 8 | 100% |
| Merchant | 8 | 8 | 100% |
| Transaction | 8 | 8 | 100% |
| Prediction | 5 | 5 | 100% |
| Alert | 8 | 8 | 100% |
| Audit | 6 | 6 | 100% |
| User | 10 | 10 | 100% |
| Model | 0 | 0 | N/A |
| **TOTAL** | **53** | **53** | **100%** |

