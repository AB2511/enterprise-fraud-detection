# Milestone 1: Dataset Loading, Validation & Analysis

**Date**: August 1, 2026  
**Status**: Ready for Implementation  
**Approved**: YES

---

## 🎯 Objective

Load and validate the IEEE-CIS fraud dataset from local files, perform comprehensive data quality analysis, and generate a detailed report to inform preprocessing decisions.

---

## 📋 Requirements

### Dataset Location (Assumed to Exist)
```
data/raw/
├── train_transaction.csv
└── train_identity.csv
```

### Success Criteria
1. ✅ Load both CSV files successfully
2. ✅ Validate dataset schema and integrity
3. ✅ Generate comprehensive data quality report
4. ✅ Identify missing values, outliers, distributions
5. ✅ Recommend preprocessing strategies
6. ✅ All code passes ruff, black, mypy
7. ✅ Graceful failure if files missing

---

## 📂 Files to Create

### 1. `ml/data/loader.py` (NEW)
**Purpose**: Load and validate IEEE-CIS dataset  
**Functions**:
- `load_fraud_dataset()` - Load both CSVs, merge on TransactionID
- `validate_dataset_exists()` - Check files exist
- `validate_schema()` - Validate columns and types
- Error handling with clear messages

### 2. `ml/data/quality_checker.py` (NEW)
**Purpose**: Comprehensive data quality analysis  
**Analysis**:
- Missing value statistics
- Data type validation
- Numerical feature distributions (mean, std, min, max, quantiles)
- Categorical feature cardinality
- Target class distribution (fraud rate)
- Outlier detection (IQR method)
- Duplicate detection
- Memory usage analysis

### 3. `ml/data/exploratory_analysis.py` (NEW)
**Purpose**: Generate EDA visualizations and insights  
**Visualizations**:
- Target distribution (fraud vs legitimate)
- Missing values heatmap
- Numerical feature distributions (histograms)
- Correlation matrix
- Feature importance (if quick to compute)
- Temporal patterns (if timestamp exists)

### 4. `ml/reports/data_quality_report.py` (NEW)
**Purpose**: Generate comprehensive quality report  
**Report Sections**:
1. Dataset Overview (rows, columns, memory)
2. Target Distribution
3. Missing Values Analysis
4. Numerical Features Summary
5. Categorical Features Summary
6. Data Quality Issues
7. Preprocessing Recommendations

### 5. `scripts/analyze_dataset.py` (NEW)
**Purpose**: CLI entry point for Milestone 1  
**Usage**:
```bash
python scripts/analyze_dataset.py \
  --data-dir ./data/raw \
  --output-dir ./reports/milestone1
```

### 6. `ml/data/__init__.py` (UPDATE)
Add exports for new modules

---

## 🔧 Dependencies to Add

Update `requirements.txt`:
```
# Data Analysis
pandas==2.2.0
numpy==1.26.3
scipy==1.12.0

# Visualization
matplotlib==3.8.2
seaborn==0.13.1

# Reporting
tabulate==0.9.0
```

---

## 📊 Expected Outputs

### Console Output
```
✓ Dataset files found
✓ Loaded train_transaction.csv: 590,540 rows, 394 columns
✓ Loaded train_identity.csv: 144,233 rows, 41 columns
✓ Merged dataset: 590,540 rows, 433 columns
✓ Validated schema
✓ Generated data quality report

Summary:
- Fraud rate: 3.5%
- Missing values: 35% of features have >50% missing
- Numerical features: 280
- Categorical features: 153
- Data quality issues: 12 identified
- Recommendations: 5 preprocessing steps suggested

Report saved to: reports/milestone1/data_quality_report.html
```

### Generated Files
```
reports/milestone1/
├── data_quality_report.html         # Comprehensive HTML report
├── data_quality_report.json         # Machine-readable report
├── missing_values_heatmap.png       # Visualization
├── target_distribution.png          # Fraud vs legitimate
├── numerical_distributions.png      # Feature histograms
├── correlation_matrix.png           # Feature correlations
└── summary_statistics.csv           # Detailed stats
```

---

## 🧪 Testing

### Test File: `tests/test_data_loader.py` (NEW)
**Tests**:
- Test missing files error handling
- Test successful load
- Test schema validation
- Test merge logic
- Test error messages

### Test File: `tests/test_quality_checker.py` (NEW)
**Tests**:
- Test missing value detection
- Test outlier detection
- Test target distribution calculation
- Test quality issue identification

---

## 📝 Implementation Steps

### Step 1: Setup (30 min)
1. Add dependencies to requirements.txt
2. Create directory structure
3. Update .gitignore for reports/

### Step 2: Data Loader (2 hours)
1. Implement loader.py
2. Add validation logic
3. Error handling for missing files
4. Test with sample data

### Step 3: Quality Checker (2-3 hours)
1. Implement quality_checker.py
2. Missing value analysis
3. Distribution analysis
4. Outlier detection
5. Quality issue identification

### Step 4: Exploratory Analysis (2-3 hours)
1. Implement exploratory_analysis.py
2. Generate visualizations
3. Correlation analysis
4. Temporal patterns

### Step 5: Reporting (1-2 hours)
1. Implement data_quality_report.py
2. HTML report generation
3. JSON output for automation
4. Recommendations engine

### Step 6: CLI Script (1 hour)
1. Implement analyze_dataset.py
2. Argument parsing
3. Progress indicators
4. Summary output

### Step 7: Testing (1-2 hours)
1. Write unit tests
2. Test error scenarios
3. Validate outputs

### Step 8: Quality Checks (30 min)
1. Run ruff
2. Run black
3. Run mypy
4. Fix any issues

**Total Estimate: 10-12 hours**

---

## ✅ Acceptance Criteria

### Functional ✅
- [ ] Loads train_transaction.csv successfully
- [ ] Loads train_identity.csv successfully
- [ ] Merges datasets correctly
- [ ] Detects missing files gracefully
- [ ] Validates dataset schema
- [ ] Generates quality report
- [ ] Creates all visualizations
- [ ] Produces recommendations

### Quality ✅
- [ ] Ruff passes with 0 errors
- [ ] Black formatting passes
- [ ] Mypy type checking passes (if applicable)
- [ ] Unit tests pass
- [ ] Report is readable and actionable

### Documentation ✅
- [ ] All functions have docstrings
- [ ] Type hints on all functions
- [ ] README explains how to run analysis
- [ ] Report is self-explanatory

---

## 🔍 Key Deliverables for Review

After Milestone 1 completion, review will focus on:

1. **Data Quality Report**
   - Is fraud rate reasonable (~3.5%)?
   - Which features have excessive missing values?
   - Are there data integrity issues?

2. **Preprocessing Recommendations**
   - Which features to drop (>80% missing)?
   - Which features need imputation?
   - Which features need encoding?
   - Which features need scaling?

3. **Dataset Readiness**
   - Is the dataset suitable for training?
   - Are there blockers (data corruption, wrong format)?
   - Do we need additional data cleaning?

---

## 🚦 Go/No-Go Decision

Based on Milestone 1 results, we will decide:

✅ **GO**: Proceed to preprocessing & training  
❌ **NO-GO**: Address data quality issues first  
⚠️ **CAUTION**: Proceed with modifications

---

## 📋 Next Steps After Milestone 1

If approved:
1. **Milestone 2**: Preprocessing pipeline
2. **Milestone 3**: Feature engineering
3. **Milestone 4**: Model training
4. **Milestone 5**: Evaluation & artifacts

---

**Ready to implement Milestone 1.**

