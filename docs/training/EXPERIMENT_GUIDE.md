# Experiment Tracking Guide

This guide covers comprehensive experiment tracking for fraud detection model training, including MLflow integration and local tracking capabilities.

## Table of Contents

1. [Overview](#overview)
2. [Experiment Tracking Backends](#experiment-tracking-backends)
3. [MLflow Setup and Configuration](#mlflow-setup-and-configuration)
4. [Local Experiment Tracking](#local-experiment-tracking)
5. [Experiment Management](#experiment-management)
6. [Best Practices](#best-practices)
7. [Advanced Features](#advanced-features)

## Overview

Experiment tracking is essential for managing machine learning experiments, comparing model performance, and ensuring reproducibility. The fraud detection training pipeline supports two tracking backends:

- **MLflow**: Industry-standard ML lifecycle management
- **Local Tracker**: Lightweight JSON-based tracking for development

## Experiment Tracking Backends

### MLflow Tracker

MLflow provides comprehensive experiment tracking with:
- Web UI for experiment visualization
- Model registry integration
- REST API for programmatic access
- Integration with popular ML frameworks
- Artifact storage and management

### Local Tracker

Local tracker provides:
- JSON-based storage for simplicity
- No external dependencies
- Fast iteration during development
- Easy inspection of experiment data

## MLflow Setup and Configuration

### Installation

```bash
pip install mlflow
```

### Starting MLflow Server

#### Option 1: Local SQLite Backend

```bash
# Start server with SQLite backend
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./artifacts
```

#### Option 2: Remote Database Backend

```bash
# Start server with PostgreSQL backend
mlflow server \
    --backend-store-uri postgresql://user:password@localhost/mlflow \
    --default-artifact-root s3://my-bucket/artifacts
```

#### Option 3: Docker Deployment

```yaml
# docker-compose.yml
version: '3'
services:
  mlflow:
    image: python:3.9
    command: >
      bash -c "pip install mlflow psycopg2-binary boto3 &&
               mlflow server --host 0.0.0.0 --port 5000 
               --backend-store-uri postgresql://user:pass@db:5432/mlflow
               --default-artifact-root s3://bucket/artifacts"
    ports:
      - "5000:5000"
    environment:
      - AWS_ACCESS_KEY_ID=your_access_key
      - AWS_SECRET_ACCESS_KEY=your_secret_key
    depends_on:
      - db
      
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: mlflow
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Configuration

Configure MLflow tracking in your training pipeline:

```yaml
# Pipeline configuration
experiment_tracker_type: "mlflow"
tracking_uri: "http://localhost:5000"
experiment_name: "fraud_detection_experiments"
```

Or via command line:

```bash
python scripts/train_models.py \
    --tracker mlflow \
    --tracking-uri http://localhost:5000 \
    --experiment-name fraud_detection_v1
```

### Environment Variables

```bash
export MLFLOW_TRACKING_URI=http://localhost:5000
export MLFLOW_EXPERIMENT_NAME=fraud_detection
export AWS_ACCESS_KEY_ID=your_access_key  # For S3 artifact storage
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

## Local Experiment Tracking

### Configuration

```yaml
experiment_tracker_type: "local"
experiment_name: "fraud_detection_local"
```

### Storage Structure

```
experiments/
├── experiments.json         # Experiment metadata
└── runs/
    ├── run_123/
    │   ├── run.json        # Run metadata and metrics
    │   └── artifacts/      # Run artifacts
    │       ├── model.pkl
    │       ├── plots/
    │       └── reports/
    └── run_456/
        ├── run.json
        └── artifacts/
```

### Local Tracker API

```python
from ml.training.tracking import LocalTracker

# Initialize tracker
tracker = LocalTracker("fraud_detection", tracking_dir="experiments")

# Start run
run_id = tracker.start_run("xgboost_baseline")

# Log parameters
tracker.log_params(run_id, {
    "n_estimators": 100,
    "max_depth": 6,
    "learning_rate": 0.1
})

# Log metrics
tracker.log_metrics(run_id, {
    "train_accuracy": 0.95,
    "val_accuracy": 0.93,
    "test_roc_auc": 0.89
})

# Log artifacts
tracker.log_artifact(run_id, "model.pkl")
tracker.log_artifact(run_id, "confusion_matrix.png")

# Set tags
tracker.set_tags(run_id, {
    "model_type": "xgboost",
    "version": "1.0.0"
})

# End run
tracker.end_run(run_id)

# Query runs
runs = tracker.list_runs()
for run in runs:
    print(f"Run {run.run_id}: {run.metrics}")
```

## Experiment Management

### Organizing Experiments

#### By Model Type

```python
# Separate experiments for each model type
xgb_config = PipelineConfig(
    experiment_name="xgboost_experiments",
    trainer_configs=[XGBoostConfig(...)]
)

if_config = PipelineConfig(
    experiment_name="isolation_forest_experiments", 
    trainer_configs=[IsolationForestConfig(...)]
)
```

#### By Dataset Version

```python
# Different experiments for dataset versions
config_v1 = PipelineConfig(
    experiment_name="fraud_detection_dataset_v1",
    dataset_path="data/fraud_v1.csv"
)

config_v2 = PipelineConfig(
    experiment_name="fraud_detection_dataset_v2",
    dataset_path="data/fraud_v2.csv"
)
```

#### By Feature Set

```python
# Experiments with different feature sets
baseline_config = PipelineConfig(
    experiment_name="baseline_features",
    trainer_configs=[TrainingConfig(feature_columns=baseline_features)]
)

enhanced_config = PipelineConfig(
    experiment_name="enhanced_features",
    trainer_configs=[TrainingConfig(feature_columns=enhanced_features)]
)
```

### Experiment Comparison

#### MLflow UI Comparison

1. Navigate to MLflow UI (http://localhost:5000)
2. Select experiment from dropdown
3. Compare runs side-by-side
4. Sort by metrics (ROC-AUC, F1-Score, etc.)
5. Filter runs by tags or parameters

#### Programmatic Comparison

```python
import mlflow
import pandas as pd

# Search experiments
experiment = mlflow.get_experiment_by_name("fraud_detection")
runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])

# Compare key metrics
comparison = runs[['params.model_name', 'metrics.test_roc_auc', 'metrics.test_f1_score']]
comparison = comparison.sort_values('metrics.test_roc_auc', ascending=False)
print(comparison.head())

# Best run by ROC-AUC
best_run = runs.loc[runs['metrics.test_roc_auc'].idxmax()]
print(f"Best run: {best_run['run_id']} with ROC-AUC: {best_run['metrics.test_roc_auc']}")
```

### Hyperparameter Sweeps

#### Grid Search Example

```python
from ml.training.pipeline import ExperimentRunner
from itertools import product

# Define parameter grid
learning_rates = [0.01, 0.1, 0.3]
max_depths = [3, 6, 9]
n_estimators = [50, 100, 200]

runner = ExperimentRunner(base_config)

# Add experiments for each combination
for lr, depth, n_est in product(learning_rates, max_depths, n_estimators):
    config = XGBoostConfig(
        model_name=f"xgb_lr{lr}_depth{depth}_nest{n_est}",
        learning_rate=lr,
        max_depth=depth,
        n_estimators=n_est
    )
    
    experiment_name = f"grid_search_lr{lr}_depth{depth}_nest{n_est}"
    runner.add_experiment(experiment_name, [config])

# Run all experiments
results = runner.run_all_experiments(data)
```

#### Random Search Example

```python
import numpy as np

# Random parameter sampling
np.random.seed(42)
n_trials = 20

for trial in range(n_trials):
    lr = np.random.uniform(0.01, 0.3)
    depth = np.random.randint(3, 10)
    n_est = np.random.choice([50, 100, 150, 200])
    
    config = XGBoostConfig(
        model_name=f"xgb_random_trial_{trial}",
        learning_rate=lr,
        max_depth=depth,
        n_estimators=n_est
    )
    
    runner.add_experiment(f"random_search_trial_{trial}", [config])
```

## Best Practices

### 1. Experiment Naming

Use descriptive, consistent naming conventions:

```python
# Good: Descriptive and versioned
experiment_name = "xgboost_fraud_detection_v2.1_enhanced_features"

# Bad: Generic and unclear
experiment_name = "test_experiment_1"
```

### 2. Parameter Logging

Log all relevant parameters:

```python
# Model hyperparameters
tracker.log_params(run_id, {
    "n_estimators": 100,
    "max_depth": 6,
    "learning_rate": 0.1,
    "subsample": 0.8
})

# Data parameters
tracker.log_params(run_id, {
    "dataset_version": "v2.1",
    "feature_count": len(feature_columns),
    "train_samples": len(X_train),
    "test_size": 0.2
})

# Training parameters
tracker.log_params(run_id, {
    "cv_folds": 5,
    "early_stopping": True,
    "random_seed": 42
})
```

### 3. Comprehensive Metrics

Track metrics at different levels:

```python
# Training metrics
tracker.log_metrics(run_id, {
    "train_accuracy": train_acc,
    "train_roc_auc": train_auc,
    "train_loss": train_loss
})

# Validation metrics
tracker.log_metrics(run_id, {
    "val_accuracy": val_acc,
    "val_roc_auc": val_auc,
    "val_loss": val_loss
})

# Test metrics
tracker.log_metrics(run_id, {
    "test_accuracy": test_acc,
    "test_roc_auc": test_auc,
    "test_precision": test_prec,
    "test_recall": test_recall,
    "test_f1": test_f1
})

# Cross-validation metrics
tracker.log_metrics(run_id, {
    "cv_roc_auc_mean": cv_scores.mean(),
    "cv_roc_auc_std": cv_scores.std()
})

# Business metrics
tracker.log_metrics(run_id, {
    "false_positive_rate": fpr,
    "false_negative_rate": fnr,
    "cost_savings": estimated_savings
})
```

### 4. Artifact Management

Organize artifacts systematically:

```python
# Model artifacts
tracker.log_artifact(run_id, "model.pkl", "models/")
tracker.log_artifact(run_id, "feature_importance.json", "models/")

# Evaluation artifacts
tracker.log_artifact(run_id, "roc_curve.png", "evaluation/")
tracker.log_artifact(run_id, "confusion_matrix.png", "evaluation/")
tracker.log_artifact(run_id, "evaluation_report.json", "evaluation/")

# Configuration artifacts
tracker.log_artifact(run_id, "config.yaml", "config/")
tracker.log_artifact(run_id, "feature_list.txt", "config/")
```

### 5. Tagging Strategy

Use tags for filtering and organization:

```python
tracker.set_tags(run_id, {
    "model_type": "xgboost",
    "version": "1.0.0",
    "dataset": "fraud_v2", 
    "purpose": "baseline",
    "team": "ml_team",
    "environment": "development"
})
```

### 6. Reproducibility

Ensure experiments are reproducible:

```python
# Log environment information
tracker.log_params(run_id, {
    "python_version": sys.version,
    "xgboost_version": xgboost.__version__,
    "pandas_version": pd.__version__,
    "numpy_version": np.__version__
})

# Log git information
try:
    import subprocess
    git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    tracker.set_tag(run_id, "git_commit", git_commit)
except:
    pass

# Log random seeds
tracker.log_params(run_id, {
    "random_seed": 42,
    "numpy_seed": 42
})
```

## Advanced Features

### Custom Metrics

Track domain-specific metrics:

```python
def calculate_business_metrics(y_true, y_pred, y_proba, threshold=0.5):
    """Calculate business-specific metrics."""
    
    # Convert probabilities to predictions
    y_pred_thresh = (y_proba >= threshold).astype(int)
    
    # Calculate costs (example values)
    fp_cost = 10  # Cost of false positive
    fn_cost = 100  # Cost of false negative
    tp_reward = 50  # Reward for true positive
    
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred_thresh).ravel()
    
    total_cost = fp * fp_cost + fn * fn_cost - tp * tp_reward
    cost_per_transaction = total_cost / len(y_true)
    
    return {
        "total_cost": total_cost,
        "cost_per_transaction": cost_per_transaction,
        "false_positive_cost": fp * fp_cost,
        "false_negative_cost": fn * fn_cost,
        "true_positive_reward": tp * tp_reward
    }

# Log business metrics
business_metrics = calculate_business_metrics(y_true, y_pred, y_proba)
tracker.log_metrics(run_id, business_metrics)
```

### Model Comparison Dashboard

Create custom comparison dashboards:

```python
import plotly.graph_objects as go
import plotly.express as px

def create_comparison_dashboard(runs_df):
    """Create interactive comparison dashboard."""
    
    # ROC-AUC comparison
    fig_roc = px.bar(
        runs_df, 
        x='params.model_name', 
        y='metrics.test_roc_auc',
        title='Model ROC-AUC Comparison'
    )
    
    # Training time vs performance
    fig_scatter = px.scatter(
        runs_df,
        x='metrics.training_time',
        y='metrics.test_roc_auc',
        color='params.model_name',
        title='Training Time vs Performance'
    )
    
    # Save as HTML
    fig_roc.write_html("model_comparison_roc.html")
    fig_scatter.write_html("training_time_vs_performance.html")
    
    return fig_roc, fig_scatter

# Generate dashboard
runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
create_comparison_dashboard(runs)
```

### Automated Experiment Analysis

```python
def analyze_experiments(experiment_name):
    """Automatically analyze experiment results."""
    
    experiment = mlflow.get_experiment_by_name(experiment_name)
    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    
    # Best performing runs
    best_runs = runs.nlargest(5, 'metrics.test_roc_auc')
    
    # Parameter importance analysis
    param_cols = [col for col in runs.columns if col.startswith('params.')]
    metric_col = 'metrics.test_roc_auc'
    
    correlations = {}
    for param_col in param_cols:
        # Convert to numeric if possible
        try:
            param_values = pd.to_numeric(runs[param_col], errors='coerce')
            correlation = param_values.corr(runs[metric_col])
            correlations[param_col] = correlation
        except:
            continue
    
    # Sort by absolute correlation
    correlations = dict(sorted(correlations.items(), 
                              key=lambda x: abs(x[1]), 
                              reverse=True))
    
    print("Best Runs:")
    print(best_runs[['run_id', 'metrics.test_roc_auc', 'params.model_name']].head())
    
    print("\nParameter Importance (correlation with ROC-AUC):")
    for param, corr in correlations.items():
        print(f"{param}: {corr:.3f}")
    
    return best_runs, correlations

# Analyze experiments
best_runs, param_importance = analyze_experiments("fraud_detection")
```

### Integration with Hyperparameter Optimization

```python
import optuna

def objective(trial):
    """Optuna objective function."""
    
    # Suggest parameters
    learning_rate = trial.suggest_float('learning_rate', 0.01, 0.3, log=True)
    max_depth = trial.suggest_int('max_depth', 3, 9)
    n_estimators = trial.suggest_int('n_estimators', 50, 200)
    
    # Create configuration
    config = XGBoostConfig(
        model_name=f"optuna_trial_{trial.number}",
        learning_rate=learning_rate,
        max_depth=max_depth,
        n_estimators=n_estimators
    )
    
    # Train model
    trainer = XGBoostTrainer(config, tracker)
    result = trainer.train(data)
    
    # Log trial to MLflow
    with mlflow.start_run(nested=True):
        mlflow.log_params(trial.params)
        mlflow.log_metric("roc_auc", result.test_metrics['roc_auc'])
    
    return result.test_metrics['roc_auc']

# Run optimization
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=50)

print(f"Best parameters: {study.best_params}")
print(f"Best ROC-AUC: {study.best_value}")
```

This experiment tracking guide provides comprehensive coverage of managing ML experiments for fraud detection models, from basic setup to advanced optimization workflows.