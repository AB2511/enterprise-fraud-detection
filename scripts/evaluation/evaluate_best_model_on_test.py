"""
Milestone 1C.11 - Hold-Out Test Evaluation
Evaluate the best optimized model on the frozen test set EXACTLY ONCE.

CRITICAL SAFETY RULES:
- Only runs AFTER Milestone 1C.10 completes
- Requires minimum 50 successful trials
- Verifies baseline integrity
- Loads test set ONLY after all checks pass
- Single execution only - results are final
"""

import hashlib
import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


class PrerequisiteCheckError(Exception):
    """Raised when prerequisites are not met."""

    pass


def check_prerequisites():
    """
    Verify all prerequisites before test evaluation.
    
    Raises PrerequisiteCheckError if any requirement fails.
    """
    print("=" * 80)
    print("PREREQUISITE VERIFICATION")
    print("=" * 80)
    print()
    
    # 1. Check optimization process terminated
    print("1. Checking optimization process status...")
    # Note: In production, check for running processes
    # For now, we verify by checking artifact count
    
    # 2. Check experiment_summary.csv exists
    summary_path = Path("artifacts/experiments/experiment_summary.csv")
    if not summary_path.exists():
        raise PrerequisiteCheckError("experiment_summary.csv not found")
    print("   ✓ experiment_summary.csv found")
    
    # 3. Count successful trials
    print("2. Counting successful trials...")
    df = pd.read_csv(summary_path)
    successful = df[df['training_success'] == True]
    n_successful = len(successful)
    print(f"   Found {n_successful} successful trials")
    
    if n_successful < 50:
        raise PrerequisiteCheckError(
            f"Insufficient trials: {n_successful} < 50 required"
        )
    print(f"   ✓ Minimum 50 trials requirement met ({n_successful} trials)")
    
    # 4. Verify baseline integrity
    print("3. Verifying baseline integrity...")
    expected_hashes = {
        "baseline_xgboost.json": "d5905f4d677fb064d5048d3a60c8d17dcacfc6f672dbcbd8159bfb8644c189b7",
        "baseline_metrics.json": "ec1a0305b007a945a49dc0f801d404e38fdf784e488a2568f5598fae38a9d2ef",
        "training_metadata.json": "0f979e7e38b182005a375686eac9198b8d9f35c0dbea282c9b266e0b9146134a",
    }
    
    for filename, expected_hash in expected_hashes.items():
        filepath = Path(f"artifacts/models/{filename}")
        if not filepath.exists():
            raise PrerequisiteCheckError(f"Baseline file missing: {filename}")
        
        actual_hash = compute_sha256(filepath)
        if actual_hash.lower() != expected_hash.lower():
            raise PrerequisiteCheckError(
                f"Baseline modified: {filename}\n"
                f"Expected: {expected_hash}\n"
                f"Actual:   {actual_hash}"
            )
    print("   ✓ All baseline artifacts verified (unchanged)")
    
    print()
    print("=" * 80)
    print("ALL PREREQUISITES SATISFIED")
    print("=" * 80)
    print()


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def identify_best_trial(summary_path: Path):
    """
    Identify best trial by validation PR-AUC.
    
    Returns:
        trial_number, trial_data
    """
    print("=" * 80)
    print("IDENTIFYING BEST TRIAL")
    print("=" * 80)
    print()
    
    df = pd.read_csv(summary_path)
    successful = df[df['training_success'] == True].copy()
    
    # Find best by PR-AUC
    best_idx = successful['metric_pr_auc'].idxmax()
    best_trial = successful.loc[best_idx]
    
    trial_number = int(best_trial['trial_number'])
    
    print(f"Best Trial: {trial_number}")
    print(f"Validation PR-AUC: {best_trial['metric_pr_auc']:.6f}")
    print(f"Validation ROC-AUC: {best_trial['metric_roc_auc']:.6f}")
    print(f"Validation MCC: {best_trial['metric_mcc']:.6f}")
    print(f"Validation F1: {best_trial['metric_f1']:.6f}")
    print()
    
    return trial_number, best_trial


def load_best_model(trial_number: int):
    """Load the best model from experiment artifacts."""
    print("=" * 80)
    print("LOADING BEST MODEL")
    print("=" * 80)
    print()
    
    model_path = Path(f"artifacts/experiments/experiment_{trial_number:03d}/model.json")
    
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    print(f"Loading: {model_path}")
    model = xgb.XGBClassifier()
    model.load_model(model_path)
    print("✓ Model loaded successfully")
    print()
    
    return model


def load_test_data():
    """
    Load the hold-out test set.
    
    WARNING: This should only be called ONCE after optimization completes.
    """
    print("=" * 80)
    print("LOADING HOLD-OUT TEST SET")
    print("=" * 80)
    print()
    print("⚠️  WARNING: Loading test data - this can only be done ONCE")
    print()
    
    test_path = Path("artifacts/scaling/test_scaled.parquet")
    
    if not test_path.exists():
        raise FileNotFoundError(f"Test set not found: {test_path}")
    
    print(f"Loading: {test_path}")
    test_df = pd.read_parquet(test_path)
    print(f"✓ Loaded {len(test_df):,} test samples")
    print()
    
    return test_df


def evaluate_on_test(model, test_df, threshold=0.5):
    """Evaluate model on test set."""
    print("=" * 80)
    print("TEST SET EVALUATION")
    print("=" * 80)
    print()
    
    # Separate features and target
    TARGET = "isFraud"
    X_test = test_df.drop(columns=[TARGET])
    y_test = test_df[TARGET]
    
    print(f"Test set size: {len(X_test):,}")
    print(f"Features: {len(X_test.columns)}")
    print(f"Fraud rate: {y_test.mean()*100:.2f}%")
    print()
    
    # Generate predictions
    print("Generating predictions...")
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)
    
    # Compute metrics
    print("Computing metrics...")
    metrics = {
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "pr_auc": float(average_precision_score(y_test, y_proba)),
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "mcc": float(matthews_corrcoef(y_test, y_pred)),
    }
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    
    print()
    print("Test Set Results:")
    for metric, value in metrics.items():
        print(f"  {metric}: {value:.6f}")
    print()
    print(f"Confusion Matrix:")
    print(f"  TN: {cm[0,0]:,}  FP: {cm[0,1]:,}")
    print(f"  FN: {cm[1,0]:,}  TP: {cm[1,1]:,}")
    print()
    
    return metrics, y_proba, y_pred, cm


def generate_plots(y_test, y_proba, y_pred, output_dir: Path):
    """Generate ROC, PR, and calibration curves."""
    print("Generating plots...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ROC Curve
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, label=f'ROC (AUC={roc_auc_score(y_test, y_proba):.3f})')
    plt.plot([0, 1], [0, 1], 'k--', label='Random')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve - Test Set')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(output_dir / "test_roc_curve.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    # Precision-Recall Curve
    precision, recall, _ = precision_recall_curve(y_test, y_proba)
    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, label=f'PR (AUC={average_precision_score(y_test, y_proba):.3f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve - Test Set')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(output_dir / "test_pr_curve.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    # Calibration Curve
    fraction_of_positives, mean_predicted_value = calibration_curve(
        y_test, y_proba, n_bins=10
    )
    plt.figure(figsize=(8, 6))
    plt.plot(mean_predicted_value, fraction_of_positives, 's-', label='Model')
    plt.plot([0, 1], [0, 1], 'k--', label='Perfect Calibration')
    plt.xlabel('Mean Predicted Probability')
    plt.ylabel('Fraction of Positives')
    plt.title('Calibration Curve - Test Set')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(output_dir / "test_calibration_curve.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Plots saved to {output_dir}")


def save_results(trial_number, metrics, y_proba, y_pred, cm, output_dir: Path):
    """Save all results."""
    print()
    print("Saving results...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save metrics
    results = {
        "trial_number": trial_number,
        "evaluation_timestamp": pd.Timestamp.now().isoformat(),
        "test_metrics": metrics,
        "confusion_matrix": {
            "TN": int(cm[0, 0]),
            "FP": int(cm[0, 1]),
            "FN": int(cm[1, 0]),
            "TP": int(cm[1, 1]),
        },
    }
    
    with open(output_dir / "test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Save predictions and probabilities
    np.save(output_dir / "test_probabilities.npy", y_proba)
    np.save(output_dir / "test_predictions.npy", y_pred)
    
    print(f"✓ Results saved to {output_dir}")


def main():
    """Main execution."""
    print("=" * 80)
    print("MILESTONE 1C.11 - HOLD-OUT TEST EVALUATION")
    print("=" * 80)
    print()
    print("⚠️  CRITICAL: This evaluates the best model on the test set ONCE")
    print("⚠️  Test results are FINAL and cannot be used for further optimization")
    print()
    
    try:
        # Step 1: Check prerequisites
        check_prerequisites()
        
        # Step 2: Identify best trial
        summary_path = Path("artifacts/experiments/experiment_summary.csv")
        trial_number, best_trial = identify_best_trial(summary_path)
        
        # Step 3: Load best model
        model = load_best_model(trial_number)
        
        # Step 4: Load test data (ONLY AFTER all checks pass)
        test_df = load_test_data()
        
        # Step 5: Evaluate on test set
        metrics, y_proba, y_pred, cm = evaluate_on_test(model, test_df)
        
        # Step 6: Generate plots
        output_dir = Path("artifacts/test_evaluation")
        generate_plots(test_df['isFraud'], y_proba, y_pred, output_dir)
        
        # Step 7: Save results
        save_results(trial_number, metrics, y_proba, y_pred, cm, output_dir)
        
        print()
        print("=" * 80)
        print("TEST EVALUATION COMPLETE")
        print("=" * 80)
        print()
        print(f"Best Model: Trial {trial_number}")
        print(f"Test PR-AUC: {metrics['pr_auc']:.6f}")
        print(f"Test ROC-AUC: {metrics['roc_auc']:.6f}")
        print(f"Test MCC: {metrics['mcc']:.6f}")
        print()
        print("Results saved to: artifacts/test_evaluation/")
        print()
        
        return 0
        
    except PrerequisiteCheckError as e:
        print()
        print("=" * 80)
        print("PREREQUISITE CHECK FAILED")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        print("Cannot proceed with test evaluation.")
        print("Ensure Milestone 1C.10 has completed successfully.")
        print()
        return 1
        
    except Exception as e:
        print()
        print("=" * 80)
        print("ERROR")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
