# Dataset Versioning Guide

**Version:** 1.0.0  
**Date:** July 7, 2026  
**Status:** Production-Ready

---

## Overview

The Dataset Versioning system provides **immutable versioning** with **integrity checks** for all ML datasets. Every dataset version is uniquely identified, checksummed, and linked to its parent version for complete lineage tracking.

---

## Key Concepts

### 1. Immutable Versions

- **Never Overwrite:** Once a dataset version is created, it cannot be modified
- **Unique IDs:** Each version has a unique identifier: `YYYYMMDD_HHMMSS_uuid`
- **Integrity Checks:** SHA256 checksums verify data integrity
- **Lineage:** Parent-child relationships track data transformations

### 2. Version Lifecycle

```
[Raw Dataset] ──transform──▶ [Version 1] ──process──▶ [Version 2] ──split──▶ [Version 3]
      │                           │                        │                     │
      └─ creditcard_raw           └─ creditcard_cleaned     └─ creditcard_features └─ creditcard_train
```

### 3. Storage Structure

```
data/
└── processed/
    └── {dataset_name}/
        ├── 20240706_120000_abc123.parquet    # Version 1
        ├── 20240706_150000_def456.parquet    # Version 2  
        ├── 20240707_090000_ghi789.parquet    # Version 3
        └── latest.parquet -> 20240707_090000_ghi789.parquet
```

---

## Creating Dataset Versions

### Basic Usage

```python
from ml.data.versioning.dataset_version import DatasetVersion
import pandas as pd
from pathlib import Path

# Load your processed DataFrame
df = pd.read_csv("data/interim/creditcard_cleaned.csv")

# Create version
version = DatasetVersion(
    dataset_name="creditcard_processed",
    schema_version="v1.2.0",
    preprocessing_version="v1.1.0",
    source="creditcard_raw",
    parent_version_id="20240706_120000_abc123"  # Optional: link to parent
)

# Save immutably
output_path = version.save_dataframe(
    df=df,
    output_dir=Path("data/processed")
)

print(f"Saved version: {version.version_id}")
print(f"File path: {output_path}")
print(f"Checksum: {version.checksum}")
```

### Version Information

```python
# Access version details
print(f"Version ID: {version.version_id}")
print(f"Created: {version.created_at}")
print(f"Schema: {version.schema_version}")
print(f"Preprocessing: {version.preprocessing_version}")
print(f"Source: {version.source}")
print(f"Parent: {version.parent_version_id}")
print(f"Checksum: {version.checksum}")
```

### Advanced Configuration

```python
version = DatasetVersion(
    dataset_name="creditcard_features_engineered",
    schema_version="v2.0.0",
    preprocessing_version="v1.5.0", 
    source="creditcard_processed",
    parent_version_id="20240707_090000_ghi789",
    tags=["features", "engineered", "production"],
    metadata={
        "feature_count": 47,
        "transformation_pipeline": "v1.5.0",
        "quality_checks_passed": True
    }
)
```

---

## Version Registry

### Using the Registry

```python
from ml.data.versioning.dataset_version import DatasetVersionRegistry

# Initialize registry
registry = DatasetVersionRegistry(data_root=Path("data"))

# Get latest version
latest = registry.get_latest_version("creditcard_processed")
print(f"Latest version: {latest.version_id}")

# List all versions
all_versions = registry.list_versions("creditcard_processed")
for v in all_versions:
    print(f"Version: {v.version_id}, Created: {v.created_at}")

# Get specific version
specific = registry.get_version("creditcard_processed", "20240707_090000_ghi789")
```

### Version Queries

```python
# Search by date range
recent_versions = registry.get_versions_in_range(
    dataset_name="creditcard_processed",
    start_date=datetime(2024, 7, 1),
    end_date=datetime(2024, 7, 7)
)

# Search by tags
tagged_versions = registry.search_by_tags(
    dataset_name="creditcard_processed", 
    tags=["production", "validated"]
)

# Search by parent
children = registry.get_child_versions("20240707_090000_ghi789")
```

---

## Lineage Tracking

### Parent-Child Relationships

```python
# Create child version with lineage
parent_version = registry.get_latest_version("creditcard_cleaned")

child_version = DatasetVersion(
    dataset_name="creditcard_features",
    schema_version="v2.0.0",
    preprocessing_version="v1.0.0",
    source="creditcard_cleaned",
    parent_version_id=parent_version.version_id  # Link to parent
)
```

### Lineage Queries

```python
# Get full lineage chain
lineage_chain = registry.get_lineage_chain("creditcard_train_20240707_120000")

# Example result:
# [
#   "creditcard_raw_20240706_080000",
#   "creditcard_cleaned_20240706_120000", 
#   "creditcard_features_20240707_090000",
#   "creditcard_train_20240707_120000"
# ]

# Get immediate parent and children
parent = registry.get_parent_version("creditcard_features_20240707_090000")
children = registry.get_child_versions("creditcard_features_20240707_090000")
```

### Lineage Visualization

```python
# Export lineage as graph
graph_data = registry.export_lineage_graph(
    dataset_name="creditcard_processed",
    format="networkx"  # or "graphviz", "json"
)

# Visualize with matplotlib/networkx
import networkx as nx
import matplotlib.pyplot as plt

G = nx.DiGraph(graph_data)
nx.draw(G, with_labels=True, node_color='lightblue')
plt.savefig("lineage_graph.png")
```

---

## Integrity & Validation

### Checksum Verification

```python
# Verify file integrity
is_valid = version.verify_checksum()
if not is_valid:
    print("WARNING: File integrity check failed!")
    
# Manual verification
from ml.utils.file_manager import compute_file_hash, verify_file_hash

actual_checksum = compute_file_hash(version.get_file_path())
matches = verify_file_hash(version.get_file_path(), version.checksum)
```

### Schema Validation

```python
# Validate against expected schema
schema_validator = SchemaValidator(
    required_columns=["transaction_id", "amount", "is_fraud"],
    column_types={"amount": "float64", "is_fraud": "bool"}
)

df = version.load_dataframe()
validation_results = schema_validator.validate(df)

if not all(check.passed for check in validation_results):
    print("Schema validation failed!")
```

### Version Consistency

```python
# Check for version conflicts
conflicts = registry.detect_version_conflicts("creditcard_processed")

# Validate version sequence
sequence_valid = registry.validate_version_sequence("creditcard_processed")

# Check for orphaned versions
orphaned = registry.find_orphaned_versions()
```

---

## Best Practices

### 1. Naming Conventions

```python
# Good naming conventions
dataset_names = [
    "creditcard_raw",           # Raw data
    "creditcard_cleaned",       # After cleaning
    "creditcard_validated",     # After validation
    "creditcard_features",      # After feature engineering
    "creditcard_train",         # Training split
    "creditcard_val",           # Validation split
    "creditcard_test"           # Test split
]

# Use consistent prefixes by domain
fraud_datasets = ["fraud_raw", "fraud_processed", "fraud_features"]
ieee_datasets = ["ieee_raw", "ieee_processed", "ieee_features"]
```

### 2. Version Metadata

```python
# Include rich metadata
version = DatasetVersion(
    dataset_name="creditcard_features_v2",
    schema_version="v2.0.0",
    preprocessing_version="v1.5.0",
    source="creditcard_cleaned_v1",
    parent_version_id="20240707_090000_ghi789",
    tags=["features", "production", "validated"],
    metadata={
        "feature_engineering_pipeline": "v1.5.0",
        "feature_count": 47,
        "categorical_features": 8,
        "numerical_features": 39,
        "target_encoding_version": "v1.2.0",
        "scaling_method": "standard",
        "imputation_strategy": "median",
        "outlier_detection": "isolation_forest",
        "quality_score": 0.98,
        "data_drift_score": 0.02
    }
)
```

### 3. Error Handling

```python
try:
    output_path = version.save_dataframe(df, output_dir)
except FileExistsError:
    print(f"Version {version.version_id} already exists!")
    # Handle appropriately - maybe load existing version
    existing_version = registry.get_version(dataset_name, version.version_id)
    
except PermissionError:
    print("Permission denied - check file permissions")
    
except ValueError as e:
    print(f"Invalid data: {e}")
```

### 4. Performance Optimization

```python
# Use appropriate file formats
if df.shape[0] > 100000:
    # Large datasets - use Parquet
    output_path = version.save_dataframe(df, output_dir, format="parquet")
else:
    # Small datasets - CSV is fine
    output_path = version.save_dataframe(df, output_dir, format="csv")

# Compress when possible
output_path = version.save_dataframe(
    df, 
    output_dir, 
    format="parquet",
    compression="snappy"  # or "gzip", "brotli"
)
```

---

## Integration with ML Pipeline

### Pipeline Stage Integration

```python
from ml.pipeline.stage import PipelineStage

class DataProcessingStage(PipelineStage):
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Load input dataset version
        input_version_id = inputs["dataset_version_id"]
        registry = DatasetVersionRegistry(Path("data"))
        input_version = registry.get_version_by_id(input_version_id)
        
        df = input_version.load_dataframe()
        
        # Process data
        processed_df = self.process_data(df)
        
        # Create new version
        output_version = DatasetVersion(
            dataset_name=f"{input_version.dataset_name}_processed",
            schema_version="v1.0.0",
            preprocessing_version="v1.0.0",
            source=input_version.dataset_name,
            parent_version_id=input_version.version_id
        )
        
        # Save processed version
        output_path = output_version.save_dataframe(
            processed_df, 
            Path("data/processed")
        )
        
        return {
            "output_dataset_version_id": output_version.version_id,
            "output_path": str(output_path)
        }
```

### Metadata Integration

```python
from ml.utils.metadata import MetadataManager

# Automatically update metadata when creating versions
def create_versioned_dataset(df, dataset_name, **version_kwargs):
    # Create version
    version = DatasetVersion(dataset_name=dataset_name, **version_kwargs)
    output_path = version.save_dataframe(df, Path("data/processed"))
    
    # Update metadata
    metadata_manager = MetadataManager(Path("data/metadata"))
    dataset_metadata = DatasetMetadata(
        dataset_name=version.dataset_name,
        version_id=version.version_id,
        created_at=version.created_at,
        source=version.source,
        file_path=str(output_path),
        file_size_bytes=output_path.stat().st_size,
        checksum=version.checksum,
        schema_version=version.schema_version,
        preprocessing_version=version.preprocessing_version,
        row_count=len(df),
        column_count=len(df.columns),
        # ... other metadata fields
    )
    
    metadata_manager.save_dataset_metadata(dataset_metadata)
    
    # Update lineage
    if version.parent_version_id:
        metadata_manager.add_lineage_edge(
            version.parent_version_id,
            version.version_id,
            "data_processing"
        )
    
    return version, output_path
```

---

## Migration & Maintenance

### Version Cleanup

```python
# Clean up old versions (keep latest N)
registry.cleanup_old_versions(
    dataset_name="creditcard_processed",
    keep_latest=5,  # Keep 5 most recent versions
    dry_run=True    # Preview what would be deleted
)

# Clean up by age
registry.cleanup_by_age(
    dataset_name="creditcard_processed", 
    older_than_days=30,
    keep_minimum=3  # Always keep at least 3 versions
)
```

### Schema Migration

```python
# Migrate to new schema version
def migrate_schema_v1_to_v2(old_version: DatasetVersion):
    # Load old data
    df = old_version.load_dataframe()
    
    # Apply schema changes
    df = apply_schema_migration_v1_to_v2(df)
    
    # Create new version
    new_version = DatasetVersion(
        dataset_name=old_version.dataset_name,
        schema_version="v2.0.0",  # Increment version
        preprocessing_version=old_version.preprocessing_version,
        source=old_version.source,
        parent_version_id=old_version.version_id
    )
    
    return new_version.save_dataframe(df, Path("data/processed"))
```

### Backup & Recovery

```python
# Export version registry for backup
registry.export_registry(Path("backups/version_registry_20240707.json"))

# Import registry from backup
registry.import_registry(Path("backups/version_registry_20240707.json"))

# Verify all versions after recovery
validation_results = registry.validate_all_versions()
for dataset_name, results in validation_results.items():
    if not results["valid"]:
        print(f"Issues with {dataset_name}: {results['errors']}")
```

---

## Monitoring & Alerting

### Version Health Checks

```python
# Check version health
health_status = registry.health_check()

# Example output:
# {
#   "total_datasets": 15,
#   "total_versions": 45,  
#   "corrupted_files": 0,
#   "missing_files": 0,
#   "checksum_mismatches": 0,
#   "orphaned_versions": 1,
#   "disk_usage_gb": 2.3
# }
```

### Automated Monitoring

```python
# Set up monitoring alerts
def monitor_version_health():
    health = registry.health_check()
    
    if health["corrupted_files"] > 0:
        send_alert("Corrupted dataset files detected!")
    
    if health["disk_usage_gb"] > 50:
        send_alert("High disk usage for dataset versions!")
    
    if health["orphaned_versions"] > 10:
        send_alert("Many orphaned dataset versions found!")

# Run monitoring check
monitor_version_health()
```

---

## Summary

The Dataset Versioning system provides **enterprise-grade data management**:

✅ **Immutable** - Versions never change once created  
✅ **Traceable** - Complete lineage from raw data to final models  
✅ **Verifiable** - Cryptographic checksums ensure data integrity  
✅ **Queryable** - Rich metadata and search capabilities  
✅ **Scalable** - Efficient storage and retrieval for large datasets  
✅ **Maintainable** - Cleanup, migration, and monitoring tools  

This foundation enables confident data management for ML pipelines with full auditability and governance.