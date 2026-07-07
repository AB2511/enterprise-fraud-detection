# Pipeline Framework Documentation

**Version:** 1.0.0  
**Date:** July 7, 2026  
**Status:** Production-Ready

---

## Overview

The Pipeline Framework provides a **reusable orchestration system** for ML workflows. It supports **stage dependencies**, **execution ordering**, **retry logic**, **checkpointing**, and **failure recovery**. All pipeline stages inherit from a common base class and integrate with the foundation's logging, metadata, and validation systems.

---

## Core Components

### 1. PipelineStage (`ml/pipeline/stage.py`)

**Purpose:** Abstract base class for all pipeline stages

**Key Features:**
- Dependency management
- Retry logic with exponential backoff
- Input/output validation
- Setup and cleanup hooks
- Status tracking
- Execution timing

```python
from ml.pipeline.stage import PipelineStage, StageStatus

class DataLoadingStage(PipelineStage):
    def __init__(self):
        super().__init__(
            name="data_loading",
            dependencies=[],  # No dependencies
            max_retries=2,
            retry_delay_seconds=1.0,
            checkpoint=True,
            description="Load and validate raw dataset"
        )
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute stage logic"""
        dataset_path = inputs["dataset_path"]
        
        # Load data
        df = pd.read_csv(dataset_path)
        
        # Return outputs for next stages
        return {
            "dataset": df,
            "row_count": len(df),
            "column_count": len(df.columns)
        }
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate required inputs"""
        if "dataset_path" not in inputs:
            raise ValueError("Missing required input: dataset_path")
    
    def validate_outputs(self, outputs: Dict[str, Any]) -> None:
        """Validate stage outputs"""
        if "dataset" not in outputs:
            raise ValueError("Stage must return 'dataset'")
```

### 2. Pipeline (`ml/pipeline/pipeline.py`)

**Purpose:** Container for pipeline stages with execution orchestration

**Key Features:**
- Stage registration and dependency resolution
- Execution ordering (topological sort)
- Parallel execution where possible
- Progress tracking
- Result aggregation

```python
from ml.pipeline.pipeline import Pipeline
from ml.pipeline.stage import PipelineStage

# Create pipeline
pipeline = Pipeline(
    name="fraud_detection_pipeline",
    description="End-to-end fraud detection ML pipeline"
)

# Add stages
pipeline.add_stage(DataLoadingStage())
pipeline.add_stage(ValidationStage(dependencies=["data_loading"]))
pipeline.add_stage(FeatureEngineeringStage(dependencies=["validation"]))
pipeline.add_stage(ModelTrainingStage(dependencies=["feature_engineering"]))

# Execute
results = pipeline.execute(inputs={"dataset_path": "data/raw/fraud.csv"})
```

### 3. PipelineExecutor (`ml/pipeline/executor.py`)

**Purpose:** Handles pipeline execution with retry, recovery, and monitoring

**Key Features:**
- Dependency resolution
- Retry logic
- Failure handling
- Checkpointing
- Resume from failures
- Execution timing

```python
from ml.pipeline.executor import PipelineExecutor

executor = PipelineExecutor(
    enable_checkpoints=True,
    checkpoint_dir=Path("checkpoints"),
    max_parallel_stages=4
)

# Execute with monitoring
result = executor.execute_pipeline(
    pipeline=pipeline,
    inputs=inputs,
    resume_from_checkpoint=True
)
```

### 4. StageRegistry (`ml/pipeline/registry.py`)

**Purpose:** Central registry for reusable pipeline stages

**Key Features:**
- Stage discovery and registration
- Version management
- Plugin architecture
- Configuration templates

```python
from ml.pipeline.registry import StageRegistry

# Register stages
registry = StageRegistry()
registry.register("data_loading", DataLoadingStage)
registry.register("validation", ValidationStage)
registry.register("feature_engineering", FeatureEngineeringStage)

# Create pipeline from registry
pipeline = registry.create_pipeline("fraud_detection", [
    "data_loading",
    "validation", 
    "feature_engineering"
])
```

---

## Stage Lifecycle

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   PENDING   │───▶│   RUNNING   │───▶│   SUCCESS   │───▶│  COMPLETED  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                                       
       │                   ▼                                       
       │            ┌─────────────┐    ┌─────────────┐              
       │            │   FAILED    │───▶│  RETRYING   │              
       │            └─────────────┘    └─────────────┘              
       │                   │                   │                   
       │                   ▼                   │                   
       └────────────┌─────────────┐◀───────────┘                   
                    │   SKIPPED   │                                
                    └─────────────┘                                
```

### Status Transitions

1. **PENDING** → **RUNNING**
   - All dependencies completed successfully
   - Stage selected for execution

2. **RUNNING** → **SUCCESS**
   - Stage executed without errors
   - Output validation passed

3. **RUNNING** → **FAILED** 
   - Exception during execution
   - Output validation failed

4. **FAILED** → **RETRYING**
   - Retry attempts remaining
   - Retry delay elapsed

5. **RETRYING** → **RUNNING**
   - Retry attempt initiated

6. **FAILED** → **SKIPPED**
   - Max retries exceeded
   - Manual skip requested

---

## Dependency Management

### Dependency Declaration

```python
class FeatureEngineeringStage(PipelineStage):
    def __init__(self):
        super().__init__(
            name="feature_engineering",
            dependencies=["data_loading", "validation"],  # Multiple dependencies
            description="Generate features from validated dataset"
        )
```

### Dynamic Dependencies

```python
class ConditionalStage(PipelineStage):
    def __init__(self):
        super().__init__(name="conditional_stage")
    
    def can_execute(self, completed_stages: Set[str]) -> bool:
        # Custom execution logic
        if "data_quality_check" in completed_stages:
            return "high_quality_preprocessing" in completed_stages
        else:
            return "standard_preprocessing" in completed_stages
```

### Dependency Resolution

The pipeline executor uses **topological sorting** to determine execution order:

```python
# Example pipeline
stages = [
    DataLoadingStage(),                    # No dependencies
    ValidationStage(deps=["data_loading"]),
    CleaningStage(deps=["validation"]),
    FeatureStage(deps=["cleaning"]),
    SplittingStage(deps=["feature"]),
    TrainingStage(deps=["splitting"])
]

# Execution order: data_loading → validation → cleaning → feature → splitting → training
```

---

## Error Handling & Retry Logic

### Retry Configuration

```python
class UnreliableStage(PipelineStage):
    def __init__(self):
        super().__init__(
            name="unreliable_stage",
            max_retries=3,              # Retry up to 3 times
            retry_delay_seconds=2.0,    # 2 second delay between retries
        )
    
    def on_retry(self, attempt: int, error: Exception) -> None:
        """Called before each retry"""
        self.logger.warning(f"Retry {attempt}/3 for {self.name}: {error}")
        
        # Custom retry logic (e.g., cleanup, backoff adjustment)
        if isinstance(error, ConnectionError):
            self.retry_delay_seconds *= 1.5  # Exponential backoff
```

### Error Categories

```python
class ErrorCategory(Enum):
    TRANSIENT = "transient"       # Retry recommended
    PERMANENT = "permanent"       # Don't retry
    CONFIGURATION = "config"      # Fix config and retry
    DATA_QUALITY = "data"         # Data issue, may skip
```

### Failure Strategies

```python
class PipelineExecutor:
    def handle_stage_failure(
        self,
        stage: PipelineStage,
        error: Exception,
        strategy: str = "fail_fast"
    ):
        if strategy == "fail_fast":
            # Stop entire pipeline
            raise PipelineExecutionError(f"Stage {stage.name} failed: {error}")
            
        elif strategy == "skip_and_continue":
            # Mark stage as skipped, continue with independent stages
            stage.status = StageStatus.SKIPPED
            return
            
        elif strategy == "retry_with_backoff":
            # Implement exponential backoff retry
            return self._retry_stage_with_backoff(stage, error)
```

---

## Checkpointing & Recovery

### Checkpoint Configuration

```python
class CheckpointableStage(PipelineStage):
    def __init__(self):
        super().__init__(
            name="data_processing",
            checkpoint=True,  # Enable checkpointing
        )
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Heavy processing
        processed_data = self.process_data(inputs["data"])
        
        # Checkpoint saved automatically after success
        return {"processed_data": processed_data}
```

### Recovery from Checkpoints

```python
# Resume pipeline from last successful checkpoint
executor = PipelineExecutor(
    enable_checkpoints=True,
    checkpoint_dir=Path("checkpoints/fraud_detection")
)

# This will skip completed stages and resume from failure point
result = executor.execute_pipeline(
    pipeline,
    inputs=initial_inputs,
    resume_from_checkpoint=True
)
```

### Checkpoint Storage Format

```json
{
  "pipeline_name": "fraud_detection_pipeline",
  "run_id": "run_20240707_120000",
  "checkpoint_time": "2024-07-07T12:30:00Z",
  "completed_stages": ["data_loading", "validation"],
  "failed_stage": "feature_engineering",
  "stage_outputs": {
    "data_loading": {"dataset_path": "data/processed/dataset_v1.parquet"},
    "validation": {"validation_passed": true, "quality_score": 0.95}
  },
  "pipeline_config_hash": "abc123def456"
}
```

---

## Parallel Execution

### Parallel Stage Detection

The executor automatically identifies stages that can run in parallel:

```python
# These stages can run in parallel (no dependencies between them)
parallel_group_1 = [
    DataLoadingStage(name="load_transactions"),
    DataLoadingStage(name="load_users"),
    DataLoadingStage(name="load_merchants")
]

# This stage depends on all parallel stages
join_stage = [
    DataJoinStage(dependencies=["load_transactions", "load_users", "load_merchants"])
]
```

### Concurrency Control

```python
executor = PipelineExecutor(
    max_parallel_stages=4,        # Maximum concurrent stages
    resource_limits={
        "memory_gb": 16,          # Memory limit across all stages
        "cpu_cores": 8            # CPU core limit
    }
)
```

---

## Monitoring & Observability

### Stage Metrics

Each stage automatically tracks:

```python
class StageMetrics:
    execution_time_seconds: float
    memory_usage_mb: float
    cpu_usage_percent: float
    input_size_bytes: int
    output_size_bytes: int
    error_count: int
    retry_count: int
```

### Pipeline Metrics

```python
class PipelineMetrics:
    total_execution_time: timedelta
    stage_count: int
    successful_stages: int
    failed_stages: int
    skipped_stages: int
    parallel_efficiency: float  # % time saved by parallelism
```

### Integration with Logging

```python
# Automatic logging integration
logger = get_logger("ml.pipeline")

with logger.stage_context("feature_engineering"):
    result = stage.execute(inputs)
    
    # Automatically logged:
    # - Stage start/end times
    # - Input/output sizes  
    # - Success/failure status
    # - Performance metrics
```

---

## Configuration-Driven Pipelines

### Pipeline Definition (YAML)

```yaml
# config/fraud_detection_pipeline.yaml
pipeline:
  name: fraud_detection_pipeline
  description: End-to-end fraud detection ML pipeline
  
  stages:
    - name: data_loading
      class: DataLoadingStage
      config:
        source_path: data/raw/creditcard.csv
        validation_enabled: true
      dependencies: []
      
    - name: validation
      class: ValidationStage
      config:
        missing_threshold: 0.1
        duplicate_threshold: 0.05
      dependencies: [data_loading]
      
    - name: feature_engineering
      class: FeatureEngineeringStage
      config:
        feature_sets: [temporal, categorical, aggregated]
        window_size_days: 7
      dependencies: [validation]
      
    - name: model_training
      class: ModelTrainingStage  
      config:
        algorithm: xgboost
        cv_folds: 5
      dependencies: [feature_engineering]

  execution:
    max_parallel_stages: 4
    enable_checkpoints: true
    failure_strategy: fail_fast
    retry_policy:
      max_retries: 2
      delay_seconds: 1.0
```

### Pipeline Factory

```python
from ml.pipeline.factory import PipelineFactory

# Create pipeline from configuration
factory = PipelineFactory(stage_registry)
pipeline = factory.create_from_config("config/fraud_detection_pipeline.yaml")

# Execute
result = pipeline.execute(inputs={"source_path": "data/raw/fraud.csv"})
```

---

## Advanced Features

### Conditional Execution

```python
class ConditionalStage(PipelineStage):
    def should_execute(self, inputs: Dict[str, Any]) -> bool:
        """Override to add execution conditions"""
        return inputs.get("data_quality_score", 0.0) > 0.8
```

### Dynamic Stage Generation

```python
class MultiDatasetStage(PipelineStage):
    def generate_substages(self, inputs: Dict[str, Any]) -> List[PipelineStage]:
        """Generate stages dynamically based on inputs"""
        datasets = inputs["dataset_list"]
        return [
            DataProcessingStage(f"process_{dataset}", dataset) 
            for dataset in datasets
        ]
```

### Resource Management

```python
class ResourceAwareStage(PipelineStage):
    def __init__(self):
        super().__init__(
            name="heavy_computation",
            resource_requirements={
                "memory_gb": 8,
                "cpu_cores": 4,
                "gpu_memory_gb": 2
            }
        )
```

---

## Testing Pipeline Stages

### Unit Testing

```python
import pytest
from ml.testing.fixtures import create_mock_dataframe

class TestDataLoadingStage:
    def test_execute_success(self):
        stage = DataLoadingStage()
        inputs = {"dataset_path": "test_data.csv"}
        
        with patch('pandas.read_csv') as mock_read:
            mock_read.return_value = create_mock_dataframe()
            
            result = stage.execute(inputs)
            
            assert "dataset" in result
            assert result["row_count"] > 0

    def test_validate_inputs_missing_path(self):
        stage = DataLoadingStage()
        
        with pytest.raises(ValueError, match="Missing required input"):
            stage.validate_inputs({})
```

### Integration Testing

```python
class TestPipelineIntegration:
    def test_full_pipeline_execution(self, temp_directory):
        # Create test pipeline
        pipeline = Pipeline("test_pipeline")
        pipeline.add_stage(MockDataLoadingStage())
        pipeline.add_stage(MockValidationStage(dependencies=["data_loading"]))
        
        # Execute
        executor = PipelineExecutor()
        result = executor.execute_pipeline(pipeline, inputs={"test": True})
        
        assert result.status == "success"
        assert len(result.stage_results) == 2
```

---

## Best Practices

### 1. Stage Design

- **Single Responsibility:** Each stage should have one clear purpose
- **Stateless:** Stages should not maintain state between executions
- **Idempotent:** Running a stage multiple times should produce the same result
- **Testable:** Stages should be easily unit testable

### 2. Dependency Management

- **Minimize Dependencies:** Reduce coupling between stages where possible
- **Clear Interfaces:** Use well-defined input/output contracts
- **Fail Fast:** Validate dependencies early in the pipeline

### 3. Error Handling

- **Graceful Degradation:** Handle errors without crashing the entire pipeline
- **Meaningful Messages:** Provide actionable error information
- **Retry Strategy:** Only retry transient errors

### 4. Performance

- **Lazy Loading:** Load data only when needed
- **Memory Management:** Clean up large objects after use
- **Parallel Friendly:** Design stages to run independently

---

## Summary

The Pipeline Framework provides a **robust foundation** for ML workflow orchestration:

✅ **Declarative** - Define pipelines through configuration  
✅ **Scalable** - Parallel execution with resource management  
✅ **Resilient** - Retry logic and failure recovery  
✅ **Observable** - Comprehensive logging and monitoring  
✅ **Testable** - Built-in support for unit and integration testing  
✅ **Extensible** - Plugin architecture for custom stages  

The framework integrates seamlessly with the ML Foundation's logging, metadata, validation, and configuration systems to provide end-to-end pipeline management.