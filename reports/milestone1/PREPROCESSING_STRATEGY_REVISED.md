# Preprocessing Strategy - REVISED

**Version:** 2.0 (Post-Review)  
**Date:** August 1, 2026  
**Status:** Awaiting Final Approval

---

## Revision Summary

Based on user review feedback, the preprocessing strategy has been significantly revised to be more conservative and configurable:

### Key Changes from Version 1.0

| Aspect | Version 1.0 (Original) | Version 2.0 (Revised) | Rationale |
|--------|------------------------|----------------------|-----------|
| **Feature Dropping** | Drop ~280 columns (>50% missing) | Drop only >99.5% missing, constant, duplicates | Preserve potential signal; XGBoost handles missing values |
| **Scaling** | StandardScaler + MinMaxScaler | NO scaling for XGBoost | Tree models don't require scaling |
| **TransactionAmt** | Drop original, keep log only | Keep BOTH original + log transform | Preserve raw signal + normalized version |
| **Categorical Encoding** | LabelEncoder | OrdinalEncoder or category dtype | Avoid LabelEncoder pitfalls |
| **Temporal Features** | hour, day_of_week, day_of_month | Elapsed time only | Simpler, more directly useful |
| **DeviceInfo/id_31** | Drop immediately | Extract browser/OS info first | May contain valuable structured data |
| **SMOTE** | Optional in pipeline | Removed from default | Prefer scale_pos_weight + threshold tuning |
| **Configuration** | Hardcoded | YAML config file | Externalize all thresholds |
| **Feature Inventory** | Not created | feature_inventory.csv generated | Document every feature decision |

---

## 1. Revised Feature Dropping Strategy

### 1.1 Drop Criteria (Minimal Approach)

**Only drop features meeting these strict criteria:**

1. **Extreme Missing Values:** >99.5% missing (vs 90% in v1.0)
2. **Constant Features:** Only 1 unique value across all samples
3. **Perfect Duplicates:** 100% correlation with another feature
4. **Identifiers:** TransactionID (not predictive)

### 1.2 Features to Drop

Based on `feature_inventory.csv` analysis:

| Criterion | Count | Features |
|-----------|-------|----------|
| **>99.5% missing** | 0 | None (highest is id_24 at 99.20%) |
| **Constant features** | 0 | None detected |
| **Duplicates** | TBD | Check correlation matrix during implementation |
| **Identifiers** | 1 | TransactionID |

**Expected Drops:** ~1-5 columns (vs ~280 in v1.0)

**Justification:** XGBoost and LightGBM handle missing values internally via split logic. Dropping features prematurely may discard weak but real signals. Let the model decide feature importance.

---

## 2. Revised Feature Retention Strategy

### 2.1 Keep Almost Everything

**Philosophy:** Err on the side of retention; rely on model-based feature selection post-training.

| Feature Group | Count | Action | Justification |
|---------------|-------|--------|---------------|
| **V-series** | 339 | KEEP ALL | Vesta engineered features, unknown but potentially valuable |
| **C-series** | 14 | KEEP ALL | Count features, interpretable |
| **D-series** | 15 | KEEP ALL | Time delta features, temporal signal |
| **M-series** | 9 | KEEP ALL | Binary/categorical flags |
| **card-series** | 6 | KEEP ALL | Card attributes, low missing rate |
| **addr-series** | 2 | KEEP ALL | Address codes |
| **dist-series** | 2 | KEEP ALL | Distance features |
| **id-series** | 38 | KEEP ALL | Identity features (even with high missing %) |
| **Categorical** | 31 | KEEP ALL | Product, email, device info |

**Total Retained:** ~433 features (vs ~154 in v1.0)

---

## 3. Revised Feature Engineering Strategy

### 3.1 TransactionAmt Treatment

**Change:** Keep BOTH original and transformed versions.

```python
# Keep original
df["TransactionAmt"]  # Raw dollar amounts

# Create log-transformed version
df["TransactionAmt_log"] = np.log1p(df["TransactionAmt"])
```

**Justification:**
- Original: Interpretable, preserves absolute scale
- Log: Reduces skewness, normalizes distribution
- Model can learn which version is more predictive

### 3.2 Temporal Features from TransactionDT

**Change:** Create elapsed time only, NOT time components.

**Version 1.0 (Rejected):**
```python
# DO NOT DO THIS
df["hour"] = ...
df["day_of_week"] = ...
df["day_of_month"] = ...
```

**Version 2.0 (Approved):**
```python
# Elapsed time since first transaction
df["elapsed_time_days"] = (df["TransactionDT"] - df["TransactionDT"].min()) / 86400
```

**Justification:**
- TransactionDT is already a time delta in seconds from a reference point
- Elapsed time captures ordering and temporal distance
- Hour/day features assume cyclical patterns not evident in 6-month span
- Simpler is better

### 3.3 Device Information Extraction

**Change:** Extract structured info from DeviceInfo and id_31 BEFORE deciding to drop.

**DeviceInfo Analysis:**
```python
# Example values: "Windows", "iOS Device", "MacOS", "Linux"
# Extract: browser, OS, device type

df["browser"] = extract_browser(df["DeviceInfo"])  # Chrome, Safari, Firefox, etc.
df["os"] = extract_os(df["DeviceInfo"])  # Windows, MacOS, iOS, Android, Linux
df["device_type"] = extract_device_type(df["DeviceInfo"])  # Desktop, Mobile, Tablet
```

**id_31 Analysis:**
```python
# Example values: browser version strings, device identifiers
# Extract: structured components if pattern found

df["id_31_category"] = categorize_id31(df["id_31"])
```

**Post-Extraction Decision:**
- If extracted features have low missing % and high cardinality reduction: KEEP extracted, DROP original
- If extraction yields minimal value: KEEP original DeviceInfo/id_31 as categorical

### 3.4 Identity Availability Indicator

**Keep from v1.0:**
```python
# Binary indicator: does transaction have ANY identity data?
id_cols = [c for c in df.columns if c.startswith("id_")]
df["has_identity"] = df[id_cols].notna().any(axis=1).astype(int)
```

**Justification:** 3.7x fraud rate signal (see EDA section 9).

---

## 4. Revised Missing Value Imputation Strategy

### 4.1 Imputation by Feature Type

**No Change in Logic, More Conservative Application**

| Feature Type | Strategy | Value | Justification |
|--------------|----------|-------|---------------|
| **Numerical (V, C, D, dist, addr, card)** | Median | `df[col].median()` | Robust to outliers, preserves distribution |
| **Count Features (C-series)** | Zero | `0` | Missing counts → zero count |
| **Binary/Categorical (M-series)** | Mode | Most frequent | Preserve class balance |
| **Categorical (object dtype)** | Mode or "Unknown" | Most frequent or new category | Explicit missing indicator |

### 4.2 Implementation Note

Fit imputers on TRAIN set only, transform val/test with same parameters to prevent data leakage.

---

## 5. Revised Categorical Encoding Strategy

### 5.1 Replace LabelEncoder with OrdinalEncoder

**Problem with LabelEncoder:** 
- Assigns arbitrary integer order (0, 1, 2, ...) which may imply ordinal relationship
- Doesn't handle unseen categories in validation/test sets gracefully

**Solution: Use sklearn's OrdinalEncoder or pandas category dtype**

```python
from sklearn.preprocessing import OrdinalEncoder

# Option 1: OrdinalEncoder (handles unknown categories)
encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
df[cat_cols] = encoder.fit_transform(df[cat_cols])

# Option 2: Pandas category dtype (memory efficient)
for col in cat_cols:
    df[col] = df[col].astype("category")
```

### 5.2 Encoding Strategy by Cardinality

| Cardinality | Method | Example Features | Output Dimension |
|-------------|--------|------------------|------------------|
| **2-10 unique** | One-Hot | ProductCD (5), card4 (4), card6 (4) | +N-1 columns per feature |
| **11-20 unique** | Ordinal | M-series, id_12, DeviceType | Same column (encoded) |
| **21-100 unique** | Frequency or Ordinal | P_emaildomain (59), R_emaildomain (60) | Same column (encoded) |
| **>100 unique** | Frequency or Target | DeviceInfo (1,786), id_33 (260), id_31 (130) | Same column (encoded) |

### 5.3 Frequency Encoding

For high-cardinality features, replace category with its frequency in training set:

```python
freq_map = train_df[col].value_counts(normalize=True).to_dict()
df[col + "_freq"] = df[col].map(freq_map).fillna(0)  # Unseen categories → 0
```

**Advantage:** Single numerical column, captures popularity, no dimensionality explosion.

---

## 6. Revised Feature Scaling Strategy

### 6.1 NO Scaling for XGBoost/LightGBM

**Change:** Remove StandardScaler and MinMaxScaler from default pipeline.

**Justification:**
- Tree-based models (XGBoost, LightGBM, Random Forest) are **scale-invariant**
- Splits are based on feature value thresholds, not distances
- Scaling adds unnecessary complexity and potential data leakage risk
- Preserves interpretability (feature importance in original units)

**Exception:** If training neural networks later, enable scaling via config:

```yaml
scaling:
  enable_for_tree_models: false   # Default
  enable_for_neural_nets: true    # Optional future use
```

---

## 7. Revised Train/Val/Test Split Strategy

### 7.1 Time-Based Split (No Change)

**Maintained from v1.0:**

```python
# Sort by TransactionDT
df_sorted = df.sort_values("TransactionDT")

# Split: 60% train / 20% val / 20% test
train_end = int(len(df_sorted) * 0.6)
val_end = int(len(df_sorted) * 0.8)

train_df = df_sorted.iloc[:train_end]
val_df = df_sorted.iloc[train_end:val_end]
test_df = df_sorted.iloc[val_end:]
```

**Verification:**
```python
print(f"Train fraud rate: {train_df['isFraud'].mean():.4f}")
print(f"Val fraud rate: {val_df['isFraud'].mean():.4f}")
print(f"Test fraud rate: {test_df['isFraud'].mean():.4f}")

# Assert fraud rates within ±0.5% of overall rate
assert abs(train_df['isFraud'].mean() - 0.035) < 0.005
```

---

## 8. Revised Class Imbalance Handling

### 8.1 Remove SMOTE from Default Pipeline

**Change:** Do NOT use SMOTE by default.

**Rejected Approach (v1.0):**
```python
from imblearn.over_sampling import SMOTE

smote = SMOTE(sampling_strategy=0.3, random_state=42)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
```

**Approved Approach (v2.0):**

#### Primary: Use scale_pos_weight in XGBoost

```python
import xgboost as xgb

# Calculate class weight
neg_count = (y_train == 0).sum()
pos_count = (y_train == 1).sum()
scale_pos_weight = neg_count / pos_count  # ~27.58

# Train with class weighting
model = xgb.XGBClassifier(
    scale_pos_weight=scale_pos_weight,
    random_state=42,
)
model.fit(X_train, y_train)
```

#### Secondary: Threshold Optimization

```python
# Predict probabilities
y_proba = model.predict_proba(X_val)[:, 1]

# Optimize threshold for F1-score
from sklearn.metrics import f1_score

thresholds = np.arange(0.1, 0.9, 0.01)
f1_scores = [f1_score(y_val, y_proba >= t) for t in thresholds]
best_threshold = thresholds[np.argmax(f1_scores)]

print(f"Optimal threshold: {best_threshold:.3f}")
```

**Justification:**
- SMOTE creates synthetic samples that may not represent real fraud patterns
- scale_pos_weight is XGBoost's native class imbalance handling
- Threshold tuning optimizes for business metric (precision/recall trade-off)
- More interpretable and less prone to overfitting

---

## 9. Configuration Management

### 9.1 Externalized Configuration

**Created:** `ml/training/data/preprocessing_config.yaml`

**Key Configurable Parameters:**

```yaml
dropping:
  extreme_missing_threshold: 99.5  # Adjustable
  drop_constant_features: true
  drop_duplicates: true

imputation:
  numerical:
    strategy: "median"  # median, mean, zero
  categorical:
    strategy: "mode"

encoding:
  default_method: "ordinal"
  onehot_max_cardinality: 10
  frequency_min_cardinality: 20

class_imbalance:
  use_class_weights: true
  scale_pos_weight: "auto"
  use_smote: false
  optimize_threshold: true
```

**Advantages:**
- Change thresholds without code modification
- Version control for preprocessing decisions
- Easy experimentation with different strategies
- Clear documentation of current settings

---

## 10. Feature Inventory Documentation

### 10.1 Feature Inventory CSV

**Created:** `reports/milestone1/feature_inventory.csv`

**Columns:**
- `feature`: Feature name
- `dtype`: Data type (int64, float64, object)
- `missing_count`: Number of missing values
- `missing_pct`: Percentage missing (0-100)
- `unique_values`: Number of unique values
- `is_constant`: Boolean, only 1 unique value?
- `proposed_action`: DROP, KEEP, KEEP + IMPUTE, KEEP + ENCODE, etc.
- `justification`: Human-readable reason for action

**Sample:**
```csv
feature,dtype,missing_count,missing_pct,unique_values,is_constant,proposed_action,justification
TransactionID,int64,0,0.0,590540,False,DROP,Identifier column
isFraud,int64,0,0.0,2,False,KEEP,Target variable
TransactionAmt,float64,0,0.0,20665,False,KEEP + TRANSFORM,Keep original + create log
ProductCD,object,0,0.0,5,False,KEEP + ENCODE,Strong fraud signal
V1,float64,10752,1.82,1329,False,KEEP + IMPUTE,Low missing, impute median
id_24,float64,585793,99.20,12,False,KEEP + IMPUTE,High missing but keep for XGBoost
```

**Usage:**
- Review ALL 434 features systematically
- Audit preprocessing decisions
- Identify edge cases
- Document rationale for each feature

---

## 11. Revised Preprocessing Pipeline Order

### 11.1 Execution Steps

```
Step 1: LOAD DATA
  └─> Load train_transaction.csv + train_identity.csv
  └─> Merge on TransactionID
  └─> Result: 590,540 rows × 434 columns

Step 2: FEATURE ENGINEERING (before split)
  └─> Keep TransactionAmt (original)
  └─> Create TransactionAmt_log = log1p(TransactionAmt)
  └─> Create elapsed_time_days from TransactionDT
  └─> Extract browser/OS from DeviceInfo
  └─> Extract structured info from id_31
  └─> Create has_identity binary indicator
  └─> Result: ~434 + 6 new features = 440 columns

Step 3: DROP FEATURES (minimal)
  └─> Drop TransactionID (identifier)
  └─> Drop features >99.5% missing (if any)
  └─> Drop constant features (if any)
  └─> Drop perfect duplicates (if any)
  └─> Result: ~439 columns (only ~1 dropped)

Step 4: TRAIN/VAL/TEST SPLIT (time-based)
  └─> Sort by TransactionDT
  └─> Split: 60% train / 20% val / 20% test
  └─> Verify fraud rate preserved (±0.5%)

Step 5: IMPUTE MISSING VALUES (fit on train, transform val/test)
  └─> Numerical: Median
  └─> Categorical: Mode or "Unknown"
  └─> C-series: Zero
  └─> Result: 0% missing values

Step 6: ENCODE CATEGORICAL (fit on train, transform val/test)
  └─> One-Hot: ProductCD, card4, card6 (cardinality ≤10)
  └─> Ordinal: M-series, id_*, DeviceType (cardinality 2-20)
  └─> Frequency: DeviceInfo, P_emaildomain, id_33, id_31 (cardinality >20)
  └─> Result: ~445 columns (some one-hot expansion)

Step 7: NO SCALING
  └─> Skip scaling for XGBoost/LightGBM
  └─> Keep raw feature values

Step 8: VERIFY DATA QUALITY
  └─> Check: No nulls
  └─> Check: All numerical (no object dtype)
  └─> Check: No infinite values
  └─> Check: Fraud rate within acceptable range
  └─> Check: Shapes consistent

Step 9: SAVE PROCESSED DATA
  └─> backend/data/processed/train/features.csv
  └─> backend/data/processed/train/target.csv
  └─> backend/data/processed/val/features.csv
  └─> backend/data/processed/val/target.csv
  └─> backend/data/processed/test/features.csv
  └─> backend/data/processed/test/target.csv
  └─> backend/data/processed/preprocessing_artifacts/
      ├─ imputers.pkl
      ├─ encoders.pkl
      ├─ feature_names.json
      └─ config_snapshot.yaml
```

---

## 12. Expected Outcomes (Revised)

### 12.1 Before/After Comparison

| Metric | Before | After (v2.0) | Change | v1.0 (Rejected) |
|--------|--------|--------------|--------|-----------------|
| **Columns** | 434 | ~445 | +2.5% | ~165 (-62%) |
| **Memory (MB)** | 2,514 | ~2,100 | -16% | ~850 (-66%) |
| **Missing %** | 45.07% | 0% | -100% | 0% (-100%) |
| **Categorical Cols** | 31 | 0 | -100% | 0 (-100%) |
| **Features Dropped** | 0 | ~1-5 | Minimal | ~280 (Aggressive) |
| **Scaling Applied** | No | No | None | Yes (Unnecessary) |

### 12.2 Feature Count Breakdown

| Stage | Feature Count | Change |
|-------|---------------|--------|
| Raw merged data | 434 | - |
| + Feature engineering | 440 | +6 |
| - Dropped features | 439 | -1 |
| + Encoding (one-hot expansion) | ~445 | +6 |
| **Final** | **~445** | **+11 from original** |

---

## 13. Comparison: Version 1.0 vs Version 2.0

### 13.1 Philosophy Shift

| Aspect | Version 1.0 | Version 2.0 |
|--------|-------------|-------------|
| **Approach** | Aggressive preprocessing | Minimal preprocessing |
| **Dropping** | Drop early, ask questions later | Keep everything, let model decide |
| **Scaling** | Always scale | Only scale for neural nets |
| **Feature Count** | Minimize dimensions | Preserve information |
| **Configuration** | Hardcoded | Externalized (YAML) |
| **Documentation** | Strategy document only | Strategy + inventory CSV |

### 13.2 Why Version 2.0 is Better

1. **Preserves Signal:** XGBoost can find value in sparse features; dropping loses potential signal
2. **Less Risk:** Fewer preprocessing decisions = fewer opportunities for mistakes
3. **Configurable:** YAML config allows experimentation without code changes
4. **Auditable:** feature_inventory.csv documents every feature decision
5. **Model-Friendly:** Tree models work best with raw features, not scaled/engineered
6. **Simpler:** Fewer transformation steps = less complexity = fewer bugs

---

## 14. Risks & Mitigation (Revised)

### 14.1 Updated Risk Assessment

| Risk | Version 1.0 | Version 2.0 | Mitigation |
|------|-------------|-------------|------------|
| **Loss of signal from dropped features** | HIGH | MINIMAL | Only drop extreme cases; rely on model feature selection |
| **Memory constraints** | LOW | MEDIUM | Convert float64→float32; use category dtype |
| **High dimensionality** | LOW | MEDIUM | XGBoost handles high dimensions well; monitor training time |
| **Overfitting** | MEDIUM | MEDIUM | Use early stopping, max_depth limits, regularization |
| **DeviceInfo/id_31 extraction fails** | N/A | LOW | Fallback: keep original categorical |

---

## 15. Implementation Checklist

**DO NOT IMPLEMENT YET - Strategy approval required first**

- [ ] Load preprocessing_config.yaml
- [ ] Load feature_inventory.csv for reference
- [ ] Implement feature engineering (log, elapsed time, device extraction, has_identity)
- [ ] Implement minimal feature dropping (>99.5%, constant, duplicates, identifiers)
- [ ] Implement time-based split
- [ ] Implement imputation (median for numerical, mode for categorical)
- [ ] Implement encoding (one-hot, ordinal, frequency based on cardinality)
- [ ] Skip scaling entirely
- [ ] Implement data quality checks
- [ ] Save processed datasets and artifacts
- [ ] Generate before/after validation report
- [ ] Update PREPROCESSING_DECISIONS.md with actual decisions made

---

## 16. Next Steps

1. **User Approval:** Await approval of revised strategy
2. **Implementation:** Milestone 1C - implement preprocessing pipeline
3. **Validation:** Generate before/after comparison report
4. **Documentation:** Populate PREPROCESSING_DECISIONS.md with actual results
5. **Model Training:** Proceed to Milestone 2 with preprocessed data

---

**Status:** ✅ REVISED STRATEGY COMPLETE - Awaiting Final Approval

**Key Deliverables Created:**
- `feature_inventory.csv` (434 features documented)
- `preprocessing_config.yaml` (all thresholds externalized)
- This revised strategy document

**Ready for:** Final review and approval to proceed with Milestone 1C implementation
