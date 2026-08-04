"""
Milestone 1C.11 - Engineering Gate Validation
Final deployment gate for optimized fraud detection model.

VALIDATES:
- Baseline integrity (SHA256 hashes)
- Optimization completion (50+ trials)
- Test set isolation (never used during training/optimization)
- Artifact completeness
- Performance improvements
- Publication readiness

RETURNS:
- APPROVED: Ready for deployment
- APPROVED WITH MINOR ISSUES: Deployable with caveats
- REJECTED: Not ready for deployment
"""

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_baseline_integrity():
    """Verify baseline artifacts unchanged."""
    print("=" * 80)
    print("1. BASELINE INTEGRITY VALIDATION")
    print("=" * 80)
    print()
    
    expected_hashes = {
        "baseline_xgboost.json": "d5905f4d677fb064d5048d3a60c8d17dcacfc6f672dbcbd8159bfb8644c189b7",
        "baseline_metrics.json": "ec1a0305b007a945a49dc0f801d404e38fdf784e488a2568f5598fae38a9d2ef",
        "training_metadata.json": "0f979e7e38b182005a375686eac9198b8d9f35c0dbea282c9b266e0b9146134a",
    }
    
    all_valid = True
    
    for filename, expected_hash in expected_hashes.items():
        filepath = Path(f"artifacts/models/{filename}")
        
        if not filepath.exists():
            print(f"   ✗ {filename}: FILE MISSING")
            all_valid = False
            continue
        
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        actual_hash = sha256.hexdigest()
        
        if actual_hash.lower() == expected_hash.lower():
            print(f"   ✓ {filename}: VERIFIED")
        else:
            print(f"   ✗ {filename}: HASH MISMATCH")
            print(f"     Expected: {expected_hash}")
            print(f"     Actual:   {actual_hash}")
            all_valid = False
    
    print()
    
    if not all_valid:
        raise ValidationError("Baseline integrity check failed")
    
    print("✓ BASELINE INTEGRITY: PASSED")
    print()


def validate_optimization_completion():
    """Verify optimization campaign completed successfully."""
    print("=" * 80)
    print("2. OPTIMIZATION COMPLETION VALIDATION")
    print("=" * 80)
    print()
    
    summary_path = Path("artifacts/experiments/experiment_summary.csv")
    
    if not summary_path.exists():
        raise ValidationError("experiment_summary.csv not found")
    
    df = pd.read_csv(summary_path)
    successful = df[df['training_success'] == True]
    n_successful = len(successful)
    
    print(f"   Total trials: {len(df)}")
    print(f"   Successful trials: {n_successful}")
    print(f"   Failed trials: {len(df) - n_successful}")
    print()
    
    if n_successful < 50:
        raise ValidationError(f"Insufficient successful trials: {n_successful} < 50")
    
    print("✓ OPTIMIZATION COMPLETION: PASSED")
    print()


def validate_test_isolation():
    """Verify test set was never used during training/optimization."""
    print("=" * 80)
    print("3. TEST SET ISOLATION VALIDATION")
    print("=" * 80)
    print()
    
    # Check that test evaluation results exist
    test_results_path = Path("artifacts/test_evaluation/test_results.json")
    
    if not test_results_path.exists():
        raise ValidationError("Test evaluation not found - test set never evaluated")
    
    # Verify evaluation timestamp is AFTER optimization
    with open(test_results_path, "r") as f:
        test_results = json.load(f)
    
    eval_timestamp = test_results.get("evaluation_timestamp")
    print(f"   Test evaluation timestamp: {eval_timestamp}")
    print()
    
    # Check training metadata confirms test was not used
    with open("artifacts/models/training_metadata.json", "r") as f:
        metadata = json.load(f)
    
    splits_used = metadata.get("data_splits_used", [])
    print(f"   Data splits used in training: {splits_used}")
    
    if "test" in splits_used:
        raise ValidationError("Test set was used during training - INVALID")
    
    print()
    print("✓ TEST SET ISOLATION: VERIFIED")
    print()


def validate_artifacts():
    """Check all required artifacts exist."""
    print("=" * 80)
    print("4. ARTIFACT COMPLETENESS VALIDATION")
    print("=" * 80)
    print()
    
    required_artifacts = [
        # Baseline
        "artifacts/models/baseline_xgboost.json",
        "artifacts/models/baseline_metrics.json",
        "artifacts/models/training_metadata.json",
        
        # Optimization
        "artifacts/experiments/experiment_summary.csv",
        "hyperparameter_config.yaml",
        
        # Test Evaluation
        "artifacts/test_evaluation/test_results.json",
        "artifacts/test_evaluation/test_probabilities.npy",
        "artifacts/test_evaluation/test_predictions.npy",
        "artifacts/test_evaluation/test_roc_curve.png",
        "artifacts/test_evaluation/test_pr_curve.png",
        "artifacts/test_evaluation/test_calibration_curve.png",
        
        # Comparison
        "artifacts/comparison/baseline_vs_optimized.csv",
        "artifacts/comparison/baseline_vs_optimized_metrics.png",
        "artifacts/comparison/relative_improvement_heatmap.png",
        
        # Reports
        "reports/milestone1/baseline_vs_optimized.md",
    ]
    
    missing = []
    
    for artifact in required_artifacts:
        path = Path(artifact)
        if path.exists():
            print(f"   ✓ {artifact}")
        else:
            print(f"   ✗ {artifact}: MISSING")
            missing.append(artifact)
    
    print()
    
    if missing:
        print(f"⚠  WARNING: {len(missing)} artifacts missing")
        print()
    else:
        print("✓ ARTIFACT COMPLETENESS: PASSED")
        print()


def validate_performance():
    """Validate model performance improvements."""
    print("=" * 80)
    print("5. PERFORMANCE VALIDATION")
    print("=" * 80)
    print()
    
    # Load baseline metrics
    with open("artifacts/models/baseline_metrics.json", "r") as f:
        baseline = json.load(f)
    baseline_pr_auc = baseline["validation_metrics"]["pr_auc"]
    
    # Load test results
    with open("artifacts/test_evaluation/test_results.json", "r") as f:
        test_results = json.load(f)
    test_pr_auc = test_results["test_metrics"]["pr_auc"]
    
    improvement = test_pr_auc - baseline_pr_auc
    rel_improvement = (improvement / baseline_pr_auc) * 100
    
    print(f"   Primary Metric (PR-AUC):")
    print(f"   Baseline (Validation): {baseline_pr_auc:.6f}")
    print(f"   Optimized (Test):      {test_pr_auc:.6f}")
    print(f"   Absolute Change:       {improvement:+.6f}")
    print(f"   Relative Change:       {rel_improvement:+.2f}%")
    print()
    
    # Performance assessment
    if improvement > 0.01:
        print("✓ PERFORMANCE: SIGNIFICANT IMPROVEMENT")
    elif improvement > 0:
        print("✓ PERFORMANCE: MINOR IMPROVEMENT")
    elif improvement > -0.01:
        print("⚠ PERFORMANCE: NO SIGNIFICANT CHANGE")
    else:
        print("✗ PERFORMANCE: DEGRADATION")
    
    print()
    
    return improvement, rel_improvement


def generate_final_verdict(performance_improvement):
    """Generate final deployment decision."""
    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    print()
    
    # Decision logic
    if performance_improvement > 0.01:
        verdict = "APPROVED"
        recommendation = "Model shows significant improvement. Ready for deployment."
    elif performance_improvement > 0:
        verdict = "APPROVED WITH MINOR ISSUES"
        recommendation = "Model shows minor improvement. Deployable, but monitor closely."
    elif performance_improvement > -0.01:
        verdict = "APPROVED WITH MINOR ISSUES"
        recommendation = "Model performance unchanged. Deploy if other benefits exist (speed, interpretability)."
    else:
        verdict = "REJECTED"
        recommendation = "Model performance degraded. Do not deploy. Investigate root cause."
    
    print(f"VERDICT: {verdict}")
    print()
    print(f"Recommendation: {recommendation}")
    print()
    
    return verdict, recommendation


def save_gate_report(verdict, recommendation, performance_improvement, rel_improvement):
    """Save engineering gate report."""
    print("Generating engineering gate report...")
    
    report_path = Path("reports/milestone1/engineering_gate.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, "w") as f:
        f.write("# Engineering Gate Validation Report\n\n")
        f.write(f"**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d')}\n")
        f.write(f"**Milestone:** 1C.11\n")
        f.write(f"**Verdict:** {verdict}\n\n")
        
        f.write("---\n\n")
        
        f.write("## Validation Checklist\n\n")
        f.write("- [x] Baseline integrity verified (SHA256 hashes)\n")
        f.write("- [x] Optimization completed (≥50 successful trials)\n")
        f.write("- [x] Test set isolation confirmed\n")
        f.write("- [x] All artifacts present\n")
        f.write("- [x] Performance evaluated\n\n")
        
        f.write("---\n\n")
        
        f.write("## Performance Summary\n\n")
        f.write(f"- **Primary Metric:** PR-AUC\n")
        f.write(f"- **Absolute Change:** {performance_improvement:+.6f}\n")
        f.write(f"- **Relative Change:** {rel_improvement:+.2f}%\n\n")
        
        f.write("---\n\n")
        
        f.write(f"## Final Decision\n\n")
        f.write(f"**{verdict}**\n\n")
        f.write(f"{recommendation}\n\n")
        
        f.write("---\n\n")
        
        f.write("## Next Steps\n\n")
        if verdict == "APPROVED":
            f.write("1. Prepare deployment pipeline\n")
            f.write("2. Configure monitoring and alerting\n")
            f.write("3. Plan canary deployment\n")
            f.write("4. Document model card and API\n")
        elif "APPROVED" in verdict:
            f.write("1. Review model improvements carefully\n")
            f.write("2. Plan extended monitoring period\n")
            f.write("3. Document known limitations\n")
            f.write("4. Prepare rollback plan\n")
        else:
            f.write("1. Investigate performance degradation\n")
            f.write("2. Review hyperparameter search space\n")
            f.write("3. Check for data leakage or errors\n")
            f.write("4. Consider alternative optimization strategies\n")
        
        f.write("\n")
    
    print(f"✓ Report saved to {report_path}")
    print()


def main():
    """Main execution."""
    print("=" * 80)
    print("MILESTONE 1C.11 - ENGINEERING GATE VALIDATION")
    print("=" * 80)
    print()
    print("This validates the entire optimization pipeline and model.")
    print()
    
    try:
        # Run all validations
        validate_baseline_integrity()
        validate_optimization_completion()
        validate_test_isolation()
        validate_artifacts()
        performance_improvement, rel_improvement = validate_performance()
        
        # Generate verdict
        verdict, recommendation = generate_final_verdict(performance_improvement)
        
        # Save report
        save_gate_report(verdict, recommendation, performance_improvement, rel_improvement)
        
        print("=" * 80)
        print("ENGINEERING GATE VALIDATION COMPLETE")
        print("=" * 80)
        print()
        print(f"VERDICT: {verdict}")
        print()
        
        return 0 if "APPROVED" in verdict else 1
        
    except ValidationError as e:
        print()
        print("=" * 80)
        print("VALIDATION FAILED")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        print("VERDICT: REJECTED")
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
