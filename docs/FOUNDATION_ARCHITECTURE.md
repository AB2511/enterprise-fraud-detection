# ML Foundation Architecture

**Date:** July 7, 2026  
**Version:** 1.0.0  
**Status:** Production-Ready

---

## Overview

The ML Foundation provides a **reusable infrastructure** for enterprise fraud detection ML pipelines. It implements core engineering patterns for **data versioning**, **metadata management**, **validation**, **reproducibility**, and **pipeline orchestration**.

### Design Goals

1. **Pluggable Architecture** - Dataset adapters and transformers inherit from base classes
2. **Immutable Versioning** - Dataset versions are never overwritten
3. **Metadata-First** - All operations generate structured metadata
4. **Full Reproducibility** - Every pipeline run is deterministically reproducible
5. **Type Safety** - Pydantic schemas with runtime validation
6. **Production Quality** - Structured logging, error handling, testing

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        ML Foundation                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Dataset   │  │  Pipeline   │  │   Report    │            │
│  │  Adapters   │  │ Framework   │  │ Framework   │            │
│  │             │  │             │  │             │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Core Utilities                          │   │
│  ├─────────────┬─────────────┬─────────────┬─────────────┤   │
│  │   Logging   │  Metadata   │ Versioning  │   Config    │   │
│  │             │             │             │             │   │
│  └─────────────┴─────────────┴─────────────┴─────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Validation Framework                       │   │
│  ├─────────────┬─────────────┬─────────────┬─────────────┤   │
│  │   Schema    │  Missing    │ Duplicates  │   Ranges    │   │
│  │             │             │             │             │   │
│  └─────────────┴─────────────┴─────────────┴─────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Logging Framework (`ml/utils/logging_config.py`)

**Purpose:** Centralized structured logging for all ML operations

**Key Features:**
- JSON-structured logs with correlation IDs
- Pipeline stage context managers
- Automatic timing measurements
- Error categorization (7 categories)
- Console and file output

**Usage Example:**
```python
from ml.utils.logging_config import get_logger

logger = get_logger("ml.data.loading")

with logger.stage_context("data_validation"):
    logger.info("Starting validation", dataset_id="fraud_v1")
    # ... validation logic ...
    logger.error("Validation failed", error_category="DATA_QUALITY")
```

**Log Structure:**
```json
{
  "timestamp": "2024-07-07T12:00:00.000Z",
  "level": "INFO",
  "logger": "ml.data.loading",
  "correlation_id": "req_abc123",
  "pipeline_run_id": "run_def456",
  "stage": "data_validation",
  "message": "Starting validation",
  "dataset_id": "fraud_v1",
  "duration_ms": 1234
}
```

### 2. Metadata Management (`ml/utils/metadata.py`)

**Purpose:** Track all dataset, feature, and pipeline metadata

**Storage Structure:**
```
metadata/
├── datasets/           # Dataset versions and quality metrics
├── features/          # Feature definitions and importance
├── pipelines/         # Pipeline run history  
├── validations/       # Validation results
├── splits/           # Train/val/test split metadata
├── lineage/          # Data lineage graphs (JSONL)
├── statistics/       # Statistical summaries
└── history/          # Execution logs (JSONL)
```

**Key Classes:**
- `DatasetMetadata` - Dataset version info, quality scores, schema
- `FeatureMetadata` - Feature definitions, transformations, importance
- `PipelineRunMetadata` - Execution history, performance metrics
- `MetadataManager` - CRUD operations, lineage tracking

**Usage Example:**
```python
from ml.utils.metadata import MetadataManager, DatasetMetadata

manager = MetadataManager(metadata_root=Path("data/metadata"))

# Save dataset metadata
metadata = DatasetMetadata(
    dataset_name="creditcard_cleaned",
    version_id="20240707_120000_abc123",
    source="raw_creditcard",
    quality_score=0.95,
    row_count=284807,
    column_count=31,
)
manager.save_dataset_metadata(metadata)

# Track lineage
manager.add_lineage_edge("raw_creditcard", "creditcard_cleaned", "cleaning")
```

### 3. Dataset Versioning (`ml/data/versioning/dataset_version.py`)

**Purpose:** Immutable dataset versioning with integrity checks

**Key Features:**
- Unique version IDs: `YYYYMMDD_HHMMSS_uuid`
- SHA256 checksums for integrity
- Parent version tracking (lineage)
- Never overwrite existing versions
- DVC-ready directory structure

**Usage Example:**
```python
from ml.data.versioning.dataset_version import DatasetVersion

version = DatasetVersion(
    dataset_name="creditcard_processed",
    schema_version="v1.2.0", 
    preprocessing_version="v1.1.0",
    source="creditcard_cleaned",
    parent_version_id="20240706_180000_xyz789"
)

# Save immutably - raises FileExistsError if exists
output_path = version.save_dataframe(df, output_dir=Path("data/processed"))
```

**Version Registry:**
```python
# Lookup versions
registry = DatasetVersionRegistry(Path("data"))
latest = registry.get_latest_version("creditcard_processed")
all_versions = registry.list_versions("creditcard_processed")
```

### 4. Reproducibility (`ml/utils/reproducibility.py`)

**Purpose:** Ensure deterministic, reproducible pipeline runs

**Key Features:**
- Global random seed management
- Environment snapshots (Python, packages, platform)
- Configuration hashing
- Dependency version tracking

**Usage Example:**
```python
from ml.utils.reproducibility import get_reproducibility_manager

manager = get_reproducibility_manager(seed=42)
# All random seeds set automatically (Python, NumPy, pandas)

# Capture environment
snapshot = manager.capture_environment_snapshot()
manager.save_snapshot(Path("metadata/repro_20240707_120000.json"))

# Verify reproducibility
is_reproducible = manager.verify_environment(snapshot)
```

### 5. Configuration System (`ml/utils/config.py`)

**Purpose:** Typed configuration with validation and environment overrides

**Key Classes:**
- `PathConfig` - All directory paths
- `DatasetConfig` - Dataset loading options
- `ValidationConfig` - Validation thresholds
- `FeatureConfig` - Feature generation options
- `SplitConfig` - Train/val/test ratios
- `ExportConfig` - Output formats and compression
- `PipelineConfig` - Master configuration

**Usage Example:**
```python
from ml.utils.config import PipelineConfig, DatasetConfig

config = PipelineConfig(
    pipeline_name="fraud_detection_v1",
    random_seed=42,
    dataset=DatasetConfig(
        dataset_name="creditcard",
        source_path=Path("data/raw/creditcard.csv"),
        target_column="Class",
        id_column="transaction_id",
    ),
    paths=PathConfig(data_root=Path("data")),
)

# Environment variable override
config.dataset.source_path = Path(os.getenv("DATA_PATH", config.dataset.source_path))

# Save/load
config.save(Path("config/pipeline.json"))
loaded = PipelineConfig.load(Path("config/pipeline.json"))
```

### 6. File Management (`ml/utils/file_manager.py`)

**Purpose:** Safe file operations with integrity checks

**Key Features:**
- Atomic write operations (temp → rename)
- File hashing (SHA256, MD5)
- Dataset discovery and pattern matching
- Export utilities (Parquet, CSV, JSON)
- Hash verification

**Usage Example:**
```python
from ml.utils.file_manager import (
    atomic_write_dataframe, 
    compute_file_hash,
    discover_datasets,
    verify_file_hash
)

# Atomic write
atomic_write_dataframe(df, Path("data/output.parquet"), format="parquet")

# Compute and verify hash
checksum = compute_file_hash(Path("data/output.parquet"))
is_valid = verify_file_hash(Path("data/output.parquet"), checksum)

# Dataset discovery
datasets = discover_datasets(Path("data/processed"), pattern="*.parquet")
```

### 7. Validation Framework (`ml/validation/validators.py`)

**Purpose:** Extensible data validation with detailed reporting

**Base Classes:**
- `BaseValidator` - Abstract validator interface
- `ValidationCheck` - Individual check result
- `ValidationSummary` - Aggregated results

**Built-in Validators:**
1. `SchemaValidator` - Required columns, data types
2. `MissingValueValidator` - Missing value thresholds
3. `DuplicateValidator` - Duplicate row detection
4. `ValueRangeValidator` - Min/max bounds checking
5. `NullPercentageValidator` - Null percentage limits
6. `TimestampValidator` - Timestamp validation and ordering
7. `CategoricalConsistencyValidator` - Category cardinality checks
8. Custom validators inherit from `BaseValidator`

**Usage Example:**
```python
from ml.validation.validators import SchemaValidator, MissingValueValidator

# Schema validation
schema_validator = SchemaValidator(
    required_columns=["transaction_id", "amount", "Class"],
    column_types={"amount": "float64", "Class": "int64"}
)
checks = schema_validator.validate(df)

# Missing value validation  
missing_validator = MissingValueValidator(missing_threshold=0.1)
checks.extend(missing_validator.validate(df))

# Results
summary = schema_validator.get_summary()
# {'validator': 'SchemaValidator', 'total_checks': 3, 'passed': 3, 'failed': 0}
```

---

## Data Flow Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Raw Dataset   │    │  Dataset        │    │   Versioned     │
│   (External)    │───▶│  Adapter        │───▶│   Dataset       │
│                 │    │  (Load &        │    │   (Immutable)   │
└─────────────────┘    │   Standardize)  │    └─────────────────┘
                       └─────────────────┘              │
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Validation    │    │    Metadata     │
                       │   Framework     │    │    Manager      │
                       │   (Quality      │    │   (Lineage &    │
                       │    Checks)      │    │    History)     │
                       └─────────────────┘    └─────────────────┘
                                │                       │
                                └───────┬───────────────┘
                                        ▼
                              ┌─────────────────┐
                              │   Pipeline      │
                              │   Framework     │
                              │  (Orchestrate   │
                              │   Next Steps)   │
                              └─────────────────┘
```

### Stage Lifecycle

1. **Data Loading**
   - Dataset adapter loads raw data
   - Standardizes schema and formats
   - Generates initial metadata

2. **Validation** 
   - Runs configured validators
   - Records check results
   - Blocks pipeline on critical failures

3. **Versioning**
   - Creates immutable version with unique ID
   - Computes SHA256 checksum
   - Links to parent version (lineage)

4. **Metadata Storage**
   - Saves dataset metadata (quality, statistics)
   - Records validation results
   - Updates lineage graph

5. **Pipeline Continuation**
   - Next stages receive versioned dataset
   - All operations tracked and logged
   - Reproducible execution guaranteed

---

## Directory Structure

```
enterprise-fraud-detection/
├── ml/                              # ML Foundation Package
│   ├── __init__.py                  
│   ├── data/                        # Data Engineering
│   │   ├── adapters/                # Dataset adapters
│   │   │   ├── base.py             # BaseDatasetAdapter
│   │   │   └── __init__.py         
│   │   ├── loaders/                # Data loaders
│   │   ├── processors/             # Data processors  
│   │   └── versioning/             # Version management
│   │       ├── dataset_version.py  # DatasetVersion, Registry
│   │       └── __init__.py         
│   ├── pipeline/                   # Pipeline Framework
│   │   ├── stage.py               # PipelineStage, StageResult
│   │   ├── pipeline.py            # Pipeline, executor
│   │   ├── executor.py            # Pipeline execution
│   │   ├── registry.py            # Stage registry
│   │   └── __init__.py            
│   ├── reports/                   # Report Framework
│   │   ├── base.py               # BaseReport
│   │   ├── validation_report.py   # Validation reports
│   │   ├── metadata_report.py     # Metadata reports
│   │   ├── quality_report.py      # Quality reports
│   │   ├── pipeline_report.py     # Pipeline reports
│   │   └── __init__.py           
│   ├── testing/                  # Testing Infrastructure
│   │   ├── fixtures.py           # Test fixtures & mock data
│   │   ├── assertions.py         # Custom assertions
│   │   └── __init__.py          
│   ├── utils/                   # Core Utilities
│   │   ├── config.py           # Typed configurations
│   │   ├── file_manager.py     # File operations
│   │   ├── logging_config.py   # Structured logging
│   │   ├── metadata.py         # Metadata management
│   │   ├── reproducibility.py  # Reproducibility
│   │   └── __init__.py         
│   └── validation/             # Validation Framework
│       ├── schemas.py         # Data schemas
│       ├── validators.py      # Validation logic
│       └── __init__.py       
│
├── data/                      # Data Directories
│   ├── raw/                  # Raw datasets
│   ├── interim/              # Intermediate processing
│   ├── processed/            # Final processed datasets
│   ├── external/             # External reference data
│   ├── feature_store/        # Feature engineering outputs
│   ├── validation/           # Validation reports
│   ├── reports/              # Generated reports
│   └── metadata/             # Metadata storage
│       ├── datasets/         # Dataset metadata
│       ├── features/         # Feature metadata
│       ├── pipelines/        # Pipeline metadata
│       ├── validations/      # Validation results
│       ├── splits/           # Split metadata
│       ├── lineage/          # Lineage graphs
│       ├── statistics/       # Statistical summaries
│       └── history/          # Execution history
│
├── tests/ml/                 # Test Suite
│   ├── data/                # Data engineering tests
│   ├── pipeline/            # Pipeline tests
│   ├── reports/             # Report tests
│   ├── utils/               # Utility tests
│   ├── validation/          # Validation tests
│   ├── integration/         # Integration tests
│   └── __init__.py         
│
├── docs/                    # Documentation
│   ├── FOUNDATION_ARCHITECTURE.md
│   ├── PIPELINE_FRAMEWORK.md
│   ├── METADATA_SYSTEM.md
│   ├── VERSIONING_GUIDE.md
│   └── REPRODUCIBILITY_GUIDE.md
│
└── config/                  # Configuration Files
    └── pipeline.json       # Pipeline configurations
```

---

## Extension Points

The foundation is designed for extensibility:

### 1. Dataset Adapters

Inherit from `BaseDatasetAdapter`:

```python
from ml.data.adapters.base import BaseDatasetAdapter

class CreditCardAdapter(BaseDatasetAdapter):
    def load_data(self, source_path: Path) -> pd.DataFrame:
        # Custom loading logic
        pass
        
    def validate_raw_schema(self, df: pd.DataFrame) -> bool:
        # Schema validation
        pass
        
    def standardize_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        # Column standardization
        pass
```

### 2. Custom Validators

Inherit from `BaseValidator`:

```python
from ml.validation.validators import BaseValidator, ValidationCheck

class FraudRateValidator(BaseValidator):
    def validate(self, df: pd.DataFrame) -> List[ValidationCheck]:
        fraud_rate = df['is_fraud'].mean()
        
        return [ValidationCheck(
            validator_name="FraudRateValidator",
            check_name="fraud_rate_bounds",
            passed=0.01 <= fraud_rate <= 0.05,
            message=f"Fraud rate: {fraud_rate:.3f}",
            severity="warning" if fraud_rate > 0.05 else "info"
        )]
```

### 3. Pipeline Stages

Inherit from `PipelineStage`:

```python
from ml.pipeline.stage import PipelineStage

class FeatureEngineeringStage(PipelineStage):
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        df = inputs["dataset"]
        # Feature engineering logic
        return {"features": engineered_df}
```

### 4. Report Generators

Inherit from `BaseReport`:

```python
from ml.reports.base import BaseReport

class ModelPerformanceReport(BaseReport):
    def collect_data(self, model_results: Dict[str, Any]) -> None:
        self.data = model_results
        
    def generate_html(self) -> str:
        # HTML generation logic
        pass
```

---

## Quality Assurance

### 1. Type Safety
- All configurations use Pydantic models
- Runtime type validation
- IDE support with type hints

### 2. Error Handling
- Custom exception hierarchy
- Graceful degradation
- Detailed error messages with context

### 3. Testing Strategy
- Unit tests for all components
- Integration tests for workflows
- Mock data generators
- Property-based testing where applicable

### 4. Logging & Monitoring
- Structured JSON logs
- Performance metrics
- Error tracking
- Pipeline execution monitoring

---

## Production Considerations

### 1. Performance
- Lazy loading of large datasets
- Chunked processing for memory efficiency
- Parallel execution where possible
- File format optimization (Parquet)

### 2. Scalability
- Modular component design
- Configurable resource limits
- Horizontal scaling support
- Efficient metadata storage

### 3. Security
- Input validation and sanitization
- Safe file operations
- Audit logging
- Configurable access controls

### 4. Reliability
- Atomic operations
- Checkpointing and recovery
- Retry mechanisms
- Health checks

---

## Summary

The ML Foundation provides a **production-ready infrastructure** for enterprise fraud detection pipelines. Key benefits:

✅ **Reusable** - Dataset adapters plug into common interface  
✅ **Reproducible** - Full environment and configuration capture  
✅ **Auditable** - Complete metadata and lineage tracking  
✅ **Reliable** - Immutable versioning with integrity checks  
✅ **Extensible** - Plugin architecture for custom components  
✅ **Type-Safe** - Runtime validation with Pydantic schemas  
✅ **Observable** - Structured logging and monitoring  

The foundation enables rapid development of ML pipelines while maintaining enterprise-grade quality, governance, and operational requirements.