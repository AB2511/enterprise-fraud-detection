# Fraud Detection Model Training Guide

This guide provides comprehensive instructions for training fraud detection models using the ML Phase 2 training pipeline.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Model Types](#model-types)
5. [Training Pipeline](#training-pipeline)
6. [Experiment Tracking](#experiment-tracking)
7. [Model Registry](#model-registry)
8. [Evaluation and Optimization](#evaluation-and-optimization)
9. [Advanced Usage](#advanced-usage)
10. [Troubleshooting](#troubleshooting)

## Overview

The fraud detection training pipeline provides a production-ready framework for training machine learning models to detect fraudulent transactions. The system supports:

- **XGBoost**: Supervised gradient boosting classifier
- **Isolation Forest**: Unsupervised anomaly detection
- **MLflow Integration**: Experiment tracking and model registry
- **Comprehensive Evaluation**: ROC curves, confusion matrices, calibration analysis
- **Threshold Optimization**: Business cost optimization, F1, recall objectives
- **Artifact Management**: Model persistence, evaluation reports, visualizations

## Quick Start

### 1. Basic Training

Train both XGBoost and Isolation Forest models with default settings:

```bash
python scripts/train_models.py --data data/fraud_dataset.csv
```

### 2. Quick Testing

For rapid iteration and testing:

```bash
python scripts/train_models.py --data data/fraud_dataset.csv --quick
```

### 3. Specific Model Training

Train only XGBoost:

```bash
python scripts/train_models.py --data data/fraud_dataset.csv --models xgboost
```

Train only Isolation Forest:

```bash
python scripts/train_models.py --data data/fraud_dataset.csv --models isolation_forest
```

### 4. Custom Configuration

Use a custom configuration file:

```bash
python scripts/train_models.py --config config/training/my_config.yaml
```

## Configuration

### Pipeline Configuration

The main pipeline configuration file (`config/training/pipeline_config.yaml`) controls all aspects of training:

```yaml
# Pipeline identification
pipeline_name: "fraud_detection_training"
pipeline_version: "1.0.0"

# Data source
dataset_path: "data/processed/fraud_detection_dataset.csv"

# Experiment tracking
experiment_tracker_type: "auto"  # "mlflow", "local", "auto"
experiment_name: "fraud_detection_experiments"

# Model registry
registry_path: "models/registry"

# Evaluation and optimization
generate_evaluation_reports: true
optimize_thresholds: true

# Reproducibility
random_seed: 42
```

### Model-Specific Configuration

#### XGBoost Configuration

```yaml
# XGBoost parameters
n_estimators: 100
max_depth: 6
learning_rate: 0.1
subsample: 0.8
colsample_bytree: 0.8
reg_alpha: 0.0
reg_lambda: 1.0

# Early stopping
early_stopping: true
early_stopping_rounds: 10
```

#### Isolation Forest Configuration

```yaml
# Isolation Forest parameters
n_estimators: 100
max_samples: "auto"
contamination: "auto"
max_features: 1.0
bootstrap: false

# Feature scaling
scale_features: true
scaler_type: "standard"

# Score calibration
calibrate_scores: true
calibration_method: "sigmoid"
```

## Model Types

### XGBoost (Supervised Learning)

XGBoost is a gradient boosting framework optimized for supervised learning tasks. For fraud detection:

**Advantages:**
- High predictive accuracy
- Handles imbalanced datasets well
- Built-in feature importance
- Robust to outliers
- Supports early stopping

**Use Cases:**
- Primary fraud detection model
- When labeled fraud data is available
- Real-time scoring applications

**Key Parameters:**
- `n_estimators`: Number of boosting rounds
- `max_depth`: Maximum tree depth (controls overfitting)
- `learning_rate`: Step size shrinkage
- `subsample`: Fraction of samples used for training
- `scale_pos_weight`: Handles class imbalance

### Isolation Forest (Unsupervised Learning)

Isolation Forest is an unsupervised anomaly detection algorithm that isolates anomalies by random selection of features and split values.

**Advantages:**
- No labeled data required
- Efficient for large datasets
- Good at detecting new fraud patterns
- Low memory requirements

**Use Cases:**
- Anomaly detection in new domains
- Complementary to supervised models
- When fraud labels are scarce or unreliable

**Key Parameters:**
- `contamination`: Expected proportion of anomalies
- `n_estimators`: Number of isolation trees
- `max_samples`: Number of samples per tree
- `max_features`: Number of features per tree

## Training Pipeline

The training pipeline orchestrates the complete model training workflow:

### 1. Data Loading

```python
# From file
pipeline.load_data_from_file("data/fraud_dataset.csv")

# From feature store
pipeline.load_data_from_feature_store("fraud_features_v1")
```

### 2. Data Preprocessing

- **Feature Selection**: Automatic or manual feature selection
- **Data Splitting**: Train/validation/test splits with stratification
- **Scaling**: Optional feature scaling for Isolation Forest

### 3. Model Training

```python
from ml.training.pipeline import TrainingPipeline
from ml.training.trainers import XGBoostConfig

# Configure trainer
config = XGBoostConfig(
    model_name="fraud_detector_v1",
    n_estimators=100,
    max_depth=6
)

# Create and run pipeline
pipeline = TrainingPipeline(pipeline_config)
results = pipeline.run()
```

### 4. Cross-Validation

Automatic k-fold cross-validation with stratification:

```yaml
use_cross_validation: true
cv_folds: 5
cv_scoring: "roc_auc"
```

### 5. Model Evaluation

Comprehensive evaluation metrics:
- **Classification Metrics**: Accuracy, Precision, Recall, F1-Score
- **Ranking Metrics**: ROC-AUC, PR-AUC
- **Calibration**: Brier Score, Calibration Error
- **Confusion Matrix**: True/False Positives/Negatives

### 6. Visualization

Automatic generation of evaluation plots:
- ROC Curves
- Precision-Recall Curves
- Confusion Matrices
- Calibration Curves
- Feature Importance Plots

## Experiment Tracking

### MLflow Integration

MLflow provides comprehensive experiment tracking:

```bash
# Start MLflow server
mlflow server --backend-store-uri sqlite:///mlflow.db

# Train with MLflow tracking
python scripts/train_models.py \
    --tracker mlflow \
    --tracking-uri http://localhost:5000 \
    --experiment-name fraud_detection_v1
```

### Local Tracking

For development and testing without MLflow:

```bash
python scripts/train_models.py --tracker local
```

### Tracked Information

- **Parameters**: All hyperparameters and configuration
- **Metrics**: Training, validation, and test metrics
- **Artifacts**: Model files, plots, evaluation reports
- **Metadata**: Git commit, environment info, timestamps

## Model Registry

The model registry manages trained model versions and metadata:

### Registry Structure

```
models/registry/
├── models.json              # Model index
├── model_123/
│   ├── metadata.json        # Training metadata
│   ├── model.pkl           # Serialized model
│   ├── artifacts/          # Evaluation artifacts
│   │   ├── roc_curve.png
│   │   ├── confusion_matrix.png
│   │   └── evaluation_report.json
│   └── thresholds/         # Optimized thresholds
│       ├── business_cost.json
│       ├── f1_score.json
│       └── recall.json
```

### Model Lifecycle

1. **Training**: Model is trained and evaluated
2. **Registration**: Model is registered with metadata
3. **Staging**: Model can be promoted to staging
4. **Production**: Model can be deployed to production
5. **Archived**: Old models can be archived

### Registry API

```python
from ml.training.registry import ModelRegistry

registry = ModelRegistry("models/registry")

# List models
models = registry.list_models()

# Get model
model_info = registry.get_model("model_123")

# Load model
model = registry.load_model("model_123")

# Update model status
registry.update_model_status("model_123", "production")
```

## Evaluation and Optimization

### Threshold Optimization

The pipeline automatically optimizes decision thresholds for different objectives:

#### Business Cost Optimization

```yaml
threshold_optimization_configs:
  - objective: "business_cost"
    cost_matrix:
      false_positive_cost: 10      # Cost of flagging legitimate transaction
      false_negative_cost: 100     # Cost of missing fraud
      true_positive_reward: 50     # Reward for catching fraud
      true_negative_reward: 0      # Reward for correct normal classification
```

#### F1-Score Optimization

```yaml
- objective: "f1_score"
  save_plots: true
```

#### Recall Optimization

```yaml
- objective: "recall"
  min_precision: 0.1  # Minimum acceptable precision
  save_plots: true
```

### Evaluation Metrics

#### Classification Metrics

- **Accuracy**: Overall correctness
- **Precision**: True positives / (True positives + False positives)
- **Recall**: True positives / (True positives + False negatives)
- **F1-Score**: Harmonic mean of precision and recall
- **Matthews Correlation Coefficient**: Balanced measure for imbalanced datasets

#### Ranking Metrics

- **ROC-AUC**: Area under ROC curve
- **PR-AUC**: Area under Precision-Recall curve
- **Average Precision**: Weighted mean of precisions at each threshold

#### Calibration Metrics

- **Brier Score**: Mean squared difference between predicted probabilities and outcomes
- **Calibration Error**: Difference between predicted and observed frequencies

## Advanced Usage

### Custom Trainers

Create custom trainers by extending the base trainer:

```python
from ml.training.base import BaseTrainer, TrainingConfig

class CustomTrainer(BaseTrainer):
    def _create_model(self):
        # Implement model creation
        pass
    
    def _fit_model(self, X, y):
        # Implement model training
        pass
    
    def _predict(self, model, X):
        # Implement prediction
        pass
```

### Hyperparameter Sweeps

Use ExperimentRunner for hyperparameter optimization:

```python
from ml.training.pipeline import ExperimentRunner
from ml.training.trainers import XGBoostConfig

runner = ExperimentRunner(base_config)

# Add experiments with different hyperparameters
for lr in [0.01, 0.1, 0.3]:
    for depth in [3, 6, 9]:
        config = XGBoostConfig(
            model_name=f"xgb_lr{lr}_depth{depth}",
            learning_rate=lr,
            max_depth=depth
        )
        runner.add_experiment(f"lr{lr}_depth{depth}", [config])

# Run all experiments
results = runner.run_all_experiments(data)
```

### Feature Store Integration

Load features from the feature store:

```python
config = PipelineConfig(
    feature_store_path="data/feature_store",
    feature_set_name="fraud_features_v1",
    feature_set_version="latest"
)
```

### Custom Evaluation Metrics

Add custom evaluation metrics:

```python
from ml.training.evaluation import ModelEvaluator

class CustomEvaluator(ModelEvaluator):
    def compute_custom_metrics(self, y_true, y_pred, y_proba):
        # Implement custom metrics
        return {"custom_metric": value}
```

## Troubleshooting

### Common Issues

#### 1. Memory Issues

**Problem**: Out of memory during training
**Solutions**:
- Reduce `max_samples` for Isolation Forest
- Use smaller `n_estimators`
- Enable data sampling
- Increase system memory

#### 2. Convergence Issues

**Problem**: XGBoost not converging
**Solutions**:
- Reduce `learning_rate`
- Increase `n_estimators`
- Adjust `reg_alpha` and `reg_lambda`
- Check for data quality issues

#### 3. Poor Performance

**Problem**: Low model performance
**Solutions**:
- Check feature quality and selection
- Adjust class imbalance handling
- Tune hyperparameters
- Ensure proper data preprocessing

#### 4. MLflow Connection Issues

**Problem**: Cannot connect to MLflow server
**Solutions**:
- Verify MLflow server is running
- Check `tracking_uri` configuration
- Use local tracking as fallback
- Check network connectivity

### Debugging

Enable verbose logging for detailed debugging:

```bash
python scripts/train_models.py --verbose --log-level DEBUG
```

### Performance Optimization

#### Training Speed

- Use `n_jobs=-1` for parallel processing
- Reduce cross-validation folds for faster iteration
- Use GPU acceleration if available (XGBoost)
- Enable early stopping

#### Memory Usage

- Use `max_samples="auto"` for Isolation Forest
- Process data in chunks for large datasets
- Use feature selection to reduce dimensionality
- Clear intermediate variables

### Validation

Validate training setup before full training:

```bash
# Quick validation run
python scripts/train_models.py --quick --models xgboost

# Dry run (configuration validation only)
python scripts/train_models.py --dry-run --config my_config.yaml
```

## Best Practices

### 1. Data Preparation

- Ensure high-quality, clean training data
- Handle missing values appropriately
- Validate feature distributions
- Check for data leakage

### 2. Model Selection

- Start with XGBoost for supervised learning
- Use Isolation Forest for anomaly detection
- Consider ensemble approaches
- Validate model assumptions

### 3. Hyperparameter Tuning

- Use cross-validation for parameter selection
- Start with default parameters
- Tune systematically (one parameter at a time)
- Use automated hyperparameter optimization tools

### 4. Evaluation

- Use appropriate metrics for imbalanced datasets
- Validate on out-of-time data
- Consider business metrics alongside technical metrics
- Test model fairness and bias

### 5. Production Deployment

- Monitor model performance over time
- Implement model versioning and rollback
- Set up alerting for model drift
- Plan for model retraining

## Next Steps

After completing model training:

1. **Model Deployment**: Deploy models to production environment
2. **Monitoring**: Set up model monitoring and alerting
3. **A/B Testing**: Compare model performance in production
4. **Continuous Learning**: Implement online learning for model updates
5. **Feedback Loop**: Incorporate production feedback for model improvement