# Metadata System Documentation

**Version:** 1.0.0  
**Date:** July 7, 2026  
**Status:** Production-Ready

---

## Overview

The Metadata System provides **centralized tracking** of all ML pipeline artifacts, including datasets, features, pipeline runs, and data lineage. It enables **full auditability**, **reproducibility**, and **governance** for enterprise ML workflows.

---

## Core Components

### 1. MetadataManager (`ml/utils/metadata.py`)

**Purpose:** Central hub for all metadata operations

**Key Features:**
- CRUD operations for all metadata types
- Data lineage tracking (directed graph)
- Execution history logging (JSONL)
- Query and search capabilities
- JSON storage (human-readable, version-controllable)

```python
from ml.utils.metadata import MetadataManager

manager = MetadataManager(metadata_root=Path("data/metadata"))

# Save dataset metadata
metadata = DatasetMetadata(...)
manager.save_dataset_metadata(metadata)

# Track lineage
manager.add_lineage_edge("raw_data", "cleaned_data", "data_cleaning")

# Query
latest_datasets = manager.get_latest_datasets(limit=10)
feature_lineage = manager.get_feature_lineage("customer_risk_score")
```

---

## Metadata Types

### 1. DatasetMetadata

**Purpose:** Track dataset versions, quality, and characteristics

```python
@dataclass
class DatasetMetadata:
    dataset_name: str                   # Dataset identifier
    version_id: str                     # Unique version ID
    created_at: datetime               # Creation timestamp
    source: str                        # Source system/file
    file_path: str                     # Storage location
    file_size_bytes: int              # File size
    checksum: str                      # SHA256 checksum
    schema_version: str               # Schema version
    preprocessing_version: str         # Preprocessing version
    row_count: int                    # Number of rows
    column_count: int                 # Number of columns
    null_count: int                   # Total null values
    duplicate_count: int              # Duplicate rows
    quality_score: float              # Overall quality (0-1)
    column_info: Dict[str, Dict]      # Per-column statistics
    statistics: Dict[str, Any]        # Statistical summaries
    tags: List[str]                   # Searchable tags
    parent_version_id: Optional[str]  # Lineage parent
```

**Usage Example:**
```python
metadata = DatasetMetadata(
    dataset_name="creditcard_processed",
    version_id="20240707_120000_abc123",
    created_at=datetime.utcnow(),
    source="creditcard_raw",
    file_path="data/processed/creditcard_processed/20240707_120000_abc123.parquet",
    file_size_bytes=15728640,
    checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    schema_version="v1.2.0",
    preprocessing_version="v1.1.0",
    row_count=284807,
    column_count=31,
    null_count=0,
    duplicate_count=0,
    quality_score=0.98,
    column_info={
        "Time": {
            "dtype": "float64",
            "null_count": 0,
            "min": 0.0,
            "max": 172792.0,
            "mean": 94813.86,
            "std": 47488.15
        },
        "Amount": {
            "dtype": "float64", 
            "null_count": 0,
            "min": 0.0,
            "max": 25691.16,
            "mean": 88.35,
            "std": 250.12
        },
        "Class": {
            "dtype": "int64",
            "null_count": 0,
            "unique_count": 2,
            "value_counts": {"0": 284315, "1": 492}
        }
    },
    statistics={
        "fraud_rate": 0.001727,
        "missing_rate": 0.0,
        "feature_correlation_max": 0.005393
    },
    tags=["fraud_detection", "processed", "balanced"],
    parent_version_id="20240707_100000_xyz789"
)
```

### 2. FeatureMetadata

**Purpose:** Document feature definitions, transformations, and importance

```python
@dataclass
class FeatureMetadata:
    feature_name: str                 # Feature identifier
    data_type: str                   # Data type (int64, float64, object, bool)
    description: str                 # Human-readable description
    source_columns: List[str]        # Source columns used
    transformation: str              # Transformation applied
    importance_score: Optional[float] # Feature importance (0-1)
    null_percentage: float           # Null percentage
    unique_values: Optional[int]     # Number of unique values
    min_value: Optional[float]       # Minimum value (numeric)
    max_value: Optional[float]       # Maximum value (numeric)  
    mean_value: Optional[float]      # Mean value (numeric)
    std_value: Optional[float]       # Standard deviation (numeric)
    created_at: datetime            # Creation timestamp
    tags: List[str]                 # Searchable tags
```

**Usage Example:**
```python
feature_metadata = FeatureMetadata(
    feature_name="transaction_amount_log",
    data_type="float64",
    description="Log-transformed transaction amount for better distribution",
    source_columns=["Amount"],
    transformation="log1p(Amount)",
    importance_score=0.23,
    null_percentage=0.0,
    unique_values=None,  # Continuous variable
    min_value=0.0,
    max_value=10.15,
    mean_value=3.26,
    std_value=1.82,
    created_at=datetime.utcnow(),
    tags=["numerical", "transformed", "high_variance"]
)
```

### 3. PipelineRunMetadata

**Purpose:** Track pipeline execution history and performance

```python
@dataclass  
class PipelineRunMetadata:
    pipeline_name: str               # Pipeline identifier
    run_id: str                     # Unique run ID
    started_at: datetime            # Start timestamp
    completed_at: Optional[datetime] # End timestamp
    status: str                     # success, failed, running
    config_hash: str               # Configuration checksum
    input_datasets: List[str]      # Input dataset versions
    output_datasets: List[str]     # Output dataset versions
    metrics: Dict[str, Any]        # Performance metrics
    git_commit: Optional[str]      # Git commit hash
    environment_snapshot: Dict     # Environment info
```

**Usage Example:**
```python
run_metadata = PipelineRunMetadata(
    pipeline_name="fraud_detection_v1",
    run_id="run_20240707_120000_def456",
    started_at=datetime(2024, 7, 7, 12, 0, 0),
    completed_at=datetime(2024, 7, 7, 12, 45, 32),
    status="success",
    config_hash="a1b2c3d4e5f6",
    input_datasets=["creditcard_raw_20240707_080000"],
    output_datasets=[
        "creditcard_cleaned_20240707_120000",
        "creditcard_features_20240707_120500" 
    ],
    metrics={
        "total_execution_time_seconds": 2732,
        "rows_processed": 284807,
        "features_generated": 47,
        "validation_score": 0.98,
        "model_accuracy": 0.9924,
        "memory_peak_mb": 2048
    },
    git_commit="a1b2c3d4e5f6789",
    environment_snapshot={
        "python_version": "3.9.16",
        "pandas_version": "2.0.3",
        "scikit_learn_version": "1.3.0"
    }
)
```

---

## Storage Structure

### Directory Layout

```
metadata/
├── datasets/           # Dataset metadata
│   ├── creditcard_raw/
│   │   ├── 20240706_080000_abc123.json
│   │   ├── 20240707_080000_def456.json
│   │   └── latest.json -> 20240707_080000_def456.json
│   └── creditcard_processed/
│       ├── 20240707_120000_ghi789.json
│       └── latest.json -> 20240707_120000_ghi789.json
│
├── features/          # Feature metadata  
│   ├── transaction_amount_log.json
│   ├── customer_risk_score.json
│   └── merchant_category_encoded.json
│
├── pipelines/         # Pipeline run metadata
│   ├── fraud_detection_v1/
│   │   ├── run_20240707_120000_def456.json
│   │   └── run_20240707_140000_jkl012.json
│   └── data_preprocessing/
│       └── run_20240707_100000_mno345.json
│
├── validations/       # Validation results
│   ├── schema_validation_20240707_120000.json
│   └── quality_validation_20240707_120000.json
│
├── splits/           # Train/val/test split metadata
│   ├── creditcard_split_20240707_120000.json
│   └── ieee_cis_split_20240707_130000.json
│
├── lineage/          # Data lineage (JSONL format)
│   ├── 2024-07-07.jsonl
│   └── 2024-07-08.jsonl
│
├── statistics/       # Statistical summaries
│   ├── creditcard_stats_20240707.json
│   └── feature_correlations_20240707.json
│
└── history/          # Execution history (JSONL)
    ├── 2024-07-07.jsonl
    └── 2024-07-08.jsonl
```

### Lineage Format (JSONL)

```jsonl
{"timestamp": "2024-07-07T12:00:00Z", "source": "creditcard_raw", "target": "creditcard_cleaned", "operation": "data_cleaning", "run_id": "run_123"}
{"timestamp": "2024-07-07T12:15:00Z", "source": "creditcard_cleaned", "target": "creditcard_features", "operation": "feature_engineering", "run_id": "run_123"}
{"timestamp": "2024-07-07T12:30:00Z", "source": "creditcard_features", "target": "fraud_model_v1", "operation": "model_training", "run_id": "run_123"}
```

### Execution History Format (JSONL)

```jsonl
{"timestamp": "2024-07-07T12:00:00Z", "event": "pipeline_started", "pipeline": "fraud_detection_v1", "run_id": "run_123", "user": "ml_engineer"}
{"timestamp": "2024-07-07T12:05:00Z", "event": "stage_completed", "stage": "data_loading", "run_id": "run_123", "duration_seconds": 300}
{"timestamp": "2024-07-07T12:45:00Z", "event": "pipeline_completed", "pipeline": "fraud_detection_v1", "run_id": "run_123", "status": "success"}
```

---

## Data Lineage

### Lineage Graph

The system maintains a directed acyclic graph (DAG) of data transformations:

```
[Raw Data] ──cleaning──▶ [Cleaned Data] ──feature_eng──▶ [Features] ──training──▶ [Model]
     │                         │                           │
     └──validation──▶ [Validation Report]                  └──splitting──▶ [Train/Val/Test]
```

### Lineage Tracking

```python
# Track transformation steps
manager.add_lineage_edge(
    source_id="creditcard_raw_v1",
    target_id="creditcard_cleaned_v1", 
    operation="data_cleaning",
    metadata={
        "cleaning_rules": ["remove_nulls", "standardize_columns"],
        "records_removed": 1205,
        "run_id": "run_20240707_120000"
    }
)

# Query lineage
upstream = manager.get_upstream_lineage("fraud_model_v1", max_depth=3)
downstream = manager.get_downstream_lineage("creditcard_raw_v1")

# Lineage visualization
graph = manager.export_lineage_graph(format="graphviz")
```

### Impact Analysis

```python
# Find all downstream artifacts affected by a data change
affected_artifacts = manager.analyze_impact("creditcard_raw_v1")

# Example result:
# [
#   "creditcard_cleaned_v1",
#   "creditcard_features_v1", 
#   "fraud_model_v1",
#   "model_performance_report_v1"
# ]
```

---

## Query Interface

### Basic Queries

```python
# Get latest dataset versions
latest_datasets = manager.get_latest_datasets(limit=10)

# Search by tags
fraud_datasets = manager.search_datasets(tags=["fraud_detection"])

# Find datasets by quality score
high_quality = manager.search_datasets(min_quality_score=0.9)

# Get pipeline runs by status
failed_runs = manager.get_pipeline_runs(status="failed", limit=20)
```

### Advanced Queries

```python
# Time-based queries
recent_datasets = manager.get_datasets_in_timeframe(
    start_date=datetime(2024, 7, 1),
    end_date=datetime(2024, 7, 7)
)

# Feature importance queries
top_features = manager.get_features_by_importance(min_score=0.1, limit=20)

# Pipeline performance queries
slow_pipelines = manager.get_pipeline_runs(
    min_duration_seconds=3600,  # > 1 hour
    order_by="duration_seconds"
)
```

### Statistical Queries

```python
# Dataset statistics over time
stats = manager.get_dataset_statistics_timeline("creditcard_processed")

# Feature distribution changes
distribution = manager.get_feature_distribution_history("transaction_amount")

# Pipeline performance trends
performance = manager.get_pipeline_performance_trends("fraud_detection_v1")
```

---

## Metadata Validation

### Schema Validation

```python
from ml.utils.metadata import validate_metadata_schema

# Validate metadata before saving
try:
    validate_metadata_schema(dataset_metadata, "DatasetMetadata")
    manager.save_dataset_metadata(dataset_metadata)
except ValidationError as e:
    logger.error(f"Invalid metadata: {e}")
```

### Consistency Checks

```python
# Check for orphaned references
orphans = manager.validate_lineage_consistency()

# Verify file existence
missing_files = manager.validate_file_references()

# Check duplicate versions
duplicates = manager.detect_duplicate_versions()
```

---

## Metadata Synchronization

### Export/Import

```python
# Export metadata for backup or transfer
export_data = manager.export_metadata(
    start_date=datetime(2024, 7, 1),
    end_date=datetime(2024, 7, 7),
    format="json"
)

# Import metadata from another system
manager.import_metadata(
    source_path=Path("metadata_backup.json"),
    merge_strategy="overwrite"  # or "skip_existing"
)
```

### Metadata Versioning

```python
# Version metadata schemas
manager.upgrade_metadata_schema(
    from_version="1.0.0",
    to_version="1.1.0",
    migration_script="migrations/v1_0_to_v1_1.py"
)
```

---

## Integration with Other Systems

### MLflow Integration

```python
# Sync with MLflow experiment tracking
manager.sync_with_mlflow(
    experiment_name="fraud_detection",
    sync_direction="bidirectional"
)
```

### DVC Integration

```python
# Generate DVC pipeline configuration
dvc_config = manager.export_dvc_pipeline("fraud_detection_v1")

# Track dataset versions in DVC
manager.register_dvc_version("creditcard_processed", dvc_hash="a1b2c3")
```

### Database Integration

```python
# Sync metadata to database for advanced queries
manager.sync_to_database(
    connection_string="postgresql://user:pass@host:5432/mlmetadata",
    tables=["datasets", "pipelines", "lineage"]
)
```

---

## Monitoring & Alerting

### Metadata Quality Monitoring

```python
# Monitor for metadata quality issues
quality_alerts = manager.check_metadata_quality()

# Example alerts:
# - Missing required fields
# - Inconsistent data types
# - Broken lineage references
# - Stale metadata (> 30 days old)
```

### Automated Cleanup

```python
# Clean up old metadata (configurable retention)
cleanup_stats = manager.cleanup_old_metadata(
    retention_days=90,
    keep_latest_versions=5,
    dry_run=False
)
```

---

## Performance Optimization

### Indexing

```python
# Create indexes for fast queries
manager.create_indexes([
    "dataset_name",
    "created_at", 
    "tags",
    "quality_score"
])
```

### Caching

```python
# Enable metadata caching
manager.enable_cache(
    cache_size=1000,  # Max entries
    ttl_seconds=300   # 5 minute TTL
)
```

### Compression

```python
# Compress historical metadata
manager.compress_historical_data(
    older_than_days=30,
    compression="gzip"
)
```

---

## Best Practices

### 1. Metadata Design

- **Consistent Naming:** Use consistent naming conventions across all metadata
- **Rich Tags:** Add meaningful, searchable tags to all artifacts
- **Complete Documentation:** Include comprehensive descriptions and context
- **Version Everything:** Track versions for schemas, transformations, and configurations

### 2. Lineage Tracking

- **Track All Transformations:** Record every data transformation step
- **Include Context:** Store relevant metadata about each transformation
- **Regular Validation:** Verify lineage consistency regularly
- **Impact Analysis:** Use lineage for change impact assessment

### 3. Performance

- **Batch Operations:** Use batch APIs for bulk metadata operations
- **Lazy Loading:** Load metadata only when needed
- **Archive Old Data:** Archive historical metadata to maintain performance
- **Index Strategically:** Create indexes based on query patterns

### 4. Governance

- **Access Control:** Implement appropriate access controls for sensitive metadata
- **Audit Trail:** Maintain complete audit trail of metadata changes
- **Backup Strategy:** Regular backups of metadata store
- **Retention Policy:** Clear policy for metadata retention and cleanup

---

## Summary

The Metadata System provides **comprehensive tracking and governance** for ML pipelines:

✅ **Complete Visibility** - Track all artifacts from raw data to deployed models  
✅ **Data Lineage** - Full traceability of data transformations  
✅ **Reproducibility** - Capture all information needed to reproduce results  
✅ **Impact Analysis** - Understand downstream effects of changes  
✅ **Query Interface** - Flexible search and analysis capabilities  
✅ **Integration Ready** - Works with MLflow, DVC, databases, and other tools  
✅ **Performance Optimized** - Designed for production scale and performance  

The system enables data scientists and ML engineers to understand, govern, and optimize their ML workflows with full transparency and control.