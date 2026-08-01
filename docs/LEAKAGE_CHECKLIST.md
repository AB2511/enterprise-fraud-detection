# Data Leakage Prevention Checklist

**Project:** Enterprise Fraud Detection - IEEE-CIS Dataset  
**Purpose:** Comprehensive checklist to prevent data leakage during preprocessing and model training  
**Severity:** CRITICAL - Data leakage invalidates model evaluation and leads to false performance metrics

---

## Table of Contents

1. [What is Data Leakage?](#1-what-is-data-leakage)
2. [Types of Data Leakage](#2-types-of-data-leakage)
3. [Pre-Split Leakage Prevention](#3-pre-split-leakage-prevention)
4. [Post-Split Leakage Prevention](#4-post-split-leakage-prevention)
5. [Feature Engineering Leakage](#5-feature-engineering-leakage)
6. [Imputation Leakage](#6-imputation-leakage)
7. [Encoding Leakage](#7-encoding-leakage)
8. [Scaling Leakage](#8-scaling-leakage)
9. [Temporal Leakage](#9-temporal-leakage)
10. [Target Leakage](#10-target-leakage)
11. [Implementation Checklist](#11-implementation-checklist)
12. [Testing & Validation](#12-testing--validation)

---

## 1. What is Data Leakage?

**Definition:** Data leakage occurs when information from outside the training dataset is used to create the model, leading to overly optimistic performance estimates that don't generalize to production.

**Impact:**
- ❌ Model appears to perform well in validation but fails in production
- ❌ Overestimated metrics (precision, recall, AUC-ROC)
- ❌ Invalid business decisions based on false confidence
- ❌ Wasted resources deploying ineffective models

**Golden Rule:** The validation and test sets must **never** influence any preprocessing decisions.

---

## 2. Types of Data Leakage

### 2.1 Train-Test Contamination
Information from test set leaks into training set during preprocessing.

**Examples:**
- Computing imputation values (mean, median) on entire dataset before split
- Fitting encoders on entire dataset before split
- Calculating statistics on validation/test data

### 2.2 Temporal Leakage
Using future information to predict the past.

**Examples:**
- Random splitting time-series data instead of chronological split
- Including features derived from future transactions
- Using global statistics that include test period data

### 2.3 Target Leakage
Features that are direct consequences of the target or wouldn't be available at prediction time.

**Examples:**
- Features only populated after fraud is detected
- Aggregations that include the current transaction
- Features derived from target variable

### 2.4 Feature Engineering Leakage
Creating features using information not available at training time.

**Examples:**
- Future-looking statistics (avg fraud rate of next 7 days)
- Look-ahead bias in rolling windows
- Using test set statistics in feature creation

---

## 3. Pre-Split Leakage Prevention

**Rule:** Operations performed BEFORE train/val/test split must **not** use target information or statistics that vary between splits.

### ✅ SAFE Pre-Split Operations

| Operation | Why Safe | Example |
|-----------|----------|---------|
| **Drop constant features** | Based on data structure, not statistics | Drop columns with 1 unique value |
| **Drop identifier columns** | Based on domain knowledge | Drop TransactionID |
| **Drop features >99.5% missing** | Based on threshold, not learned statistics | Drop columns with excessive nulls |
| **Feature engineering from single row** | Uses only current transaction data | log1p(TransactionAmt) |
| **Create temporal features** | Derived from timestamp, not aggregations | elapsed_time_days from TransactionDT |
| **Create binary indicators** | Based on presence/absence | has_identity = any(id_* not null) |
| **Extract device info** | String parsing, no statistics | Extract browser from DeviceInfo |

### ❌ UNSAFE Pre-Split Operations

| Operation | Why Unsafe | Correct Approach |
|-----------|------------|------------------|
| **Impute with mean/median** | Uses statistics from entire dataset | Fit imputer on train, transform val/test |
| **Normalize features** | Uses global min/max or mean/std | Fit scaler on train, transform val/test |
| **Encode categorical** | Uses category frequencies | Fit encoder on train, transform val/test |
| **Drop highly correlated features** | Correlation computed on entire dataset | Compute correlation on train only |
| **Feature selection** | Feature importance from entire dataset | Select features on train only |

---

## 4. Post-Split Leakage Prevention

**Rule:** After splitting, all transformers must be **fit on train set only** and **applied to val/test sets**.

### 4.1 Fit-Transform Pattern

**Correct Implementation:**
```python
# ✅ CORRECT: Fit on train, transform val/test
from sklearn.impute import SimpleImputer

# Split first
X_train, X_val, X_test = split_data(X)

# Fit imputer on train only
imputer = SimpleImputer(strategy="median")
imputer.fit(X_train)

# Transform all sets using train statistics
X_train_imputed = imputer.transform(X_train)
X_val_imputed = imputer.transform(X_val)  # Uses train statistics
X_test_imputed = imputer.transform(X_test)  # Uses train statistics
```

**Incorrect Implementation:**
```python
# ❌ WRONG: Fitting on each set independently
imputer_train = SimpleImputer().fit(X_train)
imputer_val = SimpleImputer().fit(X_val)  # LEAKAGE!
imputer_test = SimpleImputer().fit(X_test)  # LEAKAGE!
```

### 4.2 Pipeline Enforcement

Use sklearn Pipeline to enforce fit-transform pattern:

```python
from sklearn.pipeline import Pipeline

# ✅ CORRECT: Pipeline ensures proper fit-transform
pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('encoder', OrdinalEncoder()),
    ('model', XGBClassifier())
])

# Fit on train (all steps fit on train)
pipeline.fit(X_train, y_train)

# Predict on val (all steps transform using train statistics)
y_pred = pipeline.predict(X_val)
```

---

## 5. Feature Engineering Leakage

### 5.1 Row-Level Features (SAFE)

**Rule:** Features derived from single row data are safe.

**Examples:**
```python
# ✅ SAFE: Uses only current transaction
df["TransactionAmt_log"] = np.log1p(df["TransactionAmt"])
df["elapsed_time_days"] = (df["TransactionDT"] - df["TransactionDT"].min()) / 86400
df["has_identity"] = df[id_cols].notna().any(axis=1)
```

### 5.2 Aggregation Features (UNSAFE if not careful)

**Rule:** Aggregations must respect temporal boundaries and exclude current row.

**❌ WRONG: Look-ahead bias**
```python
# Uses future data to predict past
df["avg_fraud_rate_next_7days"] = df.groupby("customer_id")["isFraud"].transform(
    lambda x: x.rolling(7).mean().shift(-7)
)
```

**✅ CORRECT: Look-back only**
```python
# Uses only past data
df["avg_fraud_rate_past_7days"] = df.groupby("customer_id")["isFraud"].transform(
    lambda x: x.rolling(7).mean().shift(1)  # Exclude current transaction
)
```

### 5.3 Target-Derived Features (FORBIDDEN)

**Rule:** Never use target variable to create features.

**❌ FORBIDDEN:**
```python
# Uses target to create feature
df["fraud_rate_by_product"] = df.groupby("ProductCD")["isFraud"].transform("mean")
```

**Exception:** Target encoding is acceptable if done with cross-validation within training set only and applied to val/test using train statistics.

---

## 6. Imputation Leakage

### 6.1 Numerical Imputation

**✅ CORRECT:**
```python
from sklearn.impute import SimpleImputer

# Fit on train
imputer = SimpleImputer(strategy="median")
imputer.fit(X_train[numerical_cols])

# Transform all sets
X_train[numerical_cols] = imputer.transform(X_train[numerical_cols])
X_val[numerical_cols] = imputer.transform(X_val[numerical_cols])
X_test[numerical_cols] = imputer.transform(X_test[numerical_cols])
```

**❌ WRONG:**
```python
# Computes median on entire dataset
median_values = df[numerical_cols].median()  # LEAKAGE!
df[numerical_cols] = df[numerical_cols].fillna(median_values)
```

### 6.2 Categorical Imputation

**✅ CORRECT:**
```python
# Fit on train
most_frequent = X_train[cat_col].mode()[0]

# Apply to all
X_train[cat_col] = X_train[cat_col].fillna(most_frequent)
X_val[cat_col] = X_val[cat_col].fillna(most_frequent)
X_test[cat_col] = X_test[cat_col].fillna(most_frequent)
```

### 6.3 XGBoost Native NaN Handling

**✅ PREFERRED for XGBoost:**
```python
# Let XGBoost handle missing values internally
# NO imputation needed for numerical features
X_train_with_nan = X_train  # Keep NaN values
model = xgb.XGBClassifier(missing=np.nan)
model.fit(X_train_with_nan, y_train)
```

**Justification:** XGBoost learns optimal missing value handling during training, avoiding imputation leakage.

---

## 7. Encoding Leakage

### 7.1 Ordinal Encoding

**✅ CORRECT:**
```python
from sklearn.preprocessing import OrdinalEncoder

# Fit on train
encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
encoder.fit(X_train[cat_cols])

# Transform all
X_train[cat_cols] = encoder.transform(X_train[cat_cols])
X_val[cat_cols] = encoder.transform(X_val[cat_cols])  # Unknown categories → -1
X_test[cat_cols] = encoder.transform(X_test[cat_cols])
```

### 7.2 One-Hot Encoding

**✅ CORRECT:**
```python
from sklearn.preprocessing import OneHotEncoder

# Fit on train
encoder = OneHotEncoder(handle_unknown="ignore", sparse=False)
encoder.fit(X_train[cat_cols])

# Transform all
X_train_encoded = encoder.transform(X_train[cat_cols])
X_val_encoded = encoder.transform(X_val[cat_cols])  # Ignores unknown categories
X_test_encoded = encoder.transform(X_test[cat_cols])
```

### 7.3 Frequency Encoding

**✅ CORRECT:**
```python
# Compute frequencies on train only
freq_map = X_train[cat_col].value_counts(normalize=True).to_dict()

# Apply to all (unseen categories → 0)
X_train[cat_col + "_freq"] = X_train[cat_col].map(freq_map).fillna(0)
X_val[cat_col + "_freq"] = X_val[cat_col].map(freq_map).fillna(0)
X_test[cat_col + "_freq"] = X_test[cat_col].map(freq_map).fillna(0)
```

**❌ WRONG:**
```python
# Computes frequencies on entire dataset
freq_map = df[cat_col].value_counts(normalize=True).to_dict()  # LEAKAGE!
df[cat_col + "_freq"] = df[cat_col].map(freq_map)
```

---

## 8. Scaling Leakage

**Note:** Scaling is **NOT needed for XGBoost** but included for completeness.

### 8.1 StandardScaler

**✅ CORRECT:**
```python
from sklearn.preprocessing import StandardScaler

# Fit on train
scaler = StandardScaler()
scaler.fit(X_train[numerical_cols])

# Transform all
X_train[numerical_cols] = scaler.transform(X_train[numerical_cols])
X_val[numerical_cols] = scaler.transform(X_val[numerical_cols])
X_test[numerical_cols] = scaler.transform(X_test[numerical_cols])
```

**❌ WRONG:**
```python
# Fits on entire dataset
scaler = StandardScaler()
df[numerical_cols] = scaler.fit_transform(df[numerical_cols])  # LEAKAGE!
```

---

## 9. Temporal Leakage

### 9.1 Time-Based Splitting

**✅ CORRECT:**
```python
# Sort by time
df_sorted = df.sort_values("TransactionDT")

# Split chronologically
train_end = int(len(df_sorted) * 0.6)
val_end = int(len(df_sorted) * 0.8)

train = df_sorted.iloc[:train_end]
val = df_sorted.iloc[train_end:val_end]
test = df_sorted.iloc[val_end:]
```

**❌ WRONG:**
```python
# Random split ignores temporal order
train, test = train_test_split(df, test_size=0.2)  # LEAKAGE!
```

### 9.2 Rolling Window Features

**✅ CORRECT:**
```python
# Exclude current row, use only past
df["rolling_avg"] = df.groupby("customer_id")["TransactionAmt"].transform(
    lambda x: x.shift(1).rolling(7, min_periods=1).mean()
)
```

**❌ WRONG:**
```python
# Includes current row
df["rolling_avg"] = df.groupby("customer_id")["TransactionAmt"].transform(
    lambda x: x.rolling(7).mean()  # LEAKAGE!
)
```

---

## 10. Target Leakage

### 10.1 Direct Target Leakage

**❌ FORBIDDEN:**
```python
# Feature directly uses target
df["is_fraud_flag"] = df["isFraud"]  # Obvious leakage!
```

### 10.2 Proxy Target Leakage

**❌ FORBIDDEN:**
```python
# Feature only available after fraud is confirmed
df["fraud_investigation_duration"] = ...  # Only exists for fraudulent transactions
df["chargeback_amount"] = ...  # Only known after fraud confirmed
```

### 10.3 Aggregation Target Leakage

**❌ FORBIDDEN:**
```python
# Includes current transaction in aggregation
df["fraud_rate_by_merchant"] = df.groupby("merchant_id")["isFraud"].transform("mean")
```

**✅ CORRECT (with cross-validation):**
```python
# Use cross-validation to prevent target leakage
from category_encoders import TargetEncoder

encoder = TargetEncoder(cv=5)  # 5-fold CV within training set
encoder.fit(X_train, y_train)
X_train_encoded = encoder.transform(X_train)
X_val_encoded = encoder.transform(X_val)  # Uses train statistics
```

---

## 11. Implementation Checklist

### Pre-Implementation

- [ ] Read and understand all sections of this checklist
- [ ] Review preprocessing_config.yaml for leakage-prone settings
- [ ] Identify all features requiring fit-transform pattern
- [ ] Plan data split strategy (time-based confirmed)

### During Feature Engineering (Pre-Split)

- [ ] Only create row-level features (no aggregations)
- [ ] Verify log transforms use only current row
- [ ] Verify elapsed_time uses dataset minimum (not changing)
- [ ] Verify device extraction is string parsing only
- [ ] Verify has_identity uses only current row
- [ ] DO NOT compute statistics (mean, median, mode) yet

### During Data Split

- [ ] Sort by TransactionDT before splitting
- [ ] Use fixed ratios (60/20/20)
- [ ] Verify no data shuffling
- [ ] Verify train comes before val, val before test temporally
- [ ] Save split indices for reproducibility

### During Imputation

- [ ] Fit all imputers on train set only
- [ ] Save fitted imputers to artifacts directory
- [ ] Transform val/test using train-fitted imputers
- [ ] Verify val/test contain no new imputation logic
- [ ] For XGBoost: prefer retaining NaN over imputing

### During Encoding

- [ ] Fit all encoders on train set only
- [ ] Save fitted encoders to artifacts directory
- [ ] Transform val/test using train-fitted encoders
- [ ] Verify unknown categories handled gracefully
- [ ] Test with synthetic unknown category

### During Scaling (if needed)

- [ ] Fit all scalers on train set only
- [ ] Save fitted scalers to artifacts directory
- [ ] Transform val/test using train-fitted scalers
- [ ] Verify scaling parameters from train only

### Post-Processing

- [ ] Verify no nulls in train set (if imputed)
- [ ] Verify val/test may have nulls if XGBoost native handling
- [ ] Verify all categorical features encoded
- [ ] Verify train/val/test have same column order
- [ ] Verify train/val/test have same column count

---

## 12. Testing & Validation

### 12.1 Automated Leakage Tests

```python
def test_no_leakage_in_imputation():
    """Test that validation median != train median (proves independent fitting)."""
    # If val median == train median, possible leakage
    train_median = X_train["V1"].median()
    val_median = X_val["V1"].median()
    assert train_median != val_median, "Possible imputation leakage"

def test_encoder_fitted_on_train_only():
    """Test that encoder was fitted on train, not val/test."""
    # Check encoder categories match train, not val/test
    train_categories = set(X_train["ProductCD"].unique())
    encoder_categories = set(encoder.categories_[0])
    assert encoder_categories == train_categories, "Encoder not fitted on train only"

def test_temporal_order_preserved():
    """Test that train comes before val, val before test."""
    assert X_train["TransactionDT"].max() < X_val["TransactionDT"].min()
    assert X_val["TransactionDT"].max() < X_test["TransactionDT"].min()
```

### 12.2 Manual Validation Checks

1. **Imputer Check:**
   - Print train median vs val median → Should be different
   - Print imputer statistics → Should match train exactly

2. **Encoder Check:**
   - Print encoder categories → Should only include train categories
   - Test with val-only category → Should handle gracefully (unknown=-1 or ignore)

3. **Temporal Check:**
   - Print train TransactionDT range
   - Print val TransactionDT range
   - Print test TransactionDT range
   - Verify no overlap

4. **Feature Check:**
   - Verify no target-derived features
   - Verify no look-ahead features
   - Verify all aggregations use past data only

### 12.3 Red Flags

**Warning Signs of Leakage:**
- ⚠️ Validation performance > Training performance
- ⚠️ Perfect or near-perfect AUC (>0.99)
- ⚠️ Same statistics in train and val (median, mean, etc.)
- ⚠️ Categorical encoder has val-only categories
- ⚠️ Feature importance shows target-derived features at top

---

## Summary

**Critical Rules:**

1. ✅ **Split FIRST**, then fit transformers on train
2. ✅ **Never fit** on validation or test data
3. ✅ **Always use** fit-transform pattern (fit on train, transform on val/test)
4. ✅ **Prefer time-based split** for temporal data
5. ✅ **Avoid target-derived** features
6. ✅ **Test for leakage** with automated checks

**Milestone 1C Requirements:**

- [ ] Implement time-based split FIRST
- [ ] Fit all transformers on train only
- [ ] Save all fitted artifacts
- [ ] Test for leakage with unit tests
- [ ] Document any deviations from this checklist

---

**Document Version:** 1.0  
**Last Updated:** 2026-08-01  
**Status:** Ready for Milestone 1C Implementation

