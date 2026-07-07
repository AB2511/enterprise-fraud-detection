# ML Data Engineering Foundation
## Quick Reference Guide

**Version:** 1.0.0  
**Status:** Core Foundation Complete (64%)  
**Date:** July 7, 2026

---

## Overview

The ML Data Engineering Foundation provides production-ready infrastructure for machine learning pipelines. All components are **reusable**, **type-safe**, and **dataset-agnostic**.

---

## Quick Start

### 1. Initialize Reproducible Environment

```python
from ml.utils.reproducibility import get_reproducibility_manager

# Sets all random seeds, configures Pandas, captures environment
manager = get_reproducibility_manager(seed=42)
```

### 2. Configure Pipeline

```python
from ml.utils.config import PipelineConfig, DatasetConfig
from pathlib import Path

config = PipelineConfig(
    pipeline_name="my_pipeline",
    random_seed=42,
    dataset=DatasetConfig(
        dataset_name="my_dataset",
        dataset_type="custom",
        source_path=Path("data/raw/my_data.csv"),
    )
)
```

### 3. Set Up Logging

```python
from ml.utils.logging_config import get_logger

logger = get_logger("my_pipeline", log_level="INFO")

with logger.stage_context("data_loading"):
    # Your code here - timing automatic
    logger.info("Loading data", records=1000)
```

### 4. Load and Version Dataset

```python
from ml.data.adapters.base import DatasetAdapter
from ml.data.versioning.dataset_version import DatasetVersion

# Create version
version = DatasetVersion(
    dataset_name="my_dataset",
    schema_version="v1.0.0",
    source="custom"
)

# Save with automatic checksumming
filepath = version.save_dataframe(df, output_dir=Path("data/processed"))
```

### 5. Validate Data

```python
from ml.validation.validators import SchemaValidator, MissingValueValidator

validators = [
    SchemaValidator(
        required_columns=["id", "amount", "target"],
        column_types={"amount": "float", "target": "bool"}
    ),
    MissingValueValidator(max_missing_rate=0.10)
]

for validator in validators:
    checks = validator.validate(df)
    summary = validator.get_summary()
    print(summary)
```

### 6. Track Metadata

```python
from ml.utils.metadata import MetadataManager

manager = MetadataManager(metadata_root=Path("data/metadata"))

# Save dataset metadata
manager.save_dataset_metadata(dataset_metadata)

# Track lineage
manager.add_lineage_edge(
    source_id="raw_data",
    target_id="processed_data",
    transformation="cleaning"
)
```

---

## Available Components

### ✅ Logging (`ml/utils/logging_config.py`)
- Structured JSON logging
- Stage context managers
- Correlation IDs
- Execution timing

### ✅ Metadata (`ml/utils/metadata.py`)
- Dataset metadata
- Pipeline runs
- Lineage tracking
- Execution history

### ✅ Versioning (`ml/data/versioning/dataset_version.py`)
- Immutable versions
- SHA256 checksums
- Version registry
- DVC-ready

### ✅ Reproducibility (`ml/utils/reproducibility.py`)
- Seed management
- Environment snapshots
- Configuration hashing

### ✅ Configuration (`ml/utils/config.py`)
- Typed Pydantic models
- Environment overrides
- JSON save/load

### ✅ File Management (`ml/utils/file_manager.py`)
- Atomic writes
- File hashing
- Safe reads
- Export utilities

### ✅ Validation (`ml/validation/validators.py`)
- 8 base validators
- Schema validation
- Missing value checks
- Duplicate detection
- Range validation

---

## Common Patterns

### Pattern 1: Full Pipeline with Logging and Versioning

```python
from ml.utils.logging_config import get_logger
from ml.utils.reproducibility import get_reproducibility_manager
from ml.data.versioning.dataset_version import DatasetVersion

# Initialize
manager = get_reproducibility_manager(seed=42)
logger = get_logger("pipeline")

# Load
with logger.stage_context("loading"):
    df = pd.read_csv("data/raw/data.csv")
    logger.log_dataset_info("dataset_001", len(df))

# Process
with logger.stage_context("processing"):
    df_processed = process_data(df)

# Version
version = DatasetVersion(dataset_name="processed_data", source="raw")
version.save_dataframe(df_processed, Path("data/processed"))
```

### Pattern 2: Validation with Error Handling

```python
from ml.validation.validators import SchemaValidator, MissingValueValidator

validators = [
    SchemaValidator(required_columns=["id", "value"]),
    MissingValueValidator(max_missing_rate=0.05, critical_columns=["id"])
]

all_passed = True
for validator in validators:
    checks = validator.validate(df)
    for check in checks:
        if not check.passed and check.severity in ["critical", "error"]:
            logger.error(f"Validation failed: {check.message}")
            all_passed = False

if not all_passed:
    raise ValueError("Data validation failed")
```

### Pattern 3: Metadata and Lineage Tracking

```python
from ml.utils.metadata import MetadataManager
from ml.validation.schemas import DatasetMetadata, ProcessingStage

metadata_mgr = MetadataManager(Path("data/metadata"))

# Create metadata
metadata = DatasetMetadata(
    dataset_name="processed_data",
    dataset_type="custom",
    version="v1.0.0",
    stage=ProcessingStage.PROCESSED,
    num_records=len(df),
    num_fraud=int(df['is_fraud'].sum()),
    num_legitimate=len(df) - int(df['is_fraud'].sum()),
    fraud_rate=df['is_fraud'].mean()
)

# Save metadata
metadata_mgr.save_dataset_metadata(metadata)

# Track lineage
metadata_mgr.add_lineage_edge(
    source_id="raw_dataset",
    target_id=metadata.dataset_id,
    transformation="cleaning_and_validation"
)
```

---

## Directory Structure

```
data/
├── raw/                 # Original immutable datasets
├── interim/             # Intermediate transformations
├── processed/           # Final processed datasets
├── metadata/            # All metadata (JSON)
│   ├── datasets/
│   ├── pipelines/
│   ├── validations/
│   └── lineage/
├── validation/          # Validation reports
└── reports/             # Data quality reports
```

---

## Data Contracts (Pydantic Schemas)

All data structures are defined in `ml/validation/schemas.py`:

- `RawTransaction` - Raw transaction data
- `ProcessedTransaction` - Cleaned transaction data
- `FeatureVector` - Feature data for ML
- `DatasetMetadata` - Dataset version metadata
- `PipelineRunMetadata` - Pipeline execution metadata
- `ValidationResult` - Validation results
- `SplitMetadata` - Train/val/test split metadata

---

## Configuration Options

### PathConfig
```python
PathConfig(
    data_root=Path("data"),
    raw_data_dir=Path("data/raw"),
    processed_data_dir=Path("data/processed"),
    # ... more paths
)
```

### ValidationConfig
```python
ValidationConfig(
    fail_on_error=True,
    max_missing_rate_critical=0.05,
    check_duplicates=True,
    generate_html_report=True,
)
```

### SplitConfig
```python
SplitConfig(
    strategy="stratified",  # or "time_aware", "random"
    train_ratio=0.75,
    val_ratio=0.125,
    test_ratio=0.125,
    random_seed=42,
)
```

---

## Validators Reference

| Validator | Purpose | Key Parameters |
|-----------|---------|----------------|
| `SchemaValidator` | Check schema | `required_columns`, `column_types` |
| `MissingValueValidator` | Check missing values | `max_missing_rate`, `critical_columns` |
| `DuplicateValidator` | Detect duplicates | `max_duplicate_rate`, `subset` |
| `ValueRangeValidator` | Validate ranges | `range_specs` (min/max per column) |
| `NullPercentageValidator` | Check null % | `max_null_percentage` |
| `TimestampValidator` | Validate timestamps | `timestamp_columns`, `allow_future` |
| `CategoricalConsistencyValidator` | Check cardinality | `categorical_columns`, `max_unique_ratio` |

---

## Troubleshooting

### Issue: "Version already exists"
**Cause:** Trying to overwrite an immutable version  
**Solution:** Versions are immutable by design. Create a new version with a different ID.

### Issue: "Checksum mismatch"
**Cause:** Dataset file was modified after versioning  
**Solution:** Investigate file corruption. Re-generate the dataset.

### Issue: "Schema validation failed"
**Cause:** DataFrame doesn't match expected schema  
**Solution:** Check required columns and data types. Update adapter if needed.

### Issue: "Metadata not found"
**Cause:** Metadata file doesn't exist  
**Solution:** Ensure pipeline saved metadata before attempting to load.

---

## Best Practices

1. **Always initialize reproducibility first**
   ```python
   from ml.utils.reproducibility import get_reproducibility_manager
   get_reproducibility_manager(seed=42)
   ```

2. **Use context managers for timing**
   ```python
   with logger.stage_context("stage_name"):
       # code
   ```

3. **Version every dataset transformation**
   ```python
   version = DatasetVersion(dataset_name="...", parent_version_id=parent.version_id)
   ```

4. **Validate before and after processing**
   ```python
   # Validate raw data
   # Process
   # Validate processed data
   ```

5. **Track all lineage**
   ```python
   metadata_mgr.add_lineage_edge(source, target, transformation_name)
   ```

---

## Testing

Testing infrastructure not yet implemented. Once available:

```python
# tests/ml/test_validators.py
from ml.validation.validators import SchemaValidator

def test_schema_validator():
    validator = SchemaValidator(required_columns=["id"])
    checks = validator.validate(mock_df)
    assert all(c.passed for c in checks)
```

---

## Next Steps

1. **Implement dataset adapters** (CreditCard, IEEE-CIS)
2. **Implement feature transformers** (amount, velocity, merchant, etc.)
3. **Add pipeline orchestration** framework
4. **Generate data quality reports**
5. **Create EDA notebooks**
6. **Implement testing infrastructure**

---

## Resources

- ML Design Specification: `ML_DESIGN_SPECIFICATION.md`
- Phase 1 Plan: `ML_PHASE_1_PLAN.md`
- Foundation Status: `ML_PHASE_1_1_COMPLETE.md`
- Architecture: `ARCHITECTURE.md`

---

**Questions?** Check the implementation files for detailed docstrings and examples.

**Status:** ✅ Core foundation ready for dataset adapters
