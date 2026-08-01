# Preprocessing Validation Report

**Project:** Enterprise Fraud Detection - IEEE-CIS Dataset  
**Purpose:** Track every preprocessing stage with before/after statistics  
**Generated:** 2026-08-01

---

## Report Structure

Each preprocessing stage appends:
- Input shape (rows × columns)
- Output shape (rows × columns)
- Columns added (list)
- Columns removed (list)
- Memory usage (MB)
- Execution time (seconds)
- Null counts (before/after)
- Leakage verification status
- YAML config version used

---

## Preprocessing Stages

### Stage 0: Raw Data Load

**Timestamp:** TBD  
**Stage:** Data Loading  
**Config Version:** N/A

**Input:**
- Files: train_transaction.csv, train_identity.csv
- Location: backend/data/raw/

**Output:**
- Shape: 590,540 rows × 434 columns
- Memory: 2,513.97 MB
- Null counts: 115,523,073 (45.07%)

**Actions:**
- Loaded train_transaction.csv
- Loaded train_identity.csv
- Merged on TransactionID

**Leakage Check:** ✅ N/A (raw data)

---

### Stage 1: Feature Dropping

**Timestamp:** 2026-08-01  
**Stage:** Feature Dropping  
**Config Version:** preprocessing_config.yaml v2.0

**Input:**
- Shape: 590,540 rows × 434 columns
- Memory: 2513.97 MB
- Null counts: 115,523,073

**Output:**
- Shape: 590,540 rows × 431 columns
- Memory: 2500.46 MB
- Null counts: 114,997,250

**Actions:**
- Dropped identifier columns: 1
- Dropped extreme missing (>99.5%): 0
- Dropped constant features: 0
- Dropped duplicate features: 2
- **Total columns dropped:** 3

**Columns Dropped by Reason:**
- **Identifiers:** 1 columns
- **Duplicates:** 2 columns

**Performance:**
- Execution time: 35.19s
- Memory reduction: 13.52 MB (0.5%)
- Dimensionality reduction: 3 columns (0.7%)

**Leakage Check:** ✅ Safe - Feature dropping is a pre-split operation that uses only column-level statistics

---

---

### Stage 2: Feature Engineering

**Status:** ⏳ Not started  
**To be populated by Milestone 1C.2**

---

### Stage 3: Train/Val/Test Split

**Status:** ⏳ Not started  
**To be populated by Milestone 1C.3**

---

### Stage 4: Missing Value Imputation

**Status:** ⏳ Not started  
**To be populated by Milestone 1C.4**

---

### Stage 5: Categorical Encoding

**Status:** ⏳ Not started  
**To be populated by Milestone 1C.5**

---

### Stage 6: Feature Scaling

**Status:** ⏳ Not started  
**To be populated by Milestone 1C.6**

---

## Summary Statistics

**To be updated after all stages complete**

| Stage | Rows | Columns | Memory (MB) | Execution Time (s) |
|-------|------|---------|-------------|--------------------|
| 0. Raw Data | 590,540 | 434 | 2,513.97 | - |
| 1. Dropping | TBD | TBD | TBD | TBD |
| 2. Engineering | TBD | TBD | TBD | TBD |
| 3. Split | TBD | TBD | TBD | TBD |
| 4. Imputation | TBD | TBD | TBD | TBD |
| 5. Encoding | TBD | TBD | TBD | TBD |
| 6. Scaling | TBD | TBD | TBD | TBD |

---

## Leakage Verification Log

| Stage | Leakage Check | Status | Notes |
|-------|---------------|--------|-------|
| 0. Raw Data | N/A | ✅ | No preprocessing yet |
| 1. Dropping | Pre-split operation | ⏳ | To be verified |
| 2. Engineering | Row-level only | ⏳ | To be verified |
| 3. Split | Temporal ordering | ⏳ | To be verified |
| 4. Imputation | Fit on train only | ⏳ | To be verified |
| 5. Encoding | Fit on train only | ⏳ | To be verified |
| 6. Scaling | Fit on train only | ⏳ | To be verified |

---

**Report Version:** 1.0  
**Last Updated:** 2026-08-01  
**Status:** Template created, awaiting Stage 1 implementation
