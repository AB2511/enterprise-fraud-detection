# USE CASE FIXES REQUIRED
## Service Layer Completion Sprint - Implementation Checklist

**Generated**: 2026-07-08  
**Status**: Action items for implementing now-enabled use cases

---

## IMMEDIATE FIXES REQUIRED

### MERCHANT USE CASES

#### ✅ ALREADY WORKING (7)
1. `DeleteMerchantUseCase` - ✅ Correctly calls `deactivate_merchant()`
2. `GetMerchantUseCase` - ✅ Correctly calls `get_merchant_by_id()`
3. `ListMerchantsUseCase` - ✅ Correctly calls `search_merchants()`
4. `SuspendMerchantUseCase` - ✅ Correctly calls `suspend_merchant()`
5. `ReactivateMerchantUseCase` - ✅ Correctly calls `reactivate_merchant()`
6. `GetMerchantStatisticsUseCase` - ✅ Correctly calls `get_merchant_statistics()`
7. `SearchMerchantsByNameUseCase` - ✅ Correctly calls `search_merchants_by_name()`
8. `GetHighRiskMerchantsUseCase` - ✅ Correctly calls `get_high_risk_merchants()`

#### ❌ BROKEN - NEEDS FIX (2)

**1. CreateMerchantUseCase**
- **Issue**: Calls non-existent method `create_merchant()`
- **Fix**: Call `onboard_merchant()` instead
- **Parameter Mismatch**: DTO has `contact_email` and `business_registration` but service doesn't accept them
- **Additional Issue**: Service requires `mcc` parameter which DTO calls `merchant_category`
- **Solution**: 
  - Change method call from `create_merchant()` to `onboard_merchant()`
  - Map `request.merchant_category` to both `mcc` and `merchant_category` parameters
  - Drop `contact_email` and `business_registration` (not supported by domain entity)
  
**2. UpdateMerchantUseCase**
- **Issue**: Calls non-existent method `update_merchant()`
- **Fix**: Call `update_merchant_profile()` instead

---

### TRANSACTION USE CASES

#### ✅ NEED TO VERIFY (2)

**1. GetTransactionUseCase** - MAY ALREADY EXIST
- Check if this use case file exists and calls the correct method
- Should call: `get_transaction_by_id(transaction_id)`

**2. GetCustomerTransactionsUseCase** - MAY ALREADY EXIST
- Check if this use case file exists and calls the correct method
- Should call: `get_customer_transactions(customer_id, limit, offset)`
- Note: Returns tuple `(transactions, count)`

**ACTION**: Read `transaction_use_cases.py` and verify

---

### ALERT USE CASES

#### ✅ NEED TO VERIFY (9)

All alert use cases need verification:
1. `UpdateAlertUseCase` - should call `update_alert()`
2. `GetAlertUseCase` - should call `get_alert_by_id()`
3. `ListAlertsUseCase` - should call `search_alerts()`
4. `ResolveAlertUseCase` - should call `resolve_alert()`
5. `GetAlertStatisticsUseCase` - should call `get_alert_statistics()`
6. `GetMyAlertsUseCase` - should call `get_analyst_alerts()`
7. `GetOverdueAlertsUseCase` - should call `get_overdue_alerts()`
8. `GetAlertWorkflowStatusUseCase` - should call `get_alert_workflow_status()`
9. `BulkAssignAlertsUseCase` - should call `bulk_assign_alerts()`

**ACTION**: Read `alert_use_cases.py` and verify each use case

---

### AUDIT USE CASES

#### ❌ DELETE THIS USE CASE (1)

**CreateAuditLogUseCase**
- **Issue**: Violates audit architecture - audit logs should NEVER be created via use cases
- **Reason**: Audit logs are created INTERNALLY by other services as side effects
- **Action**: DELETE this use case entirely

#### ✅ NEED TO VERIFY (6)

1. `GetAuditLogUseCase` - should call `get_audit_log_by_id()`
2. `GetEntityAuditTrailUseCase` - should call `get_entity_audit_trail()`
3. `ExportAuditLogsUseCase` - should call `export_audit_logs()`
4. `GenerateComplianceReportUseCase` - should call `generate_compliance_report()`
5. `SearchAuditByActionUseCase` - should call `search_by_action()`
6. `GetRecentUserActivityUseCase` - should call `get_recent_activity()` or map to `get_user_activity()`

**ACTION**: Read `audit_use_cases.py` and verify each use case

---

### USER USE CASES

#### ✅ NEED TO VERIFY (7)

1. `UpdateUserUseCase` - should call `update_user()`
2. `GetUserUseCase` - should call `get_user_by_id()`
3. `ListUsersUseCase` - should call `get_users_by_role()`, `get_users_by_status()`, `get_users_by_role_and_status()`
4. `GetUserStatisticsUseCase` - should call `get_user_statistics()`
5. `LockUserUseCase` - should call `lock_user()`

**ACTION**: Read `user_use_cases.py` and verify each use case

---

## IMPLEMENTATION PLAN

### Step 1: Fix Broken Merchant Use Cases ✅ HIGH PRIORITY
1. Fix `CreateMerchantUseCase`:
   - Change `create_merchant()` → `onboard_merchant()`
   - Map `merchant_category` → `mcc` and `merchant_category`
   - Remove usage of `contact_email` and `business_registration`

2. Fix `UpdateMerchantUseCase`:
   - Change `update_merchant()` → `update_merchant_profile()`

### Step 2: Verify Transaction Use Cases
1. Read `transaction_use_cases.py`
2. Check if `GetTransactionUseCase` exists and works
3. Check if `GetCustomerTransactionsUseCase` exists and works
4. Fix any issues found

### Step 3: Verify Alert Use Cases
1. Read `alert_use_cases.py`
2. Verify all 9 alert use cases exist and call correct methods
3. Fix any issues found

### Step 4: Verify & Fix Audit Use Cases
1. Read `audit_use_cases.py`
2. DELETE `CreateAuditLogUseCase` if it exists
3. Verify remaining 6 use cases exist and call correct methods
4. Fix any issues found

### Step 5: Verify User Use Cases
1. Read `user_use_cases.py`
2. Verify all 7 user use cases exist and call correct methods
3. Fix any issues found

### Step 6: Run Tests
1. Run `pytest tests/unit/application -v` after each fix
2. Ensure all tests pass
3. Fix any test failures

### Step 7: Update Documentation
1. Update `APPLICATION_LAYER_STATUS.md` with final statistics
2. Mark all fixed use cases as ✅ IMPLEMENTED
3. Document any remaining limitations

---

## EXPECTED RESULTS

### Before Fixes
- Merchant: 70% implementable (7/10 working, 3 broken)
- Transaction: Unknown status
- Alert: Unknown status
- Audit: Unknown status
- User: Unknown status

### After Fixes
- Merchant: 100% implementable (10/10 working)
- Transaction: 100% implementable (5/5 working)
- Alert: 100% implementable (13/13 working)
- Audit: 91% implementable (10/11 - 1 deleted as invalid)
- User: 90% implementable (9/10 - 1 has repository limitation)

### Overall
- **Before**: 30% application layer complete
- **After**: 68%+ application layer complete
- **Improvement**: +38 percentage points

---

## VALIDATION CHECKLIST

After completing all fixes, verify:
- [ ] All use cases import successfully
- [ ] All service method calls resolve
- [ ] No AttributeError exceptions
- [ ] No missing service methods
- [ ] All tests pass
- [ ] Audit logs are created for state-changing operations
- [ ] DTOs match service method signatures
- [ ] Use cases return correct response types

---

## NOTES

### Merchant Entity Limitations
The `Merchant` domain entity does NOT have:
- `contact_email` field
- `business_registration` field

These fields were in the DTO but are not supported by the domain model. The use case should drop these fields or they need to be added to the domain entity first (which violates our "domain is frozen" rule).

**Decision**: Drop these fields from the use case implementation.

### Audit Architecture
Audit logs are created as side effects by application services. There should be NO use case for creating audit logs directly. Any such use case violates the audit architecture and should be deleted.

### Repository Limitations
Some service methods have limitations due to repository constraints:
- `get_merchant_statistics()` - only includes high-risk merchants
- `search_merchants_by_name()` - exact match only (no fuzzy search)
- `get_users_by_status()` - only works for "active" status

These limitations are acceptable and documented in the SERVICE_COMPLETION_REPORT.md.
