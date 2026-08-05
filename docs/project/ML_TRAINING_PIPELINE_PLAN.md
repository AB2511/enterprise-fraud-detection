# ML Training Pipeline - Implementation Plan (REVISED)

**Date**: August 1, 2026  
**Priority**: PHASE 1 - Train Real Models First  
**Status**: Ready for Implementation

---

## 🎯 Objective

Implement a complete, production-quality ML training pipeline that produces real, trained fraud detection models using authentic fraud data.

**No dummy models. No placeholders. Real training only.**

---

## 📊 Dataset Selection

### Primary Choice: IEEE-CIS Fraud Detection Dataset
**Source**: Kaggle IEEE-CIS Fraud Detection Competition  
**Size**: 590,540 transactions  
**Fraud Rate**: ~3.5% (realistic imbalance)  
**Features**: 
- Transaction features (amount, type, card info)
- Identity features (device, network, email domain)
- Temporal features (timestamps, day of week)
- Categorical features (product codes, card types)

**Why This Dataset**:
- ✅ Real credit card fraud transactions
- ✅ Production-scale (590K rows)
- ✅ Realistic class imbalance
- ✅ Rich feature set for ML
- ✅ Well-documented and maintained
- ✅ Publicly available (Kaggle)

### Fallback: Credit Card Fraud Detection (Kaggle)
**Source**: Kaggle Credit Card Fraud Detection  
**Size**: 284,807 transactions  
**Fraud Rate**: 0.172%  
**If primary unavailable**

---

## 🏗️ Training Pipeline Architecture

### Pipeline Stages

```
1. Data Acquisition
   ↓
2. Data Validation & Quality Checks
   ↓
3. Preprocessing & Cleaning
   ↓
4. Feature Engineering
   ↓
5. Train/Test Split (stratified)
   ↓
6. XGBoost Training
   ↓
7. Isolation Forest Training
   ↓
8. Model Evaluation
   ↓
9. SHAP Explainer Training
   ↓
10. Artifact Serialization
```

---

## 📝 Implementation Plan

### File 1: `ml/training/data_loader.py` (NEW)
**Purpose**: Download and load IEEE-CIS dataset  
**Functions**:
- `download_dataset()` - Download from Kaggle API
- `load_train_data()` - Load training CSV
- `load_test_data()` - Load test CSV
- `validate_schema()` - Check columns and types

**Output**: Raw pandas DataFrames

---

### File 2: `ml/training/preprocessor.py` (NEW)
**Purpose**: Clean and preprocess raw data  
**Key Operations**:
- Handle missing values (imputation strategies)
- Remove duplicates
- Fix data types
- Encode categorical variables (target encoding, one-hot)
- Scale numerical features (StandardScaler)
- Handle outliers

**Output**: 
- Preprocessed DataFrame
- `artifacts/scaler.pkl` (fitted StandardScaler)
- `artifacts/encoders.pkl` (fitted encoders)
- `artifacts/preprocessing_config.json` (metadata)

---

### File 3: `ml/training/feature_engineer.py` (NEW)
**Purpose**: Engineer fraud-specific features  
**Features to Create**:
- **Temporal**: hour_of_day, day_of_week, is_weekend
- **Transaction**: amount_zscore, log_amount, is_high_value
- **Velocity**: transactions_per_hour, amount_per_day (if possible)
- **Categorical**: email_domain_risk, card_type_frequency
- **Aggregations**: mean_amount_by_card, std_amount_by_merchant

**Output**:
- Enhanced DataFrame with engineered features
- `artifacts/feature_names.json` (list of all features)
- `artifacts/feature_metadata.json` (types, ranges, descriptions)

---

### File 4: `ml/training/xgboost_trainer.py` (NEW)
**Purpose**: Train XGBoost fraud classifier  
**Configuration**:
```python
params = {
    'objective': 'binary:logistic',
    'eval_metric': 'auc',
    'max_depth': 6,
    'learning_rate': 0.1,
    'n_estimators': 200,
    'scale_pos_weight': 28,  # Handle imbalance
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': 42
}
```

**Training Process**:
- Stratified train/test split (80/20)
- Handle class imbalance (scale_pos_weight)
- Early stopping (patience=10)
- Cross-validation (5-fold stratified)
- Track training metrics

**Output**:
- `artifacts/models/xgboost_model.json` (trained model)
- `artifacts/metrics/xgboost_metrics.json` (performance metrics)
- Training curves plot

---

### File 5: `ml/training/isolation_forest_trainer.py` (NEW)
**Purpose**: Train Isolation Forest for anomaly detection  
**Configuration**:
```python
params = {
    'n_estimators': 100,
    'max_samples': 256,
    'contamination': 0.035,  # Expected fraud rate
    'random_state': 42,
    'n_jobs': -1
}
```

**Training Process**:
- Train on full dataset (unsupervised)
- Calibrate contamination parameter
- Validate on labeled test set
- Calculate anomaly scores

**Output**:
- `artifacts/models/isolation_forest.pkl` (trained model)
- `artifacts/metrics/isolation_forest_metrics.json`

---

### File 6: `ml/training/evaluator.py` (NEW)
**Purpose**: Comprehensive model evaluation  
**Metrics**:
- **Classification**: Precision, Recall, F1, AUC-ROC, AUC-PR
- **Confusion Matrix**: TP, FP, TN, FN
- **Business Metrics**: Cost analysis (FP cost vs FN cost)
- **Threshold Analysis**: Find optimal decision threshold

**Evaluation Reports**:
- Classification report
- ROC curve
- Precision-Recall curve
- Confusion matrix heatmap
- Feature importance charts

**Output**:
- `artifacts/evaluation/classification_report.json`
- `artifacts/evaluation/confusion_matrix.png`
- `artifacts/evaluation/roc_curve.png`
- `artifacts/evaluation/pr_curve.png`
- `artifacts/evaluation/feature_importance.png`

---

### File 7: `ml/training/explainer_trainer.py` (NEW)
**Purpose**: Train SHAP explainer for interpretability  
**Process**:
- Create TreeExplainer for XGBoost
- Calculate baseline SHAP values (on sample data)
- Validate explanation quality
- Serialize explainer

**Output**:
- `artifacts/models/shap_explainer.pkl` (trained explainer)
- `artifacts/shap_baseline_values.npy` (expected values)

---

### File 8: `ml/training/pipeline.py` (NEW)
**Purpose**: Orchestrate entire training pipeline  
**Class**: `FraudDetectionTrainingPipeline`  
**Methods**:
- `run()` - Execute full pipeline
- `run_preprocessing_only()` - Just preprocessing
- `run_training_only()` - Training with existing preprocessed data
- `validate_pipeline()` - Validate each stage

**Features**:
- Logging at each stage
- Error handling and rollback
- Reproducibility (set all seeds)
- Save pipeline metadata

**Output**:
- `artifacts/pipeline_metadata.json` (versions, dates, configs)
- `artifacts/training_log.txt` (detailed logs)

---

### File 9: `scripts/train_models.py` (NEW)
**Purpose**: Entry point for training  
**Usage**:
```bash
python scripts/train_models.py \
  --dataset-path ./data/ieee-fraud/ \
  --output-dir ./artifacts \
  --experiment-name fraud-detection-v1
```

**Features**:
- CLI arguments for configuration
- Progress bars for long operations
- Summary statistics at end
- Email notification option (optional)

---

### File 10: `ml/training/model_registry.py` (NEW)
**Purpose**: Register trained models with metadata  
**Functionality**:
- Save model with version
- Record training date, dataset size, metrics
- Tag models (development, staging, production)
- Model comparison utilities

**Output**:
- `artifacts/model_registry.json` (model catalog)

---

## 📂 Output Artifacts Structure

```
artifacts/
├── models/
│   ├── xgboost_model.json          # Trained XGBoost
│   ├── isolation_forest.pkl        # Trained Isolation Forest
│   └── shap_explainer.pkl          # Trained SHAP explainer
├── preprocessing/
│   ├── scaler.pkl                  # Fitted StandardScaler
│   ├── encoders.pkl                # Categorical encoders
│   └── preprocessing_config.json   # Preprocessing metadata
├── features/
│   ├── feature_names.json          # List of all features
│   └── feature_metadata.json       # Feature descriptions
├── metrics/
│   ├── xgboost_metrics.json        # XGBoost performance
│   ├── isolation_forest_metrics.json
│   └── combined_metrics.json       # Ensemble metrics
├── evaluation/
│   ├── classification_report.json
│   ├── confusion_matrix.png
│   ├── roc_curve.png
│   ├── pr_curve.png
│   └── feature_importance.png
├── shap/
│   └── baseline_values.npy         # SHAP baseline
├── pipeline_metadata.json          # Full pipeline info
├── model_registry.json             # Model catalog
└── training_log.txt                # Detailed logs
```

---

## 🔧 Dependencies to Add

### File: `requirements.txt` (MODIFY)
```
# ML Training
xgboost==2.0.3
scikit-learn==1.4.0
pandas==2.2.0
numpy==1.26.3
imbalanced-learn==0.12.0

# Explainability
shap==0.44.1

# Data Processing
pyarrow==15.0.0

# Utilities
joblib==1.3.2
matplotlib==3.8.2
seaborn==0.13.1

# Optional: Kaggle API
kaggle==1.6.6
```

---

## 🎯 Success Criteria

### Functional Requirements ✅
1. Successfully downloads IEEE-CIS fraud dataset
2. Preprocesses 590K+ transactions without errors
3. Engineers meaningful fraud features
4. Trains XGBoost with AUC > 0.85
5. Trains Isolation Forest with reasonable anomaly detection
6. Generates SHAP explainer
7. Saves all artifacts to disk
8. Produces comprehensive evaluation reports
9. Pipeline is reproducible (same seed → same results)
10. All artifacts are properly serialized

### Quality Requirements ✅
1. **Data Quality**: No NaN in final features, proper encoding
2. **Model Quality**: AUC-PR > 0.7, Recall > 0.75 at 5% FPR
3. **Code Quality**: 100% type coverage, passes ruff/black/mypy
4. **Documentation**: Each module documented
5. **Reproducibility**: Fixed random seeds, versioned artifacts

### Performance Requirements ✅
1. Training completes in < 30 minutes (on typical laptop)
2. XGBoost model < 50MB
3. Isolation Forest model < 20MB
4. SHAP explainer < 100MB

---

## 📋 Implementation Order

### Step 1: Setup (2-3 hours)
1. Add ML dependencies to requirements.txt
2. Create artifacts/ directory structure
3. Set up Kaggle API credentials
4. Download IEEE-CIS dataset

### Step 2: Data Pipeline (4-5 hours)
1. Implement data_loader.py
2. Implement preprocessor.py
3. Implement feature_engineer.py
4. Test on sample data

### Step 3: Model Training (6-8 hours)
1. Implement xgboost_trainer.py
2. Test XGBoost training on sample
3. Implement isolation_forest_trainer.py
4. Test Isolation Forest training

### Step 4: Evaluation (3-4 hours)
1. Implement evaluator.py
2. Generate all evaluation plots
3. Calculate business metrics

### Step 5: Explainability (2-3 hours)
1. Implement explainer_trainer.py
2. Train SHAP explainer
3. Validate explanations

### Step 6: Pipeline Orchestration (3-4 hours)
1. Implement pipeline.py
2. Implement model_registry.py
3. Create train_models.py script
4. End-to-end pipeline test

### Step 7: Documentation & Testing (3-4 hours)
1. Write training documentation
2. Add unit tests for preprocessing
3. Add integration test for pipeline
4. Verify reproducibility

**Total Estimate: 25-35 hours**

---

## 🔍 Verification Checklist

After training completes:

### Artifacts Generated ✅
- [ ] xgboost_model.json exists and loads
- [ ] isolation_forest.pkl exists and loads
- [ ] shap_explainer.pkl exists and loads
- [ ] scaler.pkl exists and transforms data
- [ ] feature_names.json contains all features
- [ ] All evaluation plots generated

### Model Performance ✅
- [ ] XGBoost AUC-ROC > 0.85
- [ ] XGBoost AUC-PR > 0.70
- [ ] Recall @ 5% FPR > 0.75
- [ ] Isolation Forest detects anomalies
- [ ] SHAP explanations generate correctly

### Reproducibility ✅
- [ ] Running pipeline twice produces same metrics
- [ ] All random seeds fixed
- [ ] Dependencies pinned
- [ ] Artifact versions tracked

---

## 🚫 Out of Scope (For This Phase)

❌ Hyperparameter optimization (Optuna) - use good defaults  
❌ Cross-validation grid search - single train/test split  
❌ Ensemble methods beyond XGBoost + IF  
❌ Deep learning models  
❌ Real-time retraining  
❌ A/B testing infrastructure  
❌ Drift detection  
❌ Model serving infrastructure  

These will be implemented AFTER inference layer is complete.

---

## 📊 Next Steps After Training

Once training pipeline produces real artifacts:

1. **Phase 2**: Implement inference layer using trained models
2. **Phase 3**: Build prediction API with real models
3. **Phase 4**: Integrate with existing backend
4. **Phase 5**: Deploy to production

---

## ✅ Ready for Approval

**Real dataset identified**: IEEE-CIS Fraud Detection  
**Complete training pipeline designed**  
**No dummy models**: Only real trained artifacts  
**Reproducible**: Fixed seeds, versioned data  
**Production-quality**: Proper evaluation, metrics, artifacts  

**Awaiting approval to proceed with ML training pipeline implementation.**

