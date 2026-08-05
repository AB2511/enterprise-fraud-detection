# IEEE-CIS Dataset Setup Guide

Quick reference for obtaining and validating the IEEE-CIS Fraud Detection dataset.

---

## Quick Start

```bash
# 1. Download dataset from Kaggle (manual or API)
# 2. Place files in data/raw/
# 3. Run validation:
python validate_real_dataset.py
```

---

## Required Files

Place these files in `data/raw/`:

| File | Size | Required | Description |
|------|------|----------|-------------|
| `train_transaction.csv` | ~500 MB | ✅ Yes | Training transactions |
| `train_identity.csv` | ~30 MB | ✅ Yes | Identity information |
| `test_transaction.csv` | ~450 MB | ⚪ Optional | Test transactions |
| `test_identity.csv` | ~25 MB | ⚪ Optional | Test identity |

---

## Method 1: Manual Download (Recommended)

### Step 1: Visit Kaggle
https://www.kaggle.com/c/ieee-fraud-detection/data

### Step 2: Accept Rules
- Click "I Understand and Accept"
- Agree to competition rules

### Step 3: Download Files
Click "Download All" or download individually:
- `train_transaction.csv`
- `train_identity.csv`
- `test_transaction.csv` (optional)
- `test_identity.csv` (optional)

### Step 4: Extract
Unzip the downloaded files.

### Step 5: Move to Project
Move CSV files to:
```
D:\Hackathon\enterprise-fraud-detection\data\raw\
```

### Step 6: Verify
```bash
dir data\raw
```

Should show:
```
train_transaction.csv
train_identity.csv
```

---

## Method 2: Kaggle API

### Prerequisites
```bash
pip install kaggle
```

### Configure API Key

1. Go to: https://www.kaggle.com/settings
2. Click "Create New API Token"
3. Download `kaggle.json`
4. Place in:
   - Windows: `%USERPROFILE%\.kaggle\kaggle.json`
   - Linux/Mac: `~/.kaggle/kaggle.json`

### Download Dataset

```bash
# Navigate to project root
cd D:\Hackathon\enterprise-fraud-detection

# Download competition files
kaggle competitions download -c ieee-fraud-detection

# Extract to data/raw
# Windows PowerShell:
Expand-Archive ieee-fraud-detection.zip -DestinationPath data\raw\

# Or use 7-Zip, WinRAR, etc.
```

---

## Validation

### Run Validator

```bash
python validate_real_dataset.py
```

### Expected Output (Success)

```
======================================================================
MILESTONE 1A.5: REAL DATASET VALIDATION
======================================================================

✓ All required dataset files found

======================================================================
STEP 1: Loading Individual Tables
======================================================================

Loading train_transaction.csv...
✓ Loaded: 590,540 rows, 394 columns
  Memory: 456.78 MB

Loading train_identity.csv...
✓ Loaded: 144,233 rows, 41 columns
  Memory: 38.92 MB

======================================================================
STEP 2: Schema Validation (Individual Tables)
======================================================================

Validating train_transaction.csv schema...
Schema Validation: ✓ PASSED

Validating train_identity.csv schema...
Schema Validation: ✓ PASSED

======================================================================
STEP 3: Merging Datasets
======================================================================

Merging transaction and identity tables...
✓ Merged dataset: 590,540 rows, 433 columns
  Memory: 623.45 MB

✓ No rows lost during merge

======================================================================
STEP 4: Dataset Analysis
======================================================================

Target Distribution:
  Total transactions: 590,540
  Fraud cases: 20,663
  Legitimate cases: 569,877
  Fraud rate: 0.0350 (3.50%)

Top 10 Columns with Highest Missing Values:
  dist2                           506,848 (85.82%)
  dist1                           493,887 (83.63%)
  D10                             483,039 (81.79%)
  D9                              483,039 (81.79%)
  D8                              482,672 (81.73%)
  D7                              471,407 (79.83%)
  ...

Column Type Distribution:
  float64                375 columns
  int64                   29 columns
  object                  29 columns

Memory Usage:
  Total: 623.45 MB

Duplicate Check:
  ✓ No duplicate TransactionIDs

======================================================================
STEP 5: Generating Dataset Summary
======================================================================

✓ Summary saved to: reports\milestone1\dataset_summary.json

Dataset Summary: IEEE-CIS Fraud Detection
============================================================
Rows: 590,540
Columns: 433
Memory Usage: 623.45 MB

Target Distribution:
  Total Samples: 590,540
  Fraud Cases: 20,663
  Legitimate Cases: 569,877
  Fraud Rate: 0.0350 (3.50%)

...

======================================================================
STATUS: COMPLETE
======================================================================

✅ Real dataset successfully validated

Summary report: reports\milestone1\dataset_summary.json

Ready to proceed to Milestone 1B
```

### Expected Output (Missing Files)

```
======================================================================
IEEE-CIS DATASET NOT FOUND
======================================================================

Expected directory:
  D:\Hackathon\enterprise-fraud-detection\data\raw

File status:
  ✗ MISSING: train_transaction.csv
  ✗ MISSING: train_identity.csv
  ...

[Instructions for obtaining dataset...]
```

---

## Troubleshooting

### Issue: "File not found"

**Solution**:
- Verify files are in `data/raw/` (not in subdirectories)
- Check file names match exactly (case-sensitive on Linux/Mac)
- Ensure CSV files are extracted (not still in ZIP)

### Issue: "Permission denied"

**Solution**:
```bash
# Windows: Run as administrator
# Or check file permissions
```

### Issue: "Memory error"

**Solution**:
- Close other applications
- System needs at least 2GB free RAM
- Consider upgrading RAM or using a more powerful machine

### Issue: "Kaggle API not configured"

**Solution**:
1. Download `kaggle.json` from Kaggle settings
2. Place in correct location
3. Set permissions (Linux/Mac):
   ```bash
   chmod 600 ~/.kaggle/kaggle.json
   ```

### Issue: "Invalid CSV format"

**Solution**:
- Re-download files (may be corrupted)
- Verify file sizes match expected
- Check for complete download (no partial files)

---

## Dataset Information

### Training Data

- **train_transaction.csv**: 590,540 transactions
  - 394 columns
  - Key columns: TransactionID, isFraud, TransactionDT, TransactionAmt
  - Many V-columns (numerical features)
  - Many C-columns (categorical features)
  - Many D-columns (time deltas)
  - Many M-columns (match features)

- **train_identity.csv**: 144,233 identity records
  - 41 columns
  - Links to transactions via TransactionID
  - Device information
  - Identity verification details
  - ~24% of transactions have identity info

### After Merge

- **Combined**: 590,540 rows × 433 columns
- **Memory**: ~600 MB
- **Fraud Rate**: 3.5%
- **Missing Values**: Many features have >80% missing

---

## Next Steps After Validation

Once validation succeeds:

1. ✅ Review `reports/milestone1/dataset_summary.json`
2. ✅ Check for any warnings or data quality issues
3. ✅ Proceed to Milestone 1B (Data Quality Analysis)

---

## Support

If you encounter issues:
1. Check the error message carefully
2. Review this troubleshooting section
3. Verify file locations and names
4. Ensure sufficient disk space and memory
5. Check Kaggle competition page for dataset updates

---

**Dataset Source**: [IEEE-CIS Fraud Detection on Kaggle](https://www.kaggle.com/c/ieee-fraud-detection)

**License**: Check Kaggle competition rules
