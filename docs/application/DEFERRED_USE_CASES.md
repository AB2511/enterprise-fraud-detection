# DEFERRED USE CASES
## Application Contract Stabilization Sprint

**Generated**: Application Layer Audit  
**Status**: Use cases that CANNOT be implemented with current service layer

---

## REASON FOR DEFERRAL

These use cases call service methods that DO NOT EXIST in the canonical service contract. They were created speculatively without corresponding service implementation.

**RULE**: We do NOT invent service methods. The Service Layer is the single source of truth.

---

## MERCHANT USE CASES (5 DEFERRED)

### 1. CreateMerchantUseCase ⚠️ METHOD NAME MISMATCH

**Current Call**: `create_merchant()`  
**Canonical Method**: `onboard_merchant()`  
**Status**: MISMATCH - use case calls wrong method name  
**Action Required**: Rename use case call from `create_merchant()` to `onboard_merchant()`

**Parameters Mismatch**:
- Use case expects: `merchant_name, merchant_category, country, contact_email, business_registration`
- Service provides: `merchant_name, mcc, merchant_category, country`
- **MISSING**: `contact_email`, `business_registration`
- **MISSING**: `mcc` (required by service)

---

### 2. UpdateMerchantUseCase ⚠️ METHOD NAME MISMATCH

**Current Call**: `update_merchant()`  
**Canonical Method**: `update_merchant_profile()`  
**Status**: MISMATCH - use case calls wrong method name  
**Action Required**: Rename use case call from `update_merchant()` to `update_merchant_profile()`

---

### 3. DeleteMerchantUseCase ❌ METHOD MISSING

**Current Call**: `deactivate_merchant()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

**Note**: MerchantService has `suspend_merchant()` but NOT `deactivate_merchant()`. These are different operations.

---

### 4. GetMerchantUseCase ❌ METHOD MISSING

**Current Call**: `get_merchant_by_id()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

**Note**: Service has `lookup_merchant()` which accepts EITHER merchant_id OR merchant_name, but not a dedicated `get_merchant_by_id()`.

---

### 5. ListMerchantsUseCase ❌ METHOD MISSING

**Current Call**: `search_merchants()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

---

### 6. GetMerchantStatisticsUseCase ❌ METHOD MISSING

**Current Call**: `get_merchant_statistics()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

---

### 7. SearchMerchantsByNameUseCase ❌ METHOD MISSING

**Current Call**: `search_merchants_by_name()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

---

## TRANSACTION USE CASES (2 DEFERRED)

### 1. GetTransactionUseCase ❌ METHOD MISSING

**Current Call**: `get_transaction_by_id()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

**Note**: Service has `get_transaction_history()` but not a simple `get_transaction_by_id()`.

---

### 2. GetCustomerTransactionsUseCase ❌ METHOD MISSING

**Current Call**: `get_customer_transactions()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: Use `get_transaction_history(customer_id=...)` instead OR defer

**Note**: `get_transaction_history()` CAN return customer transactions when `customer_id` is provided, but the use case expects a dedicated method with different signature.

---

## PREDICTION USE CASES (ALL 11 DEFERRED)

### ❌ ENTIRE BOUNDED CONTEXT NOT IMPLEMENTABLE

**Reason**: PredictionService only provides STORAGE methods (returns `dict`), NOT CRUD operations (returns domain entities).

All use cases expect methods that return `Prediction` entity and perform full CRUD operations via repository.

**Deferred Use Cases**:
1. CreatePredictionUseCase - calls `create_prediction()` ❌
2. UpdatePredictionUseCase - calls `update_prediction()` ❌
3. GetPredictionUseCase - calls `get_prediction_by_id()` ❌
4. GetPredictionByTransactionUseCase - calls `get_prediction_by_transaction_id()` ❌
5. ListPredictionsUseCase - calls `search_predictions()` ❌
6. GetHighRiskPredictionsUseCase - calls `get_high_risk_predictions()` ❌
7. GetModelPerformanceUseCase - calls `get_model_performance_stats()` ❌
8. GetPredictionExplanationUseCase - calls `get_prediction_explanation()` ❌
9. GetPredictionsNeedingFeedbackUseCase - calls `get_predictions_needing_feedback()` ❌
10. ProvidePredictionFeedbackUseCase - calls `provide_feedback()` ❌
11. GetModelComparisonUseCase - calls `get_model_performance_by_version()` ❌

**Action Required**:
- Implement PredictionRepository
- Add repository to PredictionService
- Implement full CRUD operations
- OR defer entire Prediction use case layer

---

## ALERT USE CASES (9 DEFERRED)

### 1. UpdateAlertUseCase ❌ METHOD MISSING

**Current Call**: `update_alert()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

---

### 2. GetAlertUseCase ❌ METHOD MISSING

**Current Call**: `get_alert_by_id()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

**Note**: Service can retrieve alerts internally (e.g., in `assign_alert()`, `escalate_alert()`), but doesn't expose public `get_alert_by_id()` for use cases.

---

### 3. ListAlertsUseCase ❌ METHOD MISSING

**Current Call**: `search_alerts()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

---

### 4. ResolveAlertUseCase ❌ METHOD MISSING

**Current Call**: `resolve_alert()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: Use `close_alert()` instead OR defer

**Note**: Service has `close_alert()` which accepts `resolution` parameter. May be semantically equivalent.

---

### 5. GetAlertStatisticsUseCase ❌ METHOD MISSING

**Current Call**: `get_alert_statistics()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

---

### 6. GetMyAlertsUseCase ❌ METHOD MISSING

**Current Call**: `get_analyst_alerts()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

**Note**: Service has `get_analyst_workload()` which returns statistics, but NOT the actual alert list.

---

### 7. GetOverdueAlertsUseCase ❌ METHOD MISSING

**Current Call**: `get_overdue_alerts()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: Use `get_sla_breached_alerts()` instead OR defer

**Note**: `get_sla_breached_alerts()` likely serves same purpose as `get_overdue_alerts()`. May be semantically equivalent.

---

### 8. GetAlertWorkflowStatusUseCase ❌ METHOD MISSING

**Current Call**: `get_alert_workflow_status()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

---

### 9. BulkAssignAlertsUseCase ❌ METHOD MISSING

**Current Call**: `bulk_assign_alerts()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

---

## AUDIT USE CASES (7 DEFERRED)

### 1. CreateAuditLogUseCase ❌ METHOD MISSING

**Current Call**: `create_audit_log()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

**Note**: Audit logs are created INTERNALLY by other services. AuditService is read-only.

---

### 2. GetAuditLogUseCase ❌ METHOD MISSING

**Current Call**: `get_audit_log_by_id()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

---

### 3. GetEntityAuditTrailUseCase ❌ METHOD MISSING

**Current Call**: `get_entity_audit_trail()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: Use `get_entity_history()` instead OR defer

**Note**: `get_entity_history()` exists and returns similar data structure. Use case may expect different return type.

---

### 4. ExportAuditLogsUseCase ❌ METHOD MISSING

**Current Call**: `export_audit_logs()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

**Note**: Service has `export_compliance_report()` which may serve similar purpose.

---

### 5. GenerateComplianceReportUseCase ❌ METHOD MISSING

**Current Call**: `generate_compliance_report()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: Use `export_compliance_report()` instead OR defer

**Note**: Service has `export_compliance_report()`. May be semantically equivalent.

---

### 6. SearchAuditByActionUseCase ❌ METHOD MISSING

**Current Call**: `search_by_action()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: Use `search_audit_logs(action=...)` instead OR defer

**Note**: `search_audit_logs()` accepts `action` parameter. May serve same purpose.

---

### 7. GetRecentUserActivityUseCase ❌ METHOD MISSING

**Current Call**: `get_recent_activity()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: Use `get_user_activity()` with date filter instead OR defer

**Note**: `get_user_activity()` accepts date range. Can be used for recent activity.

---

## USER USE CASES (7 DEFERRED)

### 1. UpdateUserUseCase ❌ METHOD MISSING

**Current Call**: `update_user()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

---

### 2. GetUserUseCase ❌ METHOD MISSING

**Current Call**: `get_user_by_id()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: Use `get_user_profile()` instead OR defer

**Note**: `get_user_profile()` exists and returns user data as dict. Use case may expect User entity.

---

### 3. ListUsersUseCase ❌ MULTIPLE METHODS MISSING

**Current Calls**:
- `get_users_by_role()`
- `get_users_by_status()`
- `get_users_by_role_and_status()`

**Canonical Methods**: NONE EXIST  
**Status**: METHODS NOT IMPLEMENTED  
**Action Required**: Use `list_users_by_role()` and `get_active_users()` as workarounds OR defer

**Note**: Service has:
- `list_users_by_role()` - can filter by role
- `get_active_users()` - can filter by active status
- But NO method for combined role+status filter
- And no `get_users_by_status()` for non-active statuses

---

### 4. ChangePasswordUseCase ⚠️ METHOD NAME MISMATCH

**Current Call**: `change_user_password()`  
**Canonical Method**: `change_user_password()` (EXISTS but wrong params)  
**Status**: PARAMETER MISMATCH  
**Action Required**: Fix use case to match service signature

**Service Signature**: `change_user_password(user_id, old_password, new_password)`  
**Use Case DTO**: Expects `ChangePasswordRequest(current_password, new_password)`  
**Mismatch**: Use case calls it correctly, but DTO naming inconsistency

---

### 5. GetUserStatisticsUseCase ❌ METHOD MISSING

**Current Call**: `get_user_statistics()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

---

### 6. LockUserUseCase ❌ METHOD MISSING

**Current Call**: `lock_user()`  
**Canonical Method**: DOES NOT EXIST  
**Status**: METHOD NOT IMPLEMENTED  
**Action Required**: DEFER until service method is implemented

---

## MODEL USE CASES (ALL DEFERRED)

### ❌ ENTIRE SERVICE NOT IMPLEMENTED

**Reason**: ModelService does not exist at all.

**Deferred Use Cases**:
1. CreateModelUseCase
2. UpdateModelUseCase
3. GetModelUseCase
4. ListModelsUseCase
5. PromoteModelUseCase
6. ArchiveModelUseCase
7. GetModelStatisticsUseCase

**Action Required**: Implement ModelService first, then implement use cases.

---

## SUMMARY

| Bounded Context | Total Use Cases | Implementable | Deferred | % Deferred |
|----------------|----------------|---------------|----------|-----------|
| Customer | 4 | 4 | 0 | 0% |
| Merchant | 10 | 3 | 7 | 70% |
| Transaction | 5 | 3 | 2 | 40% |
| Prediction | 11 | 0 | 11 | 100% |
| Alert | 13 | 4 | 9 | 69% |
| Audit | 11 | 4 | 7 | 64% |
| User | 10 | 3 | 7 | 70% |
| Model | 7 | 0 | 7 | 100% |
| **TOTAL** | **71** | **21** | **50** | **70%** |

---

## RECOMMENDED ACTIONS

### Immediate (Can be fixed now)
1. Rename `create_merchant()` → `onboard_merchant()` in CreateMerchantUseCase
2. Rename `update_merchant()` → `update_merchant_profile()` in UpdateMerchantUseCase
3. Use `get_entity_history()` instead of `get_entity_audit_trail()` in audit use cases
4. Use `search_audit_logs(action=...)` instead of `search_by_action()`

### Short-term (Add to Service Layer)
1. Add simple getter methods: `get_merchant_by_id()`, `get_transaction_by_id()`, `get_alert_by_id()`, `get_audit_log_by_id()`, `get_user_by_id()`
2. Add search methods: `search_merchants()`, `search_alerts()`
3. Add statistics methods: `get_merchant_statistics()`, `get_alert_statistics()`, `get_user_statistics()`

### Long-term (Architectural Changes)
1. Implement full PredictionRepository + update PredictionService to use it
2. Implement ModelService from scratch
3. Add missing user filtering: `get_users_by_status()`, `get_users_by_role_and_status()`
4. Add merchant deactivation lifecycle distinct from suspension

