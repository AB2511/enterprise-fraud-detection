# Milestone 1B: Exploratory Data Analysis & Preprocessing Strategy

**Dataset:** IEEE-CIS Fraud Detection  
**Date:** August 1, 2026  
**Status:** Analysis Complete (No Preprocessing Implemented)

---

## Executive Summary

Comprehensive exploratory data analysis performed on 590,540 real fraud transactions with 434 features. Key findings reveal significant class imbalance (3.5% fraud rate), extensive missing values (45% overall), and high feature dimensionality requiring aggressive preprocessing strategy.

**Critical Insights:**
- **Class Imbalance:** 27.58:1 ratio (legitimate:fraud)
- **Missing Values:** 12 columns >90% missing, 202 columns >50% missing
- **Identity Coverage:** Only 24.42% of transactions have identity data
- **Fraud Signal:** Transactions WITH identity data have 3.7x higher fraud rate
- **Feature Groups:** V-series (339 cols), C-series (14), D-series (15), M-series (9)

---

## 1. Target Variable Analysis

### Distribution

| Metric | Value |
|--------|-------|
| **Total Transactions** | 590,540 |
| **Fraud Cases** | 20,663 (3.50%) |
| **Legitimate Cases** | 569,877 (96.50%) |
| **Imbalance Ratio** | 27.58:1 |

![Target Distribution](plots/01_target_distribution.png)

### Implications for Modeling

1. **Stratified Sampling Required:** Must maintain fraud rate across train/val/test splits
2. **Class Weighting:** Model loss functions must account for imbalance
3. **Evaluation Metrics:** Accuracy is misleading; use precision, recall, F1, AUC-ROC
4. **Resampling Consideration:** SMOTE or undersampling may be beneficial
5. **Threshold Tuning:** Default 0.5 threshold will not be optimal

---

## 2. Transaction Amount Analysis

### Distribution Statistics

| Metric | Value |
|--------|-------|
| **Mean** | $135.03 |
| **Median** | $68.77 |
| **Std Dev** | $239.16 |
| **Min** | $0.25 |
| **Max** | $31,937.39 |
| **Skewness** | 14.37 (highly right-skewed) |
| **Kurtosis** | 1,123.96 (extreme outliers) |

![Transaction Amount](plots/02_transaction_amount.png)

###
 Key Observations

1. **Heavy Right Skew:** Distribution is highly skewed (skewness=14.37)
2. **Extreme Outliers:** Kurtosis of 1,123 indicates extreme tail behavior
3. **Median < Mean:** Confirms right skew; median ($68.77) is half of mean ($135.03)
4. **Log Transformation:** Required for normalization and model stability

### Recommendation
- Apply `log1p(TransactionAmt)` transformation before training
- Detect and cap extreme outliers (>$10,000)
- Consider separate handling for micro-transactions (<$1)

---

## 3. Product Code Analysis

### Distribution by ProductCD

| Product | Count | Percentage | Fraud Rate |
|---------|-------|------------|------------|
| **W** | 439,670 | 74.45% | 2.04% |
| **C** | 68,519 | 11.60% | 11.69% ⚠️ |
| **R** | 37,699 | 6.38% | 3.78% |
| **H** | 33,024 | 5.59% | 4.77% |
| **S** | 11,628 | 1.97% | 5.90% |

![Product CD](plots/03_product_cd.png)

### Key Insights

1. **ProductCD "C" has 5.7x higher fraud rate** than "W" (11.69% vs 2.04%)
2. **Product "W" dominates** (74.45% of transactions)
3. **Strong predictive signal:** ProductCD should be encoded and retained
4. **No missing values:** Complete coverage (0% missing)

### Recommendation
- **Keep:** Encode as categorical feature (one-hot or target encoding)
- **Stratify splits** by ProductCD to ensure proportional representation

---

## 4. Categorical Features Analysis

### Cardinality Overview

**Total Categorical Columns:** 31

| Cardinality Category | Count | Examples |
|---------------------|-------|----------|
| **High (>100)** | 3 | DeviceInfo (1,786), id_33 (260), id_31 (130) |
| **Medium (20-100)** | 3 | id_30 (75), R_emaildomain (60), P_emaildomain (59) |
| **Low (<20)** | 25 | ProductCD (5), card4/6 (4), M-series (2-3) |

### High-Cardinality Columns

| Column | Unique Values | Missing % | Issue |
|--------|---------------|-----------|-------|
| DeviceInfo | 1,786 | 79.91% | Very high cardinality + sparse |
| id_33 | 260 | 87.59% | High cardinality + sparse |
| id_31 | 130 | 76.25% | High cardinality + sparse |

###
 Email Domains

| Column | Unique Values | Missing % | Note |
|--------|---------------|-----------|------|
| P_emaildomain | 59 | 15.99% | Purchaser email (good coverage) |
| R_emaildomain | 60 | 76.75% | Recipient email (sparse) |

### Recommendation by Column

| Column | Action | Justification |
|--------|--------|---------------|
| **DeviceInfo** | DROP | High cardinality (1,786) + 79.91% missing |
| **id_33** | DROP | High cardinality (260) + 87.59% missing |
| **id_31** | DROP | High cardinality (130) + 76.25% missing |
| **P_emaildomain** | KEEP + Encode | Good coverage (84%), moderate cardinality (59) |
| **R_emaildomain** | DROP | Sparse (76.75% missing) + duplicate signal with P |
| **ProductCD** | KEEP + One-Hot | Strong fraud signal, low cardinality (5) |
| **card4, card6** | KEEP + One-Hot | Low cardinality (4), minimal missing |
| **M-series (M1-M9)** | KEEP + Binary | Low cardinality (2-3), moderate predictive power |
| **id_30, id_34** | DROP | High missing rate (>86%) |

---

## 5. Numerical Features Analysis

### Summary Statistics (Sample of 10)

| Column | Mean | Std | Skewness | Kurtosis | Outliers % |
|--------|------|-----|----------|----------|------------|
| TransactionID | 3,282,269.50 | 170,474.36 | 0.00 | -1.20 | 0.00% |
| TransactionDT | 7,372,311.31 | 4,617,223.65 | 0.13 | -1.23 | 0.00% |
| TransactionAmt | 135.03 | 239.16 | 14.37 | 1,123.96 | 11.26% |
| card1 | 9,898.73 | 4,901.17 | -0.04 | -1.14 | 0.00% |
| card2 | 362.56 | 157.79 | -0.20 | -1.33 | 0.00% |
| card3 | 153.19 | 11.34 | 2.02 | 6.32 | 11.49% |
| card5 | 199.28 | 41.24 | -1.22 | -0.05 | 0.00% |
| addr1 | 290.73 | 101.74 | 0.37 | -0.50 | 0.07% |
| addr2 | 86.80 | 2.69 | -14.50 | 256.78 | 0.83% |
| dist1 | 118.50 | 371.87 | 5.11 | 36.80 | 16.78% |

### Key Observations

1. **Extreme Skewness:** TransactionAmt (14.37), addr2 (-14.50)
2. **Extreme Kurtosis:** TransactionAmt (1,123.96), addr2 (256.78)
3. **High Outlier Rates:** dist1 (16.78%), card3 (11.49%), TransactionAmt (11.26%)
4. **Well-Behaved:** card1, card2, card5, addr1 have low skewness

### Feature Group Characteristics

| Group | Count | Description | Typical Missing % |
|-------|-------|-------------|-------------------|
| **V-series** | 339 | Vesta engineered features | 10-80% |
| **C-series** | 14 | Count features | 5-30% |
| **D-series** | 15 | Time delta features | 50-90% |
| **card-series** | 6 | Card attributes | 0-2% |
| **addr-series** | 2 | Address attributes | 15-20% |
| **dist-series** | 2 | Distance features | 90-95% |

---


## 6. Missing Value Analysis

### Classification by Missing Percentage

| Category | Column Count | Percentage |
|----------|-------------|------------|
| **< 5% (Minimal)** | 112 | 25.8% |
| **5-25% (Low)** | 70 | 16.1% |
| **25-50% (Moderate)** | 38 | 8.8% |
| **> 50% (High)** | 202 | 46.5% |
| **> 90% (Extreme)** | 12 | 2.8% |

![Missing Values](plots/04_missing_values.png)

### Top 30 Columns with Highest Missing Values

| Rank | Column | Missing % | Group | Action |
|------|--------|-----------|-------|--------|
| 1 | id_24 | 99.20% | Identity | DROP |
| 2 | id_25 | 99.13% | Identity | DROP |
| 3-9 | id_07, id_08, id_21, id_22, id_23, id_26, id_27 | 99.12-99.13% | Identity | DROP |
| 10 | dist2 | 93.63% | Distance | DROP |
| 11 | D7 | 93.41% | Delta | DROP |
| 12 | id_18 | 92.36% | Identity | DROP |
| 13-15 | D13, D14, D12 | 89.04-89.51% | Delta | DROP |
| 16-17 | id_04, id_03 | 88.77% | Identity | DROP |
| 18 | D6 | 87.61% | Delta | DROP |
| 19-20 | id_33, id_09 | 87.31-87.59% | Identity | DROP |
| 21-30 | Various D, id, V cols | 80-87% | Mixed | DROP |

### Missing Value Strategy

**Columns to DROP (>90% missing):** 12 columns
- All id_* columns with >90% missing
- dist2
- D7

**Columns to DROP (50-90% missing):** Consider dropping ~150 columns
- Most D-series features
- Many id_* features
- Sparse V-series features

**Columns to IMPUTE (<50% missing):**
- V-series: Median imputation
- C-series: Median imputation
- M-series: Mode (most frequent) or create "missing" category
- card/addr: Median for numerical, mode for categorical

---

## 7. Correlation Analysis

### High Correlation Pairs (|r| > 0.7)

Found **5 highly correlated pairs** in sample features:

| Pair | Pearson r | Implication |
|------|-----------|-------------|
| V4 ↔ V5 | 0.916 | Strong redundancy - drop one |
| V8 ↔ V9 | 0.825 | Strong redundancy - drop one |
| V6 ↔ V7 | 0.772 | Moderate redundancy |
| V2 ↔ V3 | 0.761 | Moderate redundancy |
| V2 ↔ V8 | 0.757 | Moderate redundancy |

![Correlation Matrix](plots/05_correlation_matrix.png)

### Recommendation
- **Drop V5** (keep V4, higher individual correlation with target)
- **Drop V9** (keep V8)
- Monitor other V-series correlations during feature selection

---


## 8. Temporal Analysis

### Transaction Timeline

| Metric | Value |
|--------|-------|
| **Time Span** | 182 days (~6 months) |
| **TransactionDT Range** | 86,400 - 15,811,131 seconds |
| **Reference Point** | Unknown fixed date (dataset timestamp format) |

![Temporal Analysis](plots/06_temporal_analysis.png)

### Fraud Rate Over Time

- **Observation:** Fraud rate varies over time (visible in plot)
- **Implication:** Temporal features are predictive
- **Pattern:** No strong seasonal pattern evident in 6-month window
- **Recommendation:** 
  - Create time-based features (hour of day, day of week, month)
  - Use time-based train/val/test split instead of random
  - Consider temporal cross-validation

### Time-Based Split Strategy

**Recommended:**
```
Training:   First 60% of timeline (Days 1-109)
Validation: Next 20% of timeline (Days 110-145)  
Test:       Final 20% of timeline (Days 146-182)
```

**Justification:** Simulates production scenario where model trains on past data and predicts future fraud.

---

## 9. Identity Coverage Analysis

### Coverage Statistics

| Metric | Value |
|--------|-------|
| **Transactions WITH Identity** | 144,233 (24.42%) |
| **Transactions WITHOUT Identity** | 446,307 (75.58%) |
| **Fraud Rate WITH Identity** | 7.85% |
| **Fraud Rate WITHOUT Identity** | 2.09% |
| **Fraud Rate Ratio** | **3.7x higher** with identity |

![Identity Coverage](plots/07_identity_coverage.png)

### Critical Insights

1. **Identity is a Strong Signal:** Fraud rate WITH identity is 3.7x higher
2. **Missing Not at Random:** Identity availability is correlated with fraud
3. **Sparse Coverage:** Only 24.42% of transactions have identity data
4. **Missingness is Informative:** Create `has_identity` binary feature

### Recommendation

**Strategy for Identity Features:**
1. **Create Binary Indicator:** `has_identity` = 1 if any id_* column has value
2. **Keep High-Quality id_* Columns:** Only those with <50% missing
3. **Drop Sparse id_* Columns:** >90% missing (already flagged)
4. **Impute Remaining:** Use "MISSING" category for categorical id features

**Identity Columns to KEEP:**
- None recommended due to extreme sparsity (most >75% missing)
- Instead, use `has_identity` derived feature

---

## 10. Memory Analysis

### Memory Footprint

| Metric | Value |
|--------|-------|
| **Total Memory** | 2,513.97 MB |
| **Average per Column** | 5.79 MB |
| **Largest Column** | card4 (31.02 MB) |

![Memory Usage](plots/08_memory_usage.png)

### Top 10 Memory-Consuming Columns

| Rank | Column | Memory (MB) | % of Total |
|------|--------|-------------|------------|
| 1 | card4 | 31.02 | 1.23% |
| 2 | P_emaildomain | 30.55 | 1.22% |
| 3 | card6 | 30.52 | 1.21% |
| 4 | ProductCD | 28.16 | 1.12% |
| 5 | M6 | 25.25 | 1.00% |
| 6 | M4 | 23.62 | 0.94% |
| 7-9 | M1, M2, M3 | 23.51 | 0.93% each |
| 10 | id_31 | 22.36 | 0.89% |

### Memory Optimization Strategy

1. **Convert float64 → float32:** ~50% memory reduction for numerical features
2. **Drop Sparse Columns:** Eliminate 150+ columns with >50% missing
3. **Categorical Encoding:** Convert object dtypes to category dtype
4. **Expected Reduction:** From 2.5 GB to ~800 MB after preprocessing

---


## 11. Preprocessing Strategy

### Overview

Based on EDA findings, the following comprehensive preprocessing strategy is recommended. This strategy addresses class imbalance, missing values, high dimensionality, and feature encoding challenges.

---

### Strategy 1: Feature Dropping

**Objective:** Reduce dimensionality from 434 to ~120-150 features

#### Columns to DROP

| Group | Criteria | Count | Justification |
|-------|----------|-------|---------------|
| **Extreme Sparsity** | >90% missing | 12 | Insufficient data for meaningful imputation |
| **High Sparsity** | 50-90% missing + low variance | ~150 | Too sparse for tree-based models |
| **High Cardinality + Sparse** | >100 unique + >75% missing | 3 | DeviceInfo, id_33, id_31 |
| **Redundant Correlations** | \|r\| > 0.9 | 2 | V5 (keep V4), V9 (keep V8) |
| **Identifier Columns** | TransactionID | 1 | Not a feature |

**Specific Columns to DROP:**

```python
DROP_COLUMNS = [
    # Extreme sparsity (>90%)
    'id_07', 'id_08', 'id_21', 'id_22', 'id_23', 'id_24', 'id_25', 
    'id_26', 'id_27', 'dist2', 'D7', 'id_18',
    
    # High sparsity D-series (>85%)
    'D6', 'D12', 'D13', 'D14',
    
    # High cardinality + sparse
    'DeviceInfo', 'id_33', 'id_31', 'R_emaildomain',
    
    # High sparsity identity columns (>80%)
    'id_03', 'id_04', 'id_09', 'id_30', 'id_34',
    
    # Redundant correlations
    'V5', 'V9',
    
    # Identifier
    'TransactionID',
    
    # Additional sparse V-series (>80% missing) - identify during implementation
    # 'V1', 'V44', 'V47', ... (to be determined by missing% threshold)
]
```

**Expected Result:** ~280 columns dropped, ~150 retained

---

### Strategy 2: Feature Retention (Keep Unchanged)

**Objective:** Identify features that require no preprocessing

#### Columns to KEEP UNCHANGED

| Feature | Reason | Action |
|---------|--------|--------|
| **TransactionDT** | Temporal feature, no missing values | Keep as-is |
| **TransactionAmt** | Will be transformed separately | Keep raw version |
| **isFraud** | Target variable | Keep as-is |

**Total:** 3 columns kept unchanged

---

### Strategy 3: Transformation & Feature Engineering

**Objective:** Create derived features and transformations

#### Features to TRANSFORM

| Original Feature | Transformation | New Feature | Justification |
|------------------|----------------|-------------|---------------|
| **TransactionAmt** | `log1p(x)` | `TransactionAmt_log` | Reduce skewness (14.37) and kurtosis (1,123) |
| **TransactionDT** | Time extraction | `hour`, `day_of_week`, `day_of_month` | Capture temporal patterns |
| **Identity Columns** | Binary indicator | `has_identity` | 3.7x fraud rate signal |
| **Email Domains** | Frequency encoding | `P_emaildomain_freq` | Handle 59 categories efficiently |
| **card1-6** | Bin numeric cards | `card1_bin`, `card2_bin` | Reduce cardinality if needed |

#### New Features to CREATE

```python
NEW_FEATURES = [
    'TransactionAmt_log',          # log1p transformation
    'hour',                         # Extract from TransactionDT
    'day_of_week',                  # 0=Monday, 6=Sunday
    'day_of_month',                 # 1-31
    'has_identity',                 # Binary: any id_* column non-null
    'P_emaildomain_freq',           # Frequency encoding
]
```

---

### Strategy 4: Missing Value Imputation

**Objective:** Handle missing values systematically by feature type

#### Imputation Rules

| Feature Group | Strategy | Imputed Value | Justification |
|---------------|----------|---------------|---------------|
| **V-series (numerical)** | Median | `df[col].median()` | Robust to outliers |
| **C-series (count)** | Zero | `0` | Counts default to zero |
| **D-series (remaining)** | Median | `df[col].median()` | Time deltas - median reasonable |
| **M-series (binary)** | Mode | Most frequent | Binary flags |
| **card1-5 (numerical)** | Median | `df[col].median()` | Card attributes |
| **addr1-2** | Median | `df[col].median()` | Address codes |
| **P_emaildomain** | Mode | "Unknown" | Categorical - create new category |

#### Implementation Priority

1. **Drop sparse columns first** (>50% missing)
2. **Impute remaining V-series** with median
3. **Impute C-series** with 0
4. **Impute categorical** with mode or "Unknown"
5. **Verify no remaining nulls** before encoding

---

### Strategy 5: Categorical Encoding

**Objective:** Convert categorical variables to numerical representations

#### Encoding Strategy by Column

| Column | Cardinality | Missing % | Encoding Method | Output Dimension |
|--------|-------------|-----------|-----------------|------------------|
| **ProductCD** | 5 | 0% | One-Hot | 5 |
| **card4** | 4 | 0.27% | One-Hot | 4 |
| **card6** | 4 | 0.27% | One-Hot | 4 |
| **P_emaildomain** | 59 | 16% | Frequency Encoding | 1 |
| **M1-M9** | 2-3 | 28-60% | Label Encoding | 1 each |
| **id_12, id_15, id_16** | 2-3 | 75-78% | Label Encoding | 1 each |
| **DeviceType** | 2 | 76% | Binary Encoding | 1 |

#### Encoding Details

**One-Hot Encoding:** (Total: 13 new columns)
```python
ONE_HOT_COLS = ['ProductCD', 'card4', 'card6']
```

**Frequency Encoding:** (Total: 1 column)
```python
FREQ_ENCODE_COLS = ['P_emaildomain']
# Replace category with its frequency in training set
```

**Label Encoding:** (Total: ~12 columns)
```python
LABEL_ENCODE_COLS = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9',
                      'id_12', 'id_15', 'id_16', 'DeviceType']
```

**Expected Dimension After Encoding:** ~165 features

---

### Strategy 6: Feature Scaling

**Objective:** Normalize numerical features for model compatibility

#### Scaling Strategy

| Feature Group | Method | Parameters | Justification |
|---------------|--------|------------|---------------|
| **TransactionAmt_log** | StandardScaler | mean=0, std=1 | Already log-transformed |
| **TransactionDT derivatives** | MinMaxScaler | range [0, 1] | Cyclical time features |
| **V-series** | StandardScaler | mean=0, std=1 | Varied scales |
| **C-series** | StandardScaler | mean=0, std=1 | Count features |
| **card-series (numerical)** | StandardScaler | mean=0, std=1 | Varied scales |
| **addr-series** | StandardScaler | mean=0, std=1 | Address codes |

#### Features to SCALE

```python
STANDARD_SCALE_COLS = [
    'TransactionAmt_log',
    'V1', 'V2', 'V3', ... # All remaining V-series
    'C1', 'C2', ... # All C-series
    'card1', 'card2', 'card3', 'card5', # Numerical cards
    'addr1', 'addr2',
]

MINMAX_SCALE_COLS = [
    'hour',  # 0-23 → [0, 1]
    'day_of_week',  # 0-6 → [0, 1]
    'day_of_month',  # 1-31 → [0, 1]
]
```

**Important:** Fit scalers on training set only, transform val/test with same parameters

---

### Strategy 7: Train/Validation/Test Split

**Objective:** Create time-based splits that preserve fraud rate

#### Split Strategy

**Method:** Time-based split (not random)

```
Training Set:   60% (First 109 days)   → 354,324 samples
Validation Set: 20% (Days 110-145)     → 118,108 samples  
Test Set:       20% (Days 146-182)     → 118,108 samples
```

**Justification:**
- Simulates production: train on past, predict future
- Prevents temporal leakage
- More realistic fraud detection scenario

#### Implementation

```python
# Sort by TransactionDT
df_sorted = df.sort_values('TransactionDT')

# Calculate split indices
train_end = int(len(df_sorted) * 0.6)
val_end = int(len(df_sorted) * 0.8)

# Split
train_df = df_sorted.iloc[:train_end]
val_df = df_sorted.iloc[train_end:val_end]
test_df = df_sorted.iloc[val_end:]

# Verify fraud rates are similar
print(f"Train fraud rate: {train_df['isFraud'].mean():.4f}")
print(f"Val fraud rate: {val_df['isFraud'].mean():.4f}")
print(f"Test fraud rate: {test_df['isFraud'].mean():.4f}")
```

---

###
 Strategy 8: Class Imbalance Handling

**Objective:** Address 27.58:1 class imbalance

#### Recommended Approaches

| Technique | When to Apply | Configuration |
|-----------|---------------|---------------|
| **Stratified Sampling** | During split | `stratify=y` parameter |
| **Class Weights** | During training | `class_weight='balanced'` or `{0: 1, 1: 27.58}` |
| **SMOTE** | Post-split (optional) | `sampling_strategy=0.3` (increase fraud to 30%) |
| **Focal Loss** | Advanced models | `gamma=2.0, alpha=0.25` |

#### Recommended Strategy

**Primary:** Class weighting during training
```python
from sklearn.utils import class_weight

# Calculate class weights
class_weights = class_weight.compute_class_weight(
    'balanced',
    classes=np.unique(y_train),
    y=y_train
)
# Result: {0: 0.51, 1: 14.05}
```

**Secondary:** SMOTE for tree-based models (optional)
```python
from imblearn.over_sampling import SMOTE

smote = SMOTE(sampling_strategy=0.3, random_state=42)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
```

**Evaluation:** Use stratified metrics
- Precision, Recall, F1-Score (per class)
- AUC-ROC, AUC-PR
- Confusion Matrix
- **NOT accuracy** (misleading with 3.5% fraud rate)

---

## 12. Feature Group Summary & Actions

### Complete Preprocessing Table

| Feature Group | Count | Action | Method | Justification |
|---------------|-------|--------|--------|---------------|
| **Identifier** | 1 | DROP | - | TransactionID not predictive |
| **Target** | 1 | KEEP | - | isFraud is target |
| **Extreme Sparse (>90%)** | 12 | DROP | - | Insufficient data |
| **High Sparse (50-90%)** | ~150 | DROP | - | Too sparse for modeling |
| **High Cardinality** | 3 | DROP | - | DeviceInfo, id_33, id_31 |
| **Redundant** | 2 | DROP | - | V5, V9 (correlated) |
| **V-series (kept)** | ~180 | IMPUTE → SCALE | Median → StandardScaler | Core features |
| **C-series** | 14 | IMPUTE → SCALE | Zero → StandardScaler | Count features |
| **D-series (kept)** | ~6 | IMPUTE → SCALE | Median → StandardScaler | Time deltas |
| **M-series** | 9 | IMPUTE → ENCODE | Mode → Label Encoding | Binary flags |
| **card-series** | 6 | IMPUTE → ENCODE/SCALE | Median/OneHot | Card attributes |
| **addr-series** | 2 | IMPUTE → SCALE | Median → StandardScaler | Address codes |
| **dist-series (kept)** | 1 | IMPUTE → SCALE | Median → StandardScaler | Distance |
| **ProductCD** | 1 | ENCODE | One-Hot | Strong signal |
| **P_emaildomain** | 1 | ENCODE | Frequency | Moderate cardinality |
| **TransactionAmt** | 1 | TRANSFORM → SCALE | log1p → StandardScaler | Reduce skew |
| **TransactionDT** | 1 | ENGINEER | Time extraction | Temporal patterns |
| **Identity Derived** | 1 | CREATE | Binary indicator | `has_identity` |

**Input Features:** 434 columns  
**After Dropping:** ~154 columns  
**After Encoding:** ~165 columns  
**After Scaling:** ~165 columns (ready for modeling)

---

## 13. Preprocessing Pipeline Order

### Step-by-Step Execution Plan

```
1. LOAD DATA
   └─> Load train_transaction.csv + train_identity.csv
   └─> Merge on TransactionID

2. FEATURE ENGINEERING (before split)
   └─> Create TransactionAmt_log = log1p(TransactionAmt)
   └─> Create hour, day_of_week, day_of_month from TransactionDT
   └─> Create has_identity = any(id_* columns not null)

3. DROP FEATURES
   └─> Drop 12 columns with >90% missing
   └─> Drop ~150 columns with 50-90% missing
   └─> Drop high-cardinality sparse columns (DeviceInfo, id_33, id_31, R_emaildomain)
   └─> Drop redundant columns (V5, V9)
   └─> Drop TransactionID
   └─> Result: 434 → ~154 columns

4. TRAIN/VAL/TEST SPLIT (time-based)
   └─> Sort by TransactionDT
   └─> Split: 60% train / 20% val / 20% test
   └─> Verify fraud rate preserved

5. IMPUTE MISSING VALUES (fit on train, transform val/test)
   └─> V-series: median
   └─> C-series: 0
   └─> D-series: median
   └─> M-series: mode
   └─> card-series: median
   └─> addr-series: median
   └─> P_emaildomain: mode or "Unknown"

6. ENCODE CATEGORICAL (fit on train, transform val/test)
   └─> One-Hot: ProductCD, card4, card6
   └─> Frequency: P_emaildomain
   └─> Label: M-series, id_12/15/16, DeviceType

7. SCALE NUMERICAL (fit on train, transform val/test)
   └─> StandardScaler: V-series, C-series, D-series, card-series, addr-series, TransactionAmt_log
   └─> MinMaxScaler: hour, day_of_week, day_of_month

8. VERIFY
   └─> Check no missing values
   └─> Check all features numerical
   └─> Check shapes: (n_samples, ~165)
   └─> Check fraud rate preserved in all splits

9. SAVE PROCESSED DATA
   └─> backend/data/processed/train/features.csv
   └─> backend/data/processed/train/target.csv
   └─> backend/data/processed/val/features.csv
   └─> backend/data/processed/val/target.csv
   └─> backend/data/processed/test/features.csv
   └─> backend/data/processed/test/target.csv
   └─> backend/data/processed/preprocessing_artifacts/ (scalers, encoders)
```

---

## 14. Expected Outcomes

### Data Reduction

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Columns** | 434 | ~165 | -62% |
| **Memory (MB)** | 2,514 | ~850 | -66% |
| **Missing Values** | 45.07% | 0% | -100% |
| **Categorical Cols** | 31 | 0 | -100% |
| **Data Type** | Mixed | All float32 | Standardized |

### Quality Improvements

✅ **Dimensionality Reduced:** 434 → 165 features (-62%)  
✅ **No Missing Values:** All nulls imputed  
✅ **Normalized Scale:** All features scaled appropriately  
✅ **Encoded Categories:** All categorical → numerical  
✅ **Class Balance Handled:** Stratified splits + class weights  
✅ **Temporal Integrity:** Time-based split prevents leakage  
✅ **Memory Optimized:** float64 → float32 where appropriate  

### Readiness for Modeling

After preprocessing:
- ✅ Clean numerical feature matrix
- ✅ Stratified train/val/test splits
- ✅ No data leakage (scalers fit on train only)
- ✅ Class imbalance addressed
- ✅ Temporal patterns preserved
- ✅ Ready for XGBoost, LightGBM, CatBoost, Neural Networks

---

## 15. Risks & Mitigation

### Identified Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Dropping 280 columns may lose signal** | Medium | Perform feature importance analysis post-modeling; add back if needed |
| **Time-based split may have different fraud patterns** | Medium | Monitor fraud rate across splits; use cross-validation |
| **SMOTE may create synthetic noise** | Low | Use class weights first; SMOTE only if underperformance |
| **Frequency encoding may cause leakage** | Low | Compute frequencies on train set only |
| **V-series meaning unknown** | Medium | Treat as black-box features; rely on feature importance |

### Monitoring Plan

1. **Track fraud rate** in train/val/test splits (should be ~3.5% each)
2. **Monitor feature distributions** before/after preprocessing
3. **Validate no data leakage** (val/test use train-fitted transformers)
4. **Check for drift** (distributions should be similar across splits)

---

## 16. Next Steps

### Milestone 1C: Preprocessing Implementation

**DO NOT START** until this strategy is reviewed and approved.

**Tasks:**
1. Implement preprocessing pipeline in `ml/training/data/preprocessing.py`
2. Create preprocessing configuration in `ml/training/data/preprocessing_config.py`
3. Write unit tests for each preprocessing step
4. Generate processed datasets in `backend/data/processed/`
5. Create preprocessing report with before/after statistics
6. Validate data quality (no nulls, correct shapes, preserved fraud rates)

---

## Appendix: Generated Files

### EDA Outputs

1. **reports/milestone1/eda_summary.json** - Machine-readable summary
2. **reports/milestone1/eda_report.md** - This comprehensive report
3. **reports/milestone1/plots/** - 8 professional visualizations:
   - 01_target_distribution.png
   - 02_transaction_amount.png
   - 03_product_cd.png
   - 04_missing_values.png
   - 05_correlation_matrix.png
   - 06_temporal_analysis.png
   - 07_identity_coverage.png
   - 08_memory_usage.png

---

**Report Generated:** August 1, 2026  
**Status:** ✅ EDA Complete - Awaiting Preprocessing Strategy Approval  
**Next Milestone:** 1C - Preprocessing Implementation
