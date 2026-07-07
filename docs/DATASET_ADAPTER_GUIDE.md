# Dataset Adapter Guide

## Overview

The Dataset Adapter Layer is the core component of ML Phase 1.2, providing a standardized interface for ingesting different fraud detection datasets. This layer ensures that all datasets are transformed into a consistent schema, enabling downstream ML components to work seamlessly with any supported dataset.

## Architecture

### Design Principles

1. **Single Responsibility**: Each adapter handles one dataset type
2. **Standardized Output**: All adapters produce identical downstream schemas
3. **Foundation Integration**: Full integration with ML Phase 1.1 infrastructure
4. **Extensibility**: Easy to add new dataset adapters
5. **Data Quality**: Comprehensive validation and quality checks

### Core Components

```
ml/data/adapters/
├── base.py              # Abstract base class
├── creditcard_adapter.py # Kaggle Credit Card dataset
├── ieee_cis_adapter.py   # IEEE-CIS competition dataset
└── __init__.py

ml/data/pipeline_stages.py  # Pipeline integration stages
```

## Base Adapter Interface

All dataset adapters inherit from `DatasetAdapter` and implement:

### Required Methods

```python
class DatasetAdapter(ABC):
    @abstractmethod
    def _get_dataset_type(self) -> DatasetType:
        """Return the dataset type enum"""
        
    @abstractmethod
    def load_raw_data(self) -> pd.DataFrame:
        """Load raw data from source files"""
        
    @abstractmethod
    def map_to_standard_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map dataset-specific columns to standard schema"""
        
    @abstractmethod
    def get_schema_mapping(self) -> Dict[str, str]:
        """Return mapping from standard schema to raw columns"""
```

### Provided Methods

The base class provides common functionality:

- `load()`: Main entry point that orchestrates the loading process
- `validate()`: Dataset validation using foundation validators
- `normalize()`: Data cleaning and normalization
- `transform()`: Feature engineering and transformations
- `export()`: Export in multiple formats (Parquet, CSV, Feather)

## Standard Schema

All adapters must produce datasets with this standardized schema:

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `transaction_id` | string | Unique transaction identifier |
| `timestamp` | datetime | Transaction timestamp |
| `amount` | float64 | Transaction amount |
| `is_fraud` | bool | Fraud label (target variable) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `customer_id` | string | Customer identifier |
| `merchant_id` | string | Merchant identifier |
| `product_code` | string | Product/service code |

### Dataset-Specific Features

Adapters preserve dataset-specific features with standardized naming:
- PCA features: `pca_feature_01`, `pca_feature_02`, etc.
- Count features: `count_feature_1`, `count_feature_2`, etc.
- Time delta features: `timedelta_feature_1`, etc.
- Vesta features: `vesta_feature_001`, etc.
- Identity features: `identity_id_01`, etc.

## Supported Datasets

### 1. Kaggle Credit Card Fraud Detection

**Source**: [Kaggle Credit Card Fraud Detection](https://www.kaggle.com/mlg-ulb/creditcardfraud)

**Characteristics**:
- 284,807 transactions over 2 days
- 492 fraudulent transactions (0.172%)
- Features V1-V28 are PCA transformed
- Anonymous due to confidentiality issues

**Adapter**: `CreditCardAdapter`

**Schema Mapping**:
```python
{
    'amount': 'Amount',
    'is_fraud': 'Class',
    'time_elapsed': 'Time',
    'pca_feature_01': 'V1',
    # ... V1-V28 mapped to pca_feature_01-28
}
```

### 2. IEEE-CIS Fraud Detection

**Source**: [IEEE-CIS Fraud Detection](https://www.kaggle.com/c/ieee-fraud-detection)

**Characteristics**:
- 590,540 transactions in train set
- Rich feature set with identity and transaction data
- Real-world e-commerce transactions
- Multiple feature types (C, D, M, V features)

**Adapter**: `IEEECISAdapter`

**Schema Mapping**:
```python
{
    'transaction_id': 'TransactionID',
    'amount': 'TransactionAmt', 
    'is_fraud': 'isFraud',
    'product_code': 'ProductCD',
    'count_feature_1': 'C1',
    'timedelta_feature_1': 'D1',
    # ... comprehensive feature mapping
}
```

## Usage Examples

### Basic Adapter Usage

```python
from ml.data.adapters import CreditCardAdapter

# Initialize adapter
adapter = CreditCardAdapter("path/to/creditcard/data")

# Load and standardize dataset
standardized_df = adapter.load()

# Dataset is now in standard schema
print(standardized_df.columns)
# ['transaction_id', 'timestamp', 'amount', 'is_fraud', ...]
```

### Pipeline Integration

```python
from ml.data.pipeline_stages import DatasetLoadingStage

# Auto-detect and load dataset
loading_stage = DatasetLoadingStage(dataset_type="auto")
result = loading_stage.execute({"raw_data_path": "path/to/data"})

dataset = result["dataset"]
adapter = result["adapter"] 
metadata = result["dataset_metadata"]
```

### Complete Pipeline

```python
from ml.data.pipeline_stages import (
    DatasetLoadingStage, DatasetValidationStage, 
    DatasetVersioningStage, DatasetNormalizationStage,
    DatasetTransformationStage, MetadataGenerationStage
)

# Stage 1: Loading
loading_stage = DatasetLoadingStage(dataset_type="creditcard")
outputs = loading_stage.execute({"raw_data_path": "data/raw/creditcard"})

# Stage 2: Validation
validation_stage = DatasetValidationStage()
outputs = validation_stage.execute(outputs)

# Stage 3: Versioning
versioning_stage = DatasetVersioningStage()
outputs = versioning_stage.execute(outputs)

# Stage 4: Normalization
normalization_stage = DatasetNormalizationStage()
outputs = normalization_stage.execute(outputs)

# Stage 5: Transformation
transformation_stage = DatasetTransformationStage()
outputs = transformation_stage.execute(outputs)

# Stage 6: Metadata Generation
metadata_stage = MetadataGenerationStage()
final_outputs = metadata_stage.execute(outputs)

# Access final processed dataset
final_dataset = final_outputs["transformed_dataset"]
```

## Pipeline Stages

The adapter layer integrates with six pipeline stages:

### 1. DatasetLoadingStage
- Auto-detects dataset type
- Creates appropriate adapter
- Loads and standardizes data
- Generates initial metadata

### 2. DatasetValidationStage
- Runs comprehensive validation checks
- Uses foundation validation framework
- Generates validation reports
- Updates metadata with validation status

### 3. DatasetVersioningStage
- Creates immutable dataset versions
- Integrates with foundation versioning system
- Tracks data lineage
- Enables reproducibility

### 4. DatasetNormalizationStage
- Applies data cleaning
- Handles missing values and outliers
- Uses adapter-specific normalization logic
- Maintains data quality

### 5. DatasetTransformationStage
- Performs feature engineering
- Adds derived features
- Uses adapter-specific transformations
- Prepares data for ML pipelines

### 6. MetadataGenerationStage
- Generates comprehensive metadata
- Creates quality and validation reports
- Produces schema and statistics files
- Integrates with foundation reporting

## Validation and Quality

### Validation Framework Integration

Adapters use the foundation validation framework with:

**Standard Validators**:
- `SchemaValidator`: Ensures required columns and types
- `MissingValueValidator`: Checks missing value rates
- `DuplicateValidator`: Detects duplicate records
- `ValueRangeValidator`: Validates value ranges
- `CategoricalConsistencyValidator`: Checks categorical consistency

**Dataset-Specific Validation**:
- CreditCard: Amount range validation, PCA feature checks
- IEEE-CIS: Transaction ID uniqueness, feature cardinality

### Quality Metrics

Generated quality metrics include:
- Missing value analysis
- Duplicate detection
- Outlier identification
- Distribution analysis
- Correlation analysis
- Data drift detection (future)

## Metadata Generation

### Generated Files

Each processed dataset produces:

**Core Metadata**:
- `metadata.json`: Dataset metadata and statistics
- `schema.json`: Complete schema information
- `statistics.json`: Comprehensive statistics

**Quality Reports**:
- `quality_report.html`: Interactive quality dashboard
- `validation_report.html`: Validation results
- `metadata_report.html`: Metadata summary

**Feature Documentation**:
- `feature_dictionary.json`: Feature definitions and mappings

### Metadata Schema

```json
{
  "dataset_name": "creditcard_final",
  "dataset_type": "CREDITCARD",
  "version": "v1.0.0",
  "stage": "FEATURED",
  "num_records": 284807,
  "num_fraud": 492,
  "num_legitimate": 284315,
  "fraud_rate": 0.001727,
  "validation_passed": true,
  "created_at": "2024-07-07T12:00:00Z",
  "schema_version": "v2.0.0",
  "processing_version": "v1.2.0"
}
```

## Export Formats

Processed datasets can be exported in multiple formats:

### Supported Formats
- **Parquet** (recommended): Efficient columnar format
- **CSV**: Human-readable, interoperable
- **Feather**: Fast binary format
- **Arrow**: In-memory columnar format

### Export Example

```python
# Export in different formats
parquet_path = adapter.export(dataset, "output/", format="parquet")
csv_path = adapter.export(dataset, "output/", format="csv")
feather_path = adapter.export(dataset, "output/", format="feather")
```

## Testing

### Comprehensive Test Suite

The adapter layer includes extensive tests:

**Unit Tests**:
- Adapter functionality
- Schema mapping accuracy
- Data type consistency
- Error handling

**Integration Tests**:
- Pipeline stage integration
- Foundation system integration
- End-to-end workflows

**Compatibility Tests**:
- Cross-adapter schema compatibility
- Data type compatibility
- Pipeline interoperability

### Running Tests

```bash
# Run all adapter tests
python run_adapter_tests.py

# Run specific test categories
python -m pytest tests/ml/data/test_adapters.py -v
python -m pytest tests/ml/data/test_pipeline_stages.py -v
```

## Adding New Adapters

### Steps to Add a New Dataset Adapter

1. **Create Adapter Class**:
```python
class NewDatasetAdapter(DatasetAdapter):
    def _get_dataset_type(self) -> DatasetType:
        return DatasetType.NEW_DATASET
    
    def load_raw_data(self) -> pd.DataFrame:
        # Load raw dataset
        pass
    
    def map_to_standard_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        # Map to standard schema
        pass
    
    def get_schema_mapping(self) -> Dict[str, str]:
        # Return schema mapping
        pass
```

2. **Add Dataset Type**:
```python
# In ml/validation/schemas.py
class DatasetType(str, Enum):
    CREDITCARD = "creditcard"
    IEEE_CIS = "ieee_cis"
    NEW_DATASET = "new_dataset"  # Add new type
```

3. **Update Pipeline Stages**:
```python
# In ml/data/pipeline_stages.py
def _create_adapter(self, dataset_type: str, raw_data_path: Path) -> DatasetAdapter:
    if dataset_type == "new_dataset":
        return NewDatasetAdapter(raw_data_path)
    # ... existing adapters
```

4. **Add Tests**:
- Unit tests for adapter functionality
- Integration tests for pipeline compatibility
- Schema compatibility tests

5. **Update Documentation**:
- Add dataset description to this guide
- Document schema mapping
- Add usage examples

### Best Practices

**Schema Mapping**:
- Preserve original feature names in mapping
- Use consistent naming patterns
- Document any transformations

**Data Quality**:
- Implement comprehensive validation
- Handle edge cases gracefully
- Provide informative error messages

**Performance**:
- Optimize for large datasets
- Use efficient data types
- Minimize memory usage

**Testing**:
- Test with realistic data sizes
- Include error condition testing
- Validate schema compatibility

## Troubleshooting

### Common Issues

**Import Errors**:
```python
# Ensure proper imports
from ml.data.adapters import CreditCardAdapter, IEEECISAdapter
from ml.validation.schemas import DatasetType
```

**Schema Validation Failures**:
- Check required columns are present
- Verify data types match expectations
- Ensure timestamp columns are datetime format

**Memory Issues**:
- Use chunked processing for large datasets
- Optimize data types (e.g., int8 for binary flags)
- Clear intermediate DataFrames

**File Path Issues**:
- Use absolute paths for reliability
- Check file exists before processing
- Handle permission errors gracefully

### Debugging Tips

**Enable Detailed Logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Inspect Data at Each Stage**:
```python
# After loading
print(f"Raw data: {len(raw_df)} rows, {len(raw_df.columns)} columns")

# After schema mapping
print(f"Standardized: {list(standardized_df.columns)}")

# Check data types
print(standardized_df.dtypes)
```

**Validate Schema Mapping**:
```python
mapping = adapter.get_schema_mapping()
for standard, raw in mapping.items():
    if raw and raw in raw_df.columns:
        print(f"{standard} ← {raw}: {raw_df[raw].dtype}")
```

## Performance Considerations

### Memory Optimization

**Data Types**:
- Use `int8` for binary flags
- Use `category` dtype for categorical data
- Use `float32` instead of `float64` when precision allows

**Processing**:
- Process data in chunks for large datasets
- Use vectorized operations
- Avoid loops over DataFrame rows

**Storage**:
- Use Parquet for efficient storage
- Apply compression (snappy, gzip)
- Store processed data for reuse

### Scalability

**Large Datasets**:
- Implement chunked processing
- Use Dask for out-of-core processing
- Consider distributed processing frameworks

**Multiple Datasets**:
- Parallelize adapter processing
- Use pipeline orchestration
- Cache intermediate results

## Integration with Foundation

The Dataset Adapter Layer fully integrates with ML Phase 1.1 foundation:

**Logging**: Structured JSON logging with correlation IDs
**Metadata**: Comprehensive metadata management and lineage
**Versioning**: Immutable dataset versioning with checksums
**Validation**: Foundation validation framework integration
**Configuration**: Typed configuration management
**Testing**: Foundation testing infrastructure
**Reproducibility**: Full reproducibility with seed management
**Reports**: HTML/Markdown report generation

This integration ensures consistency, reliability, and maintainability across the entire ML platform.

## Future Extensions

### Planned Enhancements

**Additional Datasets**:
- PaySim mobile money fraud dataset
- Synthetic fraud datasets
- Custom enterprise datasets

**Advanced Features**:
- Real-time data streaming adapters
- Automated schema evolution
- Data drift detection and adaptation
- Federated learning support

**Performance Optimizations**:
- GPU-accelerated processing
- Distributed dataset loading
- Advanced caching strategies

The Dataset Adapter Layer provides a solid foundation for these future enhancements while maintaining backward compatibility and consistent interfaces.