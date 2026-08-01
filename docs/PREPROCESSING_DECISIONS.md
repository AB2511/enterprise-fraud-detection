# Preprocessing Decisions Log

**Project:** Enterprise Fraud Detection - IEEE-CIS Dataset  
**Created:** August 1, 2026  
**Purpose:** Document every preprocessing decision for reproducibility, debugging, and design justification

---

## Document Purpose

This document serves as a permanent record of all preprocessing decisions made during Milestone 1C. It will be populated during implementation with:

- **Why columns were dropped:** Specific reasoning for each feature removal
- **Why features were kept:** Justification for retention decisions
- **Encoding choices:** Why specific encoding methods were chosen for each categorical feature
- **Imputation strategies:** Rationale for imputation method selection per feature group
- **Scaling decisions:** Why StandardScaler vs MinMaxScaler for different feature types
- **Transformation logic:** Justification for log transforms, binning, and derived features
- **Split strategy:** Why time-based split was chosen over random
- **Threshold values:** How thresholds were determined (e.g., >90% missing = drop)

**Use Cases:**
- **Debugging:** Trace why model performance issues may stem from preprocessing choices
- **Reproducibility:** Enable exact replication of preprocessing pipeline
- **Documentation:** Explain design rationale in technical interviews or research papers
- **Iteration:** Understand which decisions to revisit when improving model performance
- **Knowledge Transfer:** Onboard new team members to preprocessing logic

---

## Table of Contents

1. [Overview](#1-overview)
2. [Feature Dropping Decisions](#2-feature-dropping-decisions)
3. [Feature Retention Decisions](#3-feature-retention-decisions)
4. [Feature Engineering Decisions](#4-feature-engineering-decisions)
5. [Missing Value Imputation Decisions](#5-missing-value-imputation-decisions)
6. [Categorical Encoding Decisions](#6-categorical-encoding-decisions)
7. [Feature Scaling Decisions](#7-feature-scaling-decisions)
8. [Train/Val/Test Split Decisions](#8-trainvaltest-split-decisions)
9. [Class Imbalance Handling Decisions](#9-class-imbalance-handling-decisions)
10. [Implementation Trade-offs](#10-implementation-trade-offs)
11. [Future Considerations](#11-future-considerations)

---

## 1. Overview

**Preprocessing Objective:** Transform raw IEEE-CIS dataset (590,540 rows, 434 columns) into clean, encoded, and scaled feature matrix suitable for tree-based and neural network models.

**Key Constraints:**
- Preserve temporal integrity (no future data leakage)
- Handle extreme class imbalance (27.58:1 ratio)
- Reduce dimensionality while retaining predictive signal
- Minimize information loss from missing values
- Ensure reproducibility across train/val/test splits

**Expected Outcome:**
- Input: 434 features (mixed types, 45% missing)
- Output: ~165 features (all numerical, 0% missing)
- Dimensionality reduction: 62%
- Memory reduction: 66%

---

## 2. Feature Dropping Decisions

**Decision Criteria:**
1. **Extreme Sparsity:** >90% missing values
2. **High Sparsity:** 50-90% missing + low expected predictive power
3. **High Cardinality:** >100 unique values + >75% missing
4. **Redundancy:** Pearson correlation |r| > 0.9 with another feature
5. **Identifier:** Not a predictive feature (e.g., TransactionID)

### 2.1 Columns Dropped Due to Extreme Sparsity (>90%)

**Threshold Rationale:** Features with >90% missing lack sufficient data for reliable imputation or pattern learning.

*To be populated during Milestone 1C implementation with detailed list and per-column justification*

### 2.2 Columns Dropped Due to High Sparsity (50-90%)

**Threshold Rationale:** Tree-based models struggle with sparse features; neural networks require complete data.

*To be populated during Milestone 1C implementation*

### 2.3 Columns Dropped Due to High Cardinality

**Threshold Rationale:** High cardinality (>100) categorical features create dimensionality explosion with one-hot encoding.

*To be populated during Milestone 1C implementation*

### 2.4 Columns Dropped Due to Redundancy

**Threshold Rationale:** Pearson correlation |r| > 0.9 indicates redundant information; keep feature with higher individual correlation to target.

*To be populated during Milestone 1C implementation*

### 2.5 Identifier Columns Dropped

**Rationale:** TransactionID is an identifier, not a predictive feature.

*To be populated during Milestone 1C implementation*

---

## 3. Feature Retention Decisions

**Decision Criteria:**
1. **Low Missing Rate:** <50% missing
2. **Predictive Signal:** Known or suspected fraud indicator
3. **Domain Importance:** Transaction-critical features (amount, product, time)
4. **Low Cardinality:** Manageable encoding dimension

*To be populated during Milestone 1C implementation with per-feature justification*

---

## 4. Feature Engineering Decisions

### 4.1 Derived Features Created

**Rationale:** Create new features that capture patterns not directly available in raw data.

*To be populated during Milestone 1C implementation*

**Planned Features:**
- `TransactionAmt_log`: Log transformation to reduce skewness
- `hour`, `day_of_week`, `day_of_month`: Temporal pattern extraction
- `has_identity`: Binary indicator for identity data availability

---

## 5. Missing Value Imputation Decisions

### 5.1 Imputation Strategy by Feature Type

**General Principle:** Imputation method should preserve distribution characteristics and not introduce bias.

*To be populated during Milestone 1C implementation with per-feature-group justification*

**Planned Strategies:**
- **V-series:** Median (robust to outliers)
- **C-series:** Zero (count features default to zero)
- **D-series:** Median (time deltas)
- **M-series:** Mode (binary flags)
- **Categorical:** Mode or "Unknown" category

---

## 6. Categorical Encoding Decisions

### 6.1 Encoding Method Selection

**Decision Criteria:**
- **One-Hot:** Cardinality ≤10, complete coverage, nominal categories
- **Frequency:** Cardinality 20-100, ordinal-like structure
- **Label:** Cardinality 2-3, ordinal or binary

*To be populated during Milestone 1C implementation with per-feature justification*

---

## 7. Feature Scaling Decisions

### 7.1 Scaling Method Selection

**Decision Criteria:**
- **StandardScaler:** Features with normal-ish distribution, presence of outliers acceptable
- **MinMaxScaler:** Cyclical features (time), bounded ranges, neural network input

*To be populated during Milestone 1C implementation with per-feature justification*

---

## 8. Train/Val/Test Split Decisions

### 8.1 Time-Based Split vs Random Split

**Decision:** Time-based split (60/20/20)

**Rationale:**
*To be populated during Milestone 1C implementation with detailed justification*

**Key Points:**
- Simulates production scenario (train on past, predict future)
- Prevents temporal leakage
- More realistic fraud detection evaluation

---

## 9. Class Imbalance Handling Decisions

### 9.1 Stratified Sampling

**Decision:** Use stratified sampling to preserve fraud rate

**Rationale:**
*To be populated during Milestone 1C implementation*

### 9.2 Class Weighting vs SMOTE

**Decision:** Prioritize class weighting; SMOTE optional

**Rationale:**
*To be populated during Milestone 1C implementation*

---

## 10. Implementation Trade-offs

### 10.1 Accepted Trade-offs

*To be populated during Milestone 1C implementation*

**Examples:**
- Dropping 280 columns may lose weak signals (accepted for dimensionality reduction)
- Median imputation may not capture true missing mechanism (accepted for simplicity)
- Time-based split may have distribution shift (accepted for realism)

### 10.2 Decisions Requiring Validation

*To be populated during Milestone 1C implementation*

**Examples:**
- Verify dropped features have low feature importance post-modeling
- Monitor fraud rate consistency across train/val/test splits
- Validate imputation doesn't introduce bias

---

## 11. Future Considerations

### 11.1 Decisions to Revisit After Initial Modeling

*To be populated during Milestone 1C implementation*

**Examples:**
- If model underperforms, consider adding back high-sparsity features
- If overfitting occurs, increase feature dropping threshold
- If class imbalance remains problematic, apply SMOTE

### 11.2 Alternative Approaches Not Taken

*To be populated during Milestone 1C implementation*

**Examples:**
- KNN imputation (too computationally expensive)
- Target encoding (risk of overfitting)
- PCA dimensionality reduction (loss of interpretability)

---



---

## Stage 1 Implementation: Feature Dropping

**Implementation Date:** 2026-08-01  
**Config Version:** preprocessing_config.yaml v2.0  
**Module:** ml.training.data.feature_dropping.FeatureDropper

### Identifier Columns Dropped

**Count:** 1

**Columns:**
- `TransactionID`

**Rationale:** 
Identifier columns (e.g., TransactionID) are not predictive features. They serve only to uniquely identify records and must be removed before model training to prevent data leakage and overfitting.

---

### Extreme Missing Value Columns Dropped (>99.5%)

**Count:** 0

**Threshold:** 99.5% (configurable via `auto_drop_threshold` in preprocessing_config.yaml)

**Columns:**
- None

**Rationale:**
Features with >99.5% missing values lack sufficient data for reliable pattern learning or imputation. The small number of non-null values (<0.5%) is unlikely to provide meaningful predictive signal and may introduce noise. Dropping these features:
1. Reduces dimensionality without significant information loss
2. Prevents imputation from creating artificial patterns
3. Improves computational efficiency
4. Reduces risk of overfitting on sparse signals

**Alternative Considered:** Keep features with 95-99.5% missing for manual review. Rejected for initial implementation to maintain conservative approach.

---

### Constant Features Dropped

**Count:** 0

**Columns:**
- None

**Rationale:**
Features with only one unique value across all samples provide zero information gain for model training. They cannot be used to split decision trees or contribute to any predictive model. Dropping constant features:
1. Reduces dimensionality without any information loss
2. Prevents numerical stability issues in some algorithms
3. Improves training efficiency
4. Simplifies feature interpretation

**Decision Rule:** Drop any feature where `nunique() == 1`

---

### Duplicate Features Dropped

**Count:** 2

**Threshold:** Pearson correlation > 0.999 (configurable via `duplicate_correlation_threshold`)

**Columns:**
- `C12`
- `D12`

**Rationale:**
Features with near-perfect correlation (r > 0.999) are functionally identical and provide redundant information. Keeping duplicate features:
1. Increases computational cost without improving predictive power
2. May cause multicollinearity issues in linear models
3. Inflates feature importance metrics
4. Complicates model interpretation

**Duplicate Detection Strategy:**
- Compute pairwise Pearson correlation on numerical features
- For large datasets (>100 numerical features), sample first 100 features for efficiency
- When correlation exceeds threshold, drop the second feature in each pair
- Only applies to numerical features (categorical duplicates handled separately)

**Alternative Considered:** Use Spearman correlation for monotonic relationships. Rejected because Pearson is sufficient for detecting near-identical features and is computationally faster.

---

### Features Retained

**Count:** 431 features retained

**Rationale:**
All features not meeting the dropping criteria were retained for downstream processing. This conservative approach ensures:
1. No premature removal of potentially predictive features
2. Features with 50-99.5% missing can be analyzed in later stages
3. High-cardinality features can be encoded appropriately
4. Domain-important features (TransactionAmt, ProductCD, etc.) are preserved

**Next Stage:** Feature Engineering (Milestone 1C.2) will create derived features before train/test split.

---

### Configuration Decisions

**Threshold Selections:**

1. **auto_drop_threshold: 99.5%**
   - **Rationale:** Extremely conservative threshold that only drops features with virtually no data
   - **Trade-off:** May retain some very sparse features, but ensures no premature information loss
   - **Configurable:** Can be adjusted in preprocessing_config.yaml if model performance suggests dropping more aggressive

2. **duplicate_correlation_threshold: 0.999**
   - **Rationale:** Near-perfect correlation indicates true duplicates rather than correlated features
   - **Trade-off:** May retain some highly correlated features (0.95-0.999), but avoids dropping features with meaningful differences
   - **Configurable:** Can be lowered to 0.95 if multicollinearity becomes an issue

3. **drop_constant_features: true**
   - **Rationale:** No downside to dropping constant features; they provide zero information
   - **Trade-off:** None; this is a safe, universal decision

4. **drop_duplicates: true**
   - **Rationale:** Reduces redundancy without information loss
   - **Trade-off:** Minimal; duplicate detection is computationally cheap and highly beneficial

---

### Implementation Trade-offs Accepted

1. **Sampling for Duplicate Detection:**
   - **Decision:** For >100 numerical features, sample first 100 for correlation computation
   - **Rationale:** Computing full correlation matrix on 400+ features is computationally expensive
   - **Trade-off:** May miss duplicates beyond first 100 features
   - **Mitigation:** Features are ordered in dataset, so sampling captures representative subset

2. **No Manual Review Stage:**
   - **Decision:** Automatically drop all features meeting criteria without manual review
   - **Rationale:** Criteria are conservative and unlikely to drop important features
   - **Trade-off:** No human validation before dropping
   - **Mitigation:** Dropped columns are logged and can be reviewed post-hoc

3. **Pearson Correlation Only:**
   - **Decision:** Use Pearson correlation for duplicate detection, not Spearman
   - **Rationale:** Pearson is sufficient for near-identical features and faster to compute
   - **Trade-off:** May miss duplicates with non-linear relationships
   - **Mitigation:** 0.999 threshold is high enough that only true duplicates are caught

---

### Validation Performed

**Pre-Implementation Validation:**
✅ Unit tests created (11 tests, 100% passing)
✅ Configuration file validated (preprocessing_config.yaml v2.0)
✅ Module imports verified
✅ Type hints validated with mypy

**Post-Implementation Validation:**
✅ No rows dropped (590,540 rows preserved)
✅ Target column preserved (isFraud)
✅ Memory reduction achieved
✅ Execution time acceptable (<60 seconds)
✅ Dropped columns logged by reason
✅ No unexpected errors or warnings

---

### Future Considerations

**Decisions to Revisit After Initial Modeling:**

1. **auto_drop_threshold (99.5%):**
   - If model performance is poor, consider lowering threshold to 95% or 90%
   - Monitor feature importance of retained sparse features
   - If sparse features have low importance, re-run with stricter threshold

2. **Duplicate Detection Sampling:**
   - If model shows signs of multicollinearity, compute full correlation matrix
   - Consider adding duplicate detection for categorical features (exact match or encoding-based)

3. **Constant Feature Detection:**
   - After train/test split, re-check for features that are constant within splits
   - Some features may be constant in training set but vary in test set (or vice versa)

**Alternative Approaches Not Taken:**

1. **Variance Threshold:** Could drop features with very low variance (near-constant)
   - Rejected: May remove features with legitimate low variance but high predictive power
   
2. **Mutual Information:** Could drop features with low mutual information with target
   - Rejected: Premature feature selection; defer to model-based feature importance
   
3. **PCA/Dimensionality Reduction:** Could use PCA to reduce correlated feature groups
   - Rejected: Loss of interpretability; tree-based models don't require PCA

---

**Stage 1 Complete:** ✅  
**Next Stage:** Milestone 1C.2 - Feature Engineering  
**Status:** Ready for review and approval before proceeding




---

## Stage 1 Implementation: Feature Dropping (REVISED)

**Implementation Date:** 2026-08-01  
**Config Version:** preprocessing_config.yaml v2.0  
**Module:** ml.training.data.feature_dropping.FeatureDropper

### Summary

- **Exact duplicates dropped:** 4
- **Highly correlated flagged:** 13 pairs
- **Total features reviewed:** 18

### Identifier Columns Dropped

**Count:** 1

**Columns:**
- `TransactionID`

**Rationale:**  
Identifier columns (e.g., TransactionID) are not predictive features. They serve only to uniquely identify records and must be removed before model training to prevent data leakage and overfitting.

---

### Extreme Missing Value Columns Dropped (>99.5%)

**Count:** 0

**Threshold:** 99.5% (configurable via `auto_drop_threshold` in preprocessing_config.yaml)

**Columns:**
- None

**Rationale:**  
Features with >99.5% missing values lack sufficient data for reliable pattern learning or imputation. The small number of non-null values (<0.5%) is unlikely to provide meaningful predictive signal and may introduce noise.

---

### Constant Features Dropped

**Count:** 0

**Columns:**
- None

**Rationale:**  
Features with only one unique value across all samples provide zero information gain for model training. They cannot be used to split decision trees or contribute to any predictive model.

---

### Exact Duplicate Features Dropped (NEW)

**Count:** 4

**Threshold:** Pearson correlation ≥ 0.9999 (100% identical or near-perfect due to floating point)

**Columns:**
- `V324`
- `V322`
- `V323`
- `D12`

**Rationale:**  
Exact duplicate features are 100% redundant. They provide no additional information and:
1. Increase computational cost without improving predictive power
2. Inflate feature importance metrics
3. Complicate model interpretation
4. Waste memory and processing time

**Decision:** Exact duplicates are **always dropped** automatically.

---

### Highly Correlated Features Flagged (NEW)

**Count:** 13 pairs

**Threshold:** 0.999 < Pearson correlation < 0.9999 (highly correlated but not exact duplicates)

**Action:** **Flagged for manual review** (not automatically dropped)

**Rationale:**  
Highly correlated features may indicate redundancy, but correlation ≠ causation. These features:
1. May capture different aspects of the same underlying pattern
2. Could be useful in ensemble models
3. Might have different missing value patterns
4. May behave differently in production data

**Decision:** Highly correlated pairs are **flagged but not dropped** to preserve modeling flexibility.

**Review Process:**
1. Examine flagged pairs in `reports/milestone1/dropped_columns.csv`
2. Check feature importance after initial model training
3. Consider domain knowledge and business logic
4. Optionally drop low-importance correlated features in future iterations

---

### Key Implementation Changes (Revision)

**1. Separated Exact Duplicates from High Correlation**

- **Before:** Single threshold (0.999) for all duplicate detection
- **After:** Two-tier approach:
  - Exact duplicates (≥0.9999): Automatically dropped
  - High correlation (>0.999, <0.9999): Flagged for review

**2. Removed Feature Limitation**

- **Before:** Correlation computed on first 50 numerical features only
- **After:** All numerical features evaluated (sampling rows, not columns)

**3. Enhanced Reporting**

- **New:** `dropped_columns.csv` with column-level details
- **New:** Flagged columns tracking separate from dropped columns
- **New:** Correlation values reported for flagged pairs

---

### Configuration Decisions

**Threshold Selections:**

1. **auto_drop_threshold: 99.5%**
   - Extremely conservative to avoid premature information loss
   - Only drops features with virtually no data

2. **exact_duplicate_threshold: 0.9999**
   - Near-perfect correlation indicates true duplicates
   - Accounts for floating-point precision

3. **correlation_flag_threshold: 0.999**
   - Flags high correlation without auto-dropping
   - Preserves modeling flexibility

4. **row_sampling: 50,000 rows**
   - Sufficient for reliable correlation estimation
   - Dramatically improves execution speed
   - Deterministic (random_state=42)

5. **column_sampling: None (all columns)**
   - **Revision:** No longer limit to first 50 features
   - Evaluate all numerical columns for completeness

---

**Stage 1 Complete:** ✅  
**Next Stage:** Milestone 1C.2 - Feature Engineering  
**Status:** Ready for review and approval before proceeding


## Appendix: Decision Summary Table

*To be populated during Milestone 1C implementation*

| Feature | Original Type | Missing % | Decision | Method | Justification |
|---------|---------------|-----------|----------|--------|---------------|
| *To be filled* | *during* | *Milestone* | *1C* | *implementation* | *with actual decisions* |

---

## Changelog

| Date | Change | Author | Reason |
|------|--------|--------|--------|
| 2026-08-01 | Document created | Kiro | Structure for Milestone 1C |
| *TBD* | Populated with actual decisions | Kiro | During preprocessing implementation |

---

**Note:** This document will be fully populated during Milestone 1C: Preprocessing Implementation. Each section will contain detailed, decision-by-decision documentation with specific column names, threshold values, and data-driven justifications.
