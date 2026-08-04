# Best Model Test Results

**Status:** TEMPLATE - TO BE COMPLETED  
**Trial Number:** [TO BE FILLED]  
**Evaluation Date:** [TO BE FILLED]

---

## Model Identification

**Selected Model:**
- Trial: [TO BE FILLED]
- Selection Criterion: Highest Validation PR-AUC
- Validation PR-AUC: [TO BE FILLED]
- Training Time: [TO BE FILLED]
- Best Iteration: [TO BE FILLED]

---

## Hyperparameters

| Parameter | Value |
|-----------|-------|
| learning_rate | [TO BE FILLED] |
| max_depth | [TO BE FILLED] |
| min_child_weight | [TO BE FILLED] |
| gamma | [TO BE FILLED] |
| subsample | [TO BE FILLED] |
| colsample_bytree | [TO BE FILLED] |
| reg_alpha | [TO BE FILLED] |
| reg_lambda | [TO BE FILLED] |
| max_delta_step | [TO BE FILLED] |
| n_estimators | [TO BE FILLED] |

---

## Test Set Performance

### Primary Metrics

| Metric | Value |
|--------|-------|
| ROC-AUC | [TO BE FILLED] |
| PR-AUC | [TO BE FILLED] |
| MCC | [TO BE FILLED] |

### Classification Metrics

| Metric | Value |
|--------|-------|
| Precision | [TO BE FILLED] |
| Recall | [TO BE FILLED] |
| F1 Score | [TO BE FILLED] |
| Accuracy | [TO BE FILLED] |
| Balanced Accuracy | [TO BE FILLED] |

### Confusion Matrix

```
                 Predicted
                Legit  Fraud
Actual  Legit   [TN]   [FP]
        Fraud   [FN]   [TP]
```

---

## Visualizations

- ROC Curve: `artifacts/test_evaluation/test_roc_curve.png`
- Precision-Recall Curve: `artifacts/test_evaluation/test_pr_curve.png`
- Calibration Curve: `artifacts/test_evaluation/test_calibration_curve.png`

---

## Probability Statistics

[TO BE FILLED - Statistics about predicted probabilities]

---

## Model Artifacts

- Model: `artifacts/experiments/experiment_[XXX]/model.json`
- Test Results: `artifacts/test_evaluation/test_results.json`
- Predictions: `artifacts/test_evaluation/test_predictions.npy`
- Probabilities: `artifacts/test_evaluation/test_probabilities.npy`

---

**Generated:** [TO BE FILLED]
