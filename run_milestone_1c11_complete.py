"""
Milestone 1C.11 - Master Execution Script
Orchestrates the complete hold-out test evaluation workflow.

EXECUTION ORDER:
1. Prerequisite checks
2. Test evaluation (evaluate_best_model_on_test.py)
3. Baseline comparison (compare_baseline_vs_optimized.py)
4. Engineering gate (engineering_gate.py)
5. Report generation

SAFETY:
- Only runs AFTER Milestone 1C.10 completes (50+ trials)
- Verifies all prerequisites before execution
- Aborts if any step fails
- Logs all operations
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class WorkflowError(Exception):
    """Raised when workflow fails."""

    pass


def print_header(title):
    """Print formatted section header."""
    print()
    print("=" * 80)
    print(title.center(80))
    print("=" * 80)
    print()


def print_step(step_num, step_name):
    """Print step header."""
    print()
    print(f"{'=' * 80}")
    print(f"STEP {step_num}: {step_name}")
    print(f"{'=' * 80}")
    print()


def run_script(script_name, description):
    """Run a Python script and check for success."""
    print(f"Running: {script_name}")
    print(f"Description: {description}")
    print()
    
    start_time = time.time()
    
    result = subprocess.run(
        [sys.executable, script_name],
        capture_output=True,
        text=True
    )
    
    elapsed_time = time.time() - start_time
    
    print(result.stdout)
    
    if result.returncode != 0:
        print()
        print("ERROR OUTPUT:")
        print(result.stderr)
        print()
        raise WorkflowError(f"{script_name} failed with return code {result.returncode}")
    
    print(f"✓ Completed in {elapsed_time:.1f} seconds")
    print()
    
    return result


def check_optimization_complete():
    """Verify optimization campaign completed."""
    print("Checking optimization campaign status...")
    
    summary_path = Path("artifacts/experiments/experiment_summary.csv")
    
    if not summary_path.exists():
        raise WorkflowError(
            "Optimization not started: experiment_summary.csv not found"
        )
    
    import pandas as pd
    
    df = pd.read_csv(summary_path)
    successful = df[df['training_success'] == True]
    n_successful = len(successful)
    
    print(f"   Successful trials: {n_successful}")
    
    if n_successful < 50:
        raise WorkflowError(
            f"Optimization incomplete: {n_successful} trials < 50 required.\n"
            f"Allow optimization to complete before running Milestone 1C.11."
        )
    
    print(f"   ✓ Optimization complete ({n_successful} trials)")
    print()


def generate_summary_report():
    """Generate final comprehensive summary."""
    print("Generating comprehensive summary report...")
    
    import json
    
    # Load all results
    with open("artifacts/test_evaluation/test_results.json", "r") as f:
        test_results = json.load(f)
    
    with open("artifacts/models/baseline_metrics.json", "r") as f:
        baseline = json.load(f)
    
    with open("reports/milestone1/engineering_gate.md", "r") as f:
        gate_report = f.read()
    
    trial_number = test_results["trial_number"]
    test_metrics = test_results["test_metrics"]
    baseline_metrics = baseline["validation_metrics"]
    
    # Extract verdict from gate report
    verdict = "UNKNOWN"
    for line in gate_report.split("\n"):
        if line.startswith("**Verdict:**"):
            verdict = line.split("**Verdict:**")[1].strip()
            break
    
    # Generate summary
    summary_path = Path("MILESTONE_1C11_FINAL_SUMMARY.md")
    
    with open(summary_path, "w") as f:
        f.write("# Milestone 1C.11 - Final Summary\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Pipeline:** Hold-Out Test Evaluation\n")
        f.write(f"**Status:** COMPLETE\n\n")
        
        f.write("---\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write(f"Completed hold-out test evaluation of best optimized model (Trial {trial_number}) ")
        f.write("against frozen baseline. Full comparison, validation, and engineering gate completed.\n\n")
        
        f.write("---\n\n")
        
        f.write("## Key Results\n\n")
        f.write("### Primary Metric: PR-AUC\n\n")
        
        baseline_pr = baseline_metrics["pr_auc"]
        test_pr = test_metrics["pr_auc"]
        improvement = test_pr - baseline_pr
        rel_improvement = (improvement / baseline_pr) * 100
        
        f.write(f"- **Baseline (Validation):** {baseline_pr:.6f}\n")
        f.write(f"- **Optimized (Test):** {test_pr:.6f}\n")
        f.write(f"- **Absolute Change:** {improvement:+.6f}\n")
        f.write(f"- **Relative Change:** {rel_improvement:+.2f}%\n\n")
        
        f.write("### All Metrics Comparison\n\n")
        f.write("| Metric | Baseline | Optimized | Change |\n")
        f.write("|--------|----------|-----------|--------|\n")
        
        for metric in ["roc_auc", "pr_auc", "mcc", "f1", "precision", "recall", "accuracy", "balanced_accuracy"]:
            b_val = baseline_metrics.get(metric, 0)
            t_val = test_metrics.get(metric, 0)
            change = t_val - b_val
            f.write(f"| {metric.upper()} | {b_val:.6f} | {t_val:.6f} | {change:+.6f} |\n")
        
        f.write("\n---\n\n")
        
        f.write("## Engineering Decision\n\n")
        f.write(f"**Verdict:** {verdict}\n\n")
        
        if "APPROVED" in verdict:
            f.write("✓ Model cleared for deployment consideration.\n\n")
        else:
            f.write("✗ Model not approved. Review required.\n\n")
        
        f.write("---\n\n")
        
        f.write("## Generated Artifacts\n\n")
        f.write("### Test Evaluation\n")
        f.write("- `artifacts/test_evaluation/test_results.json`\n")
        f.write("- `artifacts/test_evaluation/test_probabilities.npy`\n")
        f.write("- `artifacts/test_evaluation/test_predictions.npy`\n")
        f.write("- `artifacts/test_evaluation/test_roc_curve.png`\n")
        f.write("- `artifacts/test_evaluation/test_pr_curve.png`\n")
        f.write("- `artifacts/test_evaluation/test_calibration_curve.png`\n\n")
        
        f.write("### Comparison\n")
        f.write("- `artifacts/comparison/baseline_vs_optimized.csv`\n")
        f.write("- `artifacts/comparison/baseline_vs_optimized_metrics.png`\n")
        f.write("- `artifacts/comparison/relative_improvement_heatmap.png`\n\n")
        
        f.write("### Reports\n")
        f.write("- `reports/milestone1/baseline_vs_optimized.md`\n")
        f.write("- `reports/milestone1/engineering_gate.md`\n")
        f.write("- `MILESTONE_1C11_FINAL_SUMMARY.md`\n\n")
        
        f.write("---\n\n")
        
        f.write("## Next Steps\n\n")
        
        if "APPROVED" in verdict:
            f.write("1. Complete deployment planning\n")
            f.write("2. Prepare model documentation (model card)\n")
            f.write("3. Set up production monitoring\n")
            f.write("4. Plan deployment strategy (canary/blue-green)\n")
            f.write("5. Configure alerting and rollback procedures\n")
        else:
            f.write("1. Review engineering gate findings\n")
            f.write("2. Investigate performance issues\n")
            f.write("3. Consider alternative optimization strategies\n")
            f.write("4. Re-run optimization if needed\n")
        
        f.write("\n---\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("**Pipeline:** Milestone 1C.11 Complete\n")
    
    print(f"✓ Summary report saved to: {summary_path}")
    print()


def main():
    """Main workflow execution."""
    print_header("MILESTONE 1C.11 - HOLD-OUT TEST EVALUATION")
    
    print("This script orchestrates the complete test evaluation workflow:")
    print("  1. Test set evaluation (best model)")
    print("  2. Baseline comparison")
    print("  3. Engineering gate validation")
    print("  4. Report generation")
    print()
    print("⚠️  WARNING: Test set will be loaded and evaluated ONCE")
    print("⚠️  Results are FINAL and cannot be used for further optimization")
    print()
    
    input("Press Enter to continue or Ctrl+C to abort...")
    print()
    
    workflow_start = time.time()
    
    try:
        # Step 0: Prerequisites
        print_step(0, "PREREQUISITE CHECKS")
        check_optimization_complete()
        
        # Step 1: Test Evaluation
        print_step(1, "TEST SET EVALUATION")
        run_script(
            "evaluate_best_model_on_test.py",
            "Evaluate best model on hold-out test set"
        )
        
        # Step 2: Baseline Comparison
        print_step(2, "BASELINE COMPARISON")
        run_script(
            "compare_baseline_vs_optimized.py",
            "Compare baseline vs optimized model performance"
        )
        
        # Step 3: Engineering Gate
        print_step(3, "ENGINEERING GATE VALIDATION")
        result = run_script(
            "engineering_gate.py",
            "Validate deployment readiness"
        )
        
        # Step 4: Summary Report
        print_step(4, "FINAL SUMMARY GENERATION")
        generate_summary_report()
        
        # Completion
        workflow_time = time.time() - workflow_start
        
        print_header("MILESTONE 1C.11 COMPLETE")
        
        print(f"Total Workflow Time: {workflow_time:.1f} seconds ({workflow_time/60:.1f} minutes)")
        print()
        print("All steps completed successfully!")
        print()
        print("Review the following reports:")
        print("  - MILESTONE_1C11_FINAL_SUMMARY.md")
        print("  - reports/milestone1/baseline_vs_optimized.md")
        print("  - reports/milestone1/engineering_gate.md")
        print()
        print("Artifacts located in:")
        print("  - artifacts/test_evaluation/")
        print("  - artifacts/comparison/")
        print()
        
        return 0
        
    except WorkflowError as e:
        print()
        print_header("WORKFLOW FAILED")
        print(f"Error: {e}")
        print()
        print("Milestone 1C.11 did not complete.")
        print("Address the error and retry.")
        print()
        return 1
        
    except KeyboardInterrupt:
        print()
        print_header("WORKFLOW ABORTED")
        print("User cancelled execution.")
        print()
        return 1
        
    except Exception as e:
        print()
        print_header("UNEXPECTED ERROR")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
