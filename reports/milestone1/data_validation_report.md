# Milestone 1A.5: Real Dataset Validation Report

**Generated:** Automated validation of IEEE-CIS Fraud Detection dataset

---

## 1. Dataset Overview

### Merged Dataset Statistics

- **Total Rows:** 590,540
- **Total Columns:** 434
- **Memory Footprint:** 2513.97 MB

### Source Tables

- **Transaction Table:** 590,540 rows, 394 columns
- **Identity Table:** 144,233 rows, 41 columns
- **Merge Key:** TransactionID
- **Rows Lost in Merge:** 0

---

## 2. Target Variable Analysis

- **Target Column:** `isFraud`
- **Total Transactions:** 590,540
- **Fraud Cases:** 20,663
- **Legitimate Cases:** 569,877
- **Fraud Rate:** 0.0350 (3.50%)

### Class Imbalance

The dataset exhibits **significant class imbalance** with fraud cases representing only 3.50% of transactions.
This ~2858.0:1 imbalance ratio will require:
- Stratified sampling in train/val/test splits
- Class-weighted loss functions or oversampling techniques
- Careful selection of evaluation metrics (precision, recall, F1, AUC-ROC over accuracy)

---

## 3. Missing Value Analysis

### Overall Missing Statistics

- **Columns with Missing Values:** 414 / 434 (95.4%)
- **Total Missing Values:** 115,523,073
- **Overall Missing Rate:** 0.4507 (45.07%)

### Top 20 Columns with Highest Missing Values

| Rank | Column | Missing Count | Missing % |
|------|--------|---------------|-----------|
| 1 | `id_24` | 585,793 | 99.20% |
| 2 | `id_25` | 585,408 | 99.13% |
| 3 | `id_07` | 585,385 | 99.13% |
| 4 | `id_08` | 585,385 | 99.13% |
| 5 | `id_21` | 585,381 | 99.13% |
| 6 | `id_26` | 585,377 | 99.13% |
| 7 | `id_27` | 585,371 | 99.12% |
| 8 | `id_23` | 585,371 | 99.12% |
| 9 | `id_22` | 585,371 | 99.12% |
| 10 | `dist2` | 552,913 | 93.63% |
| 11 | `D7` | 551,623 | 93.41% |
| 12 | `id_18` | 545,427 | 92.36% |
| 13 | `D13` | 528,588 | 89.51% |
| 14 | `D14` | 528,353 | 89.47% |
| 15 | `D12` | 525,823 | 89.04% |
| 16 | `id_04` | 524,216 | 88.77% |
| 17 | `id_03` | 524,216 | 88.77% |
| 18 | `D6` | 517,353 | 87.61% |
| 19 | `id_33` | 517,251 | 87.59% |
| 20 | `id_09` | 515,614 | 87.31% |

### Missing Value Insights

- **Columns with >90% missing:** 12
- **Columns with >50% missing:** 214
- **Columns with >10% missing:** 322
- **Columns with no missing:** 20

**Implication:** High missing rates in many columns suggest:
- Optional features (e.g., identity columns only available for subset of transactions)
- Sparse categorical variables
- Need for imputation strategy or feature selection

---

## 4. Feature Type Distribution

### Column Data Types

- **Numerical Features (int64, float64):** 403
- **Categorical Features (object):** 31
- **Total Features:** 434

### Data Type Breakdown

| Data Type | Count |
|-----------|-------|
| `float64` | 399 |
| `object` | 31 |
| `int64` | 4 |

---

## 5. Data Quality Checks

### Duplicate TransactionIDs

- **Duplicate Count:** 0
- **Status:** ✓ PASSED - No duplicates

### Merge Integrity

- **Transaction rows before merge:** 590,540
- **Merged rows:** 590,540
- **Rows lost:** 0
- **Status:** ✓ PASSED - No rows lost (left join preserves all transactions)

---

## 6. Comparison with Synthetic Testing

During Milestone 1A development, all tests used synthetic in-memory data.
Below is a comparison between **synthetic assumptions** and **real data reality:**

| Aspect | Synthetic Data | Real Data | Match? |
|--------|----------------|-----------|--------|
| **Rows** | 1,000 | 590,540 | ✗ 590x larger |
| **Columns** | 14 | 434 | ✗ 31x more features |
| **Transaction Cols** | 10 | 394 | ✗ 39x more |
| **Identity Cols** | 5 | 41 | ✗ 8x more |
| **Fraud Rate** | ~50% (balanced) | 3.50% | ✗ Highly imbalanced |
| **Missing Values** | 5-30% sparse | 45.07% | ✗ More missing |
| **Memory (MB)** | ~0.1 MB | 2513.97 MB | ✗ 25,000x larger |
| **Schema Valid** | ✓ | ✓ | ✓ Match |
| **No Duplicates** | ✓ | ✓ | ✓ Match |

### Key Differences

1. **Scale:** Real dataset is 590x larger with 31x more features
2. **Class Imbalance:** Synthetic was balanced (50/50), real is highly imbalanced (3.5% fraud)
3. **Feature Space:** Real dataset has 434 columns vs 14 in synthetic
4. **Missing Values:** Real data has extensive missingness (45% overall)
5. **Memory Requirements:** Real data requires ~2.5 GB in memory vs <1 MB for synthetic

### Invalid Assumptions from Synthetic Testing

The following assumptions from synthetic testing **do not hold** for real data:

❌ **Assumption:** Fraud rate is balanced (~50%)
- **Reality:** Fraud rate is 3.5% (20,663 / 590,540)
- **Impact:** Requires stratified splitting and class-aware evaluation metrics

❌ **Assumption:** Dataset fits comfortably in memory
- **Reality:** 2.5 GB memory footprint
- **Impact:** May require chunked processing or memory optimization for larger feature sets

❌ **Assumption:** Most columns have data
- **Reality:** 414 of 434 columns have missing values; some >99% missing
- **Impact:** Requires aggressive feature selection and imputation strategy

❌ **Assumption:** Feature engineering will be simple
- **Reality:** 434 columns with complex naming (V1-V339, C1-C14, D1-D15, M1-M9, id_*, card*, addr*, dist*, etc.)
- **Impact:** Need domain knowledge or automated feature selection

✓ **Valid Assumptions:**
- Schema validation works correctly
- Merge on TransactionID is valid
- No duplicate TransactionIDs
- Data loading and validation logic is correct

---

## 7. Readiness Assessment

### ✅ Milestone 1A.5: COMPLETE

**Status:** Real dataset successfully loaded, merged, validated, and analyzed.

**Deliverables:**
- ✓ Real transaction data loaded (590,540 rows)
- ✓ Real identity data loaded (144,233 rows)
- ✓ Datasets merged on TransactionID (434 columns)
- ✓ Schema validation passed
- ✓ No duplicate TransactionIDs
- ✓ Fraud rate calculated (3.50%)
- ✓ Missing value analysis complete (45% overall missing)
- ✓ Feature type distribution analyzed (399 float, 31 object, 4 int)
- ✓ Memory footprint measured (2.5 GB)
- ✓ Dataset summary JSON generated
- ✓ Comparison with synthetic assumptions documented

### 🚀 Ready for Milestone 1B

**Prerequisites met:**
- Real dataset validated and accessible
- Data quality confirmed
- Schema expectations established
- Class imbalance identified
- Missing value patterns understood

**Next Steps (Milestone 1B - Preprocessing):**
- Handle missing values (imputation strategy)
- Feature type conversion and encoding
- Stratified train/validation/test split (80/10/10)
- Feature selection (reduce 434 columns)
- Data normalization/scaling

---

## 8. Recommendations

Based on real data analysis, the following strategies are recommended:

### Data Preprocessing
1. **Missing Values:** Drop columns with >95% missing, impute remainder
2. **Feature Selection:** Reduce from 434 to manageable subset (~50-100 features)
3. **Memory Optimization:** Convert float64 to float32 where appropriate

### Model Training
1. **Class Imbalance:** Use SMOTE, class weights, or focal loss
2. **Evaluation Metrics:** Focus on precision, recall, F1, AUC-ROC (not accuracy)
3. **Validation Strategy:** Stratified K-fold or time-based split

### Infrastructure
1. **Memory:** Ensure at least 4-8 GB RAM available for training
2. **Storage:** Dataset requires ~1.3 GB on disk (compressed CSVs)
3. **Processing:** Consider chunked processing for feature engineering

---

**End of Report**