# Reproducibility Guide

**Version:** 1.0.0  
**Date:** July 7, 2026  
**Status:** Production-Ready

---

## Overview

The Reproducibility system ensures that **every ML pipeline run is deterministically reproducible**. It captures all sources of randomness, environment state, and configuration to enable exact reproduction of results weeks or months later.

---

## Core Components

### 1. Seed Management

**Purpose:** Control all sources of randomness in the ML pipeline

```python
from ml.utils.reproducibility import get_reproducibility_manager

# Initialize with global seed
manager = get_reproducibility_manager(seed=42)

# All random number generators are now seeded:
# - Python random module
# - NumPy random state  
# - Pandas random operations
# - Hash randomization (via PYTHONHASHSEED)
```

### 2. Environment Snapshots

**Purpose:** Capture complete environment state for reproduction

```python
# Capture current environment
snapshot = manager.capture_environment_snapshot()

# Contains:
# - Python version and executable path
# - Platform information (OS, architecture)
# - Package versions (pip freeze equivalent)
# - Environment variables
# - Git commit hash
# - System configuration
```

### 3. Configuration Hashing

**Purpose:** Detect configuration changes that affect reproducibility

```python
# Hash pipeline configuration
config_hash = manager.compute_config_hash(pipeline_config)

# Compare configurations
is_same = manager.compare_configs(config1, config2)
```

---

## Setting Up Reproducibility

### Basic Setup

```python
from ml.utils.reproducibility import get_reproducibility_manager
from ml.utils.config import PipelineConfig

# 1. Initialize reproducibility manager
manager = get_reproducibility_manager(seed=42)

# 2. Load pipeline configuration
config = PipelineConfig.load("config/pipeline.json")

# 3. Capture environment snapshot
snapshot = manager.capture_environment_snapshot()

# 4. Save reproducibility state
repro_state = {
    "seed": 42,
    "config_hash": manager.compute_config_hash(config),
    "environment_snapshot": snapshot,
    "timestamp": datetime.utcnow().isoformat() + "Z"
}

manager.save_snapshot(repro_state, Path("metadata/repro_20240707_120000.json"))
```

### Pipeline Integration

```python
from ml.pipeline.stage import PipelineStage

class ReproducibleStage(PipelineStage):
    def __init__(self, name: str, seed: int = None):
        super().__init__(name=name)
        self.seed = seed
        
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Set stage-specific seed if provided
        if self.seed is not None:
            manager = get_reproducibility_manager(seed=self.seed)
            
        # Your stage logic here
        result = self.process_data(inputs)
        
        # Capture execution state
        execution_state = {
            "stage_seed": self.seed,
            "input_checksums": self.compute_input_checksums(inputs),
            "config_hash": manager.compute_config_hash(inputs.get("config"))
        }
        
        result["reproducibility_state"] = execution_state
        return result
```

---

## Environment Snapshots

### Snapshot Contents

```json
{
  "timestamp": "2024-07-07T12:00:00.000Z",
  "python_info": {
    "version": "3.9.16",
    "executable": "/usr/local/bin/python",
    "platform": "linux-x86_64",
    "compiler": "GCC 9.4.0"
  },
  "system_info": {
    "platform": "Linux",
    "platform_version": "5.4.0-74-generic",
    "architecture": "x86_64", 
    "processor": "x86_64",
    "hostname": "ml-server-01"
  },
  "packages": {
    "pandas": "2.0.3",
    "numpy": "1.24.3",
    "scikit-learn": "1.3.0",
    "xgboost": "1.7.5"
  },
  "environment_variables": {
    "PYTHONHASHSEED": "42",
    "CUDA_VISIBLE_DEVICES": "0,1",
    "OMP_NUM_THREADS": "8"
  },
  "git_info": {
    "commit_hash": "a1b2c3d4e5f6789",
    "branch": "main", 
    "is_dirty": false,
    "remote_url": "https://github.com/company/fraud-detection.git"
  }
}
```

### Capturing Snapshots

```python
# Capture full environment
snapshot = manager.capture_environment_snapshot()

# Capture minimal snapshot (faster)
minimal_snapshot = manager.capture_environment_snapshot(
    include_all_packages=False,  # Only include specified packages
    package_whitelist=["pandas", "numpy", "scikit-learn", "xgboost"]
)

# Custom snapshot with additional info
custom_snapshot = manager.capture_environment_snapshot(
    include_system_info=True,
    include_gpu_info=True,
    include_custom_vars=["MODEL_VERSION", "TRAINING_MODE"]
)
```

---

## Seed Management

### Global Seed Configuration

```python
# Set global seed for entire pipeline
manager = get_reproducibility_manager(seed=42)

# This sets:
import random
import numpy as np
import os

random.seed(42)
np.random.seed(42) 
os.environ['PYTHONHASHSEED'] = str(42)

# Configure pandas
import pandas as pd
pd.set_option('mode.chained_assignment', None)  # Reproducible behavior
```

### Stage-Specific Seeds

```python
class DataSplittingStage(PipelineStage):
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Use derived seed for splitting
        base_seed = inputs.get("random_seed", 42)
        split_seed = base_seed + hash("data_splitting") % 10000
        
        np.random.seed(split_seed)
        
        # Perform splitting
        train_df, val_df, test_df = self.split_data(
            inputs["dataset"], 
            test_size=0.2, 
            val_size=0.2,
            random_state=split_seed
        )
        
        return {
            "train_dataset": train_df,
            "val_dataset": val_df, 
            "test_dataset": test_df,
            "split_seed": split_seed
        }
```

### Seed Derivation

```python
# Derive seeds deterministically
base_seed = 42

seeds = {
    "data_loading": manager.derive_seed(base_seed, "data_loading"),
    "preprocessing": manager.derive_seed(base_seed, "preprocessing"), 
    "feature_engineering": manager.derive_seed(base_seed, "feature_engineering"),
    "model_training": manager.derive_seed(base_seed, "model_training"),
    "evaluation": manager.derive_seed(base_seed, "evaluation")
}

# Each stage gets a different but deterministic seed
print(seeds)
# {
#   'data_loading': 42,
#   'preprocessing': 15234, 
#   'feature_engineering': 98765,
#   'model_training': 44213,
#   'evaluation': 77892
# }
```

---

## Configuration Management

### Configuration Hashing

```python
# Hash configuration for reproducibility tracking
config = PipelineConfig(
    pipeline_name="fraud_detection",
    random_seed=42,
    dataset=DatasetConfig(...)
)

config_hash = manager.compute_config_hash(config)
print(f"Configuration hash: {config_hash}")
# "a1b2c3d4e5f67890abcdef1234567890abcdef12"
```

### Configuration Comparison

```python
# Compare two configurations
config1 = PipelineConfig.load("config/pipeline_v1.json")
config2 = PipelineConfig.load("config/pipeline_v2.json")

comparison = manager.compare_configs(config1, config2)

print(comparison)
# {
#   'identical': False,
#   'hash_1': 'a1b2c3...',
#   'hash_2': 'x9y8z7...',
#   'differences': {
#     'dataset.missing_threshold': (0.1, 0.05),
#     'feature.window_size': (7, 14)
#   }
# }
```

### Configuration Versioning

```python
# Track configuration changes over time
config_history = manager.get_config_history("fraud_detection_pipeline")

for entry in config_history:
    print(f"{entry['timestamp']}: {entry['config_hash']} - {entry['description']}")

# 2024-07-01T10:00:00Z: a1b2c3... - Initial configuration
# 2024-07-03T14:30:00Z: x9y8z7... - Increased validation threshold  
# 2024-07-05T09:15:00Z: m5n6o7... - Added new features
```

---

## Reproducibility Verification

### Environment Verification

```python
# Verify current environment matches saved snapshot
saved_snapshot = manager.load_snapshot("metadata/repro_20240707_120000.json")
current_snapshot = manager.capture_environment_snapshot()

verification = manager.verify_environment(saved_snapshot, current_snapshot)

if verification['reproducible']:
    print("✅ Environment is reproducible")
else:
    print("❌ Environment differences detected:")
    for diff in verification['differences']:
        print(f"  - {diff}")
```

### Version Compatibility

```python
# Check if package versions are compatible
compatibility = manager.check_version_compatibility(
    required_packages={
        "pandas": ">=2.0.0,<3.0.0",
        "numpy": ">=1.20.0",
        "scikit-learn": ">=1.0.0"
    }
)

if not compatibility['compatible']:
    print("Package version issues:")
    for issue in compatibility['issues']:
        print(f"  - {issue}")
```

### Reproducibility Score

```python
# Calculate reproducibility confidence score
score = manager.calculate_reproducibility_score(
    environment_match=0.95,    # 95% environment match
    config_match=1.0,          # 100% config match
    seed_controlled=1.0,       # All seeds controlled
    data_versioned=1.0         # Data properly versioned
)

print(f"Reproducibility score: {score:.2%}")
# "Reproducibility score: 98.75%"
```

---

## Best Practices

### 1. Seed Strategy

```python
# Use hierarchical seeds
BASE_SEED = 42

PIPELINE_SEEDS = {
    "data_processing": BASE_SEED + 1000,
    "feature_engineering": BASE_SEED + 2000,
    "model_training": BASE_SEED + 3000,
    "evaluation": BASE_SEED + 4000
}

# Use consistent seed derivation
def get_stage_seed(base_seed: int, stage_name: str) -> int:
    """Derive deterministic seed for pipeline stage"""
    return base_seed + hash(stage_name) % 10000
```

### 2. Environment Management

```python
# Pin all package versions
requirements = """
pandas==2.0.3
numpy==1.24.3
scikit-learn==1.3.0
xgboost==1.7.5
"""

# Set environment variables consistently
os.environ.update({
    'PYTHONHASHSEED': '42',
    'CUDA_DETERMINISTIC_OPS': '1', 
    'TF_DETERMINISTIC_OPS': '1',
    'OMP_NUM_THREADS': '1'
})
```

### 3. Data Versioning Integration

```python
# Combine with dataset versioning
def create_reproducible_pipeline_run():
    # 1. Set up reproducibility
    manager = get_reproducibility_manager(seed=42)
    
    # 2. Capture environment
    env_snapshot = manager.capture_environment_snapshot()
    
    # 3. Load versioned datasets
    dataset_version = registry.get_latest_version("creditcard_processed")
    
    # 4. Create run metadata with reproducibility info
    run_metadata = PipelineRunMetadata(
        pipeline_name="fraud_detection_v1",
        run_id=f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        config_hash=manager.compute_config_hash(config),
        environment_snapshot=env_snapshot,
        input_datasets=[dataset_version.version_id],
        reproducibility_seed=42
    )
    
    return run_metadata
```

### 4. Testing Reproducibility

```python
import pytest

def test_pipeline_reproducibility():
    """Test that pipeline produces identical results with same inputs"""
    
    # Run 1
    manager1 = get_reproducibility_manager(seed=42)
    result1 = run_pipeline(config, seed=42)
    
    # Run 2  
    manager2 = get_reproducibility_manager(seed=42)
    result2 = run_pipeline(config, seed=42)
    
    # Results should be identical
    assert_results_identical(result1, result2)

def assert_results_identical(result1, result2, tolerance=1e-10):
    """Assert two pipeline results are identical"""
    
    # Compare model predictions
    np.testing.assert_allclose(
        result1['predictions'], 
        result2['predictions'], 
        atol=tolerance
    )
    
    # Compare feature importance
    np.testing.assert_allclose(
        result1['feature_importance'],
        result2['feature_importance'],
        atol=tolerance  
    )
    
    # Compare metrics
    assert result1['metrics']['accuracy'] == result2['metrics']['accuracy']
```

---

## Troubleshooting Reproducibility

### Common Issues

1. **Non-Deterministic Operations**
```python
# Problem: Random operations without seed
df_sample = df.sample(n=1000)  # ❌ Non-reproducible

# Solution: Always specify random_state
df_sample = df.sample(n=1000, random_state=42)  # ✅ Reproducible
```

2. **Hash Randomization**
```python
# Problem: Python hash randomization
hash_value = hash("feature_name")  # ❌ Changes between runs

# Solution: Use deterministic hashing
import hashlib
hash_value = int(hashlib.md5("feature_name".encode()).hexdigest()[:8], 16)
```

3. **Thread-Level Parallelism**
```python
# Problem: Non-deterministic parallel operations
from joblib import Parallel, delayed

results = Parallel(n_jobs=-1)(
    delayed(process_batch)(batch) for batch in batches
)  # ❌ Order may vary

# Solution: Control parallelism and ordering
results = Parallel(n_jobs=1)(  # Single thread
    delayed(process_batch)(batch) for batch in sorted(batches)
)  # ✅ Deterministic order
```

### Debugging Tools

```python
# Check for reproducibility issues
def diagnose_reproducibility_issues():
    issues = []
    
    # Check random seeds
    if 'PYTHONHASHSEED' not in os.environ:
        issues.append("PYTHONHASHSEED not set")
    
    # Check for non-deterministic libraries
    try:
        import tensorflow as tf
        if not tf.config.experimental.get_memory_growth():
            issues.append("TensorFlow memory growth not disabled")
    except ImportError:
        pass
    
    # Check numpy state
    if np.random.get_state()[0] != 'MT19937':
        issues.append("NumPy random state not properly initialized")
    
    return issues
```

---

## Advanced Features

### Conditional Reproducibility

```python
# Reproducible only in specific modes
class ConditionallyReproducibleStage(PipelineStage):
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        config = inputs.get("config")
        
        if config.get("reproducible_mode", False):
            # Use deterministic algorithms
            manager = get_reproducibility_manager(seed=config.random_seed)
            result = self.deterministic_process(inputs)
        else:
            # Use faster non-deterministic algorithms
            result = self.fast_process(inputs)
            
        return result
```

### Reproducibility Across Platforms

```python
# Handle platform differences
def ensure_cross_platform_reproducibility():
    """Configure for reproducibility across different platforms"""
    
    # Floating point precision
    np.seterr(all='raise')  # Raise on floating point errors
    
    # Threading
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['MKL_NUM_THREADS'] = '1'
    
    # GPU determinism (if available)
    try:
        import torch
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        pass
```

### Reproducibility Metrics

```python
# Track reproducibility over time
def track_reproducibility_metrics():
    metrics = {
        "environment_stability": calculate_env_stability(),
        "config_consistency": calculate_config_consistency(), 
        "seed_coverage": calculate_seed_coverage(),
        "verification_success_rate": calculate_verification_rate()
    }
    
    return metrics
```

---

## Summary

The Reproducibility system provides **deterministic ML pipeline execution**:

✅ **Seed Control** - All randomness sources properly seeded  
✅ **Environment Capture** - Complete environment snapshots  
✅ **Configuration Tracking** - Hash-based configuration management  
✅ **Verification Tools** - Automated reproducibility verification  
✅ **Cross-Platform** - Works across different systems and environments  
✅ **Integration Ready** - Seamlessly integrates with pipeline framework  
✅ **Debugging Support** - Tools to diagnose reproducibility issues  

This enables confident experimentation and deployment with guarantee that results can be exactly reproduced when needed.