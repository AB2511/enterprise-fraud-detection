"""
Milestone 1C.11 - Baseline vs Optimized Model Comparison
Compare frozen baseline against best optimized model on test set.

PREREQUISITES:
- Milestone 1C.10 completed (≥50 trials)
- Test evaluation completed (evaluate_best_model_on_test.py)
- Baseline integrity verified
"""

import hashlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


class ComparisonError(Exception):
    """Raised when comparison cannot proceed."""

    pass


def check_prerequisites():
    """Verify all required artifacts exist."""
    print("=" * 80)
    print("PREREQUISITE VERIFICATION")
    print("=" * 80)
    print()
    
    required_files = {
        "baseline_metrics": "artifacts/models/baseline_metrics.json",
        "test_results": "artifacts/test_evaluation/test_results.json",
        "test_predictions": "artifacts/test_evaluation/test_predictions.npy",
        "test_probabilities": "artifacts/test_evaluation/test_probabilities.npy",
    }
    
    for name, path in required_files.items():
        filepath = Path(path)
        if not filepath.exists():
            raise ComparisonError(f"Required file missing: {path}")
        print(f"   ✓ {name}: {path}")
    
    print()
    print("✓ All required artifacts found")
    print()


def load_baseline_metrics():
    """Load frozen baseline metrics."""
    print("Loading baseline metrics...")
    
    with open("artifacts/models/baseline_metrics.json", "r") as f:
        baseline = json.load(f)
    
    metrics = baseline["validation_metrics"]
    print(f"   Baseline PR-AUC: {metrics['pr_auc']:.6f}")
    print()
    
    return metrics


def load_test_results():
    """Load test evaluation results."""
    print("Loading test evaluation results...")
    
    with open("artifacts/test_evaluation/test_results.json", "r") as f:
        results = json.load(f)
    
    metrics = results["test_metrics"]
    trial_number = results["trial_number"]
    
    print(f"   Best Trial: {trial_number}")
    print(f"   Test PR-AUC: {metrics['pr_auc']:.6f}")
    print()
    
    return trial_number, metrics, results["confusion_matrix"]


def compute_improvements(baseline_metrics, test_metrics):
    """Compute absolute and relative improvements."""
    print("=" * 80)
    print("COMPUTING IMPROVEMENTS")
    print("=" * 80)
    print()
    
    comparison = []
    
    for metric_name in ["roc_auc", "pr_auc", "mcc", "f1", "precision", "recall", "accuracy", "balanced_accuracy"]:
        baseline_val = baseline_metrics.get(metric_name, 0.0)
        test_val = test_metrics.get(metric_name, 0.0)
        
        abs_improvement = test_val - baseline_val
        rel_improvement = (abs_improvement / baseline_val * 100) if baseline_val != 0 else 0.0
        
        comparison.append({
            "metric": metric_name.upper().replace("_", " "),
            "baseline": baseline_val,
            "optimized": test_val,
            "absolute_improvement": abs_improvement,
            "relative_improvement_%": rel_improvement,
        })
    
    df = pd.DataFrame(comparison)
    
    print(df.to_string(index=False))
    print()
    
    return df


def generate_comparison_plots(comparison_df, output_dir: Path):
    """Generate comparison visualizations."""
    print("Generating comparison plots...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Plot 1: Metric Comparison Bar Chart
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(comparison_df))
    width = 0.35
    
    ax.bar(x - width/2, comparison_df['baseline'], width, label='Baseline', alpha=0.8)
    ax.bar(x + width/2, comparison_df['optimized'], width, label='Optimized', alpha=0.8)
    
    ax.set_xlabel('Metric')
    ax.set_ylabel('Value')
    ax.set_title('Baseline vs Optimized Model - Test Set Performance')
    ax.set_xticks(x)
    ax.set_xticklabels(comparison_df['metric'], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(output_dir / "baseline_vs_optimized_metrics.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    # Plot 2: Improvement Heatmap
    fig, ax = plt.subplots(figsize=(10, 8))
    improvement_data = comparison_df[['metric', 'relative_improvement_%']].set_index('metric')
    
    sns.heatmap(
        improvement_data.T,
        annot=True,
        fmt='.2f',
        cmap='RdYlGn',
        center=0,
        cbar_kws={'label': 'Relative Improvement (%)'},
        ax=ax
    )
    ax.set_title('Relative Improvement - Optimized vs Baseline')
    plt.tight_layout()
    plt.savefig(output_dir / "relative_improvement_heatmap.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Plots saved to {output_dir}")
    print()


def analyze_confusion_matrices(test_cm):
    """Analyze confusion matrix differences."""
    print("=" * 80)
    print("CONFUSION MATRIX ANALYSIS")
    print("=" * 80)
    print()
    
    print("Optimized Model (Test Set):")
    print(f"  TN: {test_cm['TN']:,}  FP: {test_cm['FP']:,}")
    print(f"  FN: {test_cm['FN']:,}  TP: {test_cm['TP']:,}")
    print()
    
    total = test_cm['TN'] + test_cm['FP'] + test_cm['FN'] + test_cm['TP']
    print(f"  Total: {total:,}")
    print(f"  Fraud Rate: {(test_cm['FN'] + test_cm['TP']) / total * 100:.2f}%")
    print(f"  Prediction Positive Rate: {(test_cm['FP'] + test_cm['TP']) / total * 100:.2f}%")
    print()


def generate_summary_report(trial_number, comparison_df, output_path: Path):
    """Generate markdown summary report."""
    print("Generating summary report...")
    
    with open(output_path, "w") as f:
        f.write("# Baseline vs Optimized Model Comparison\n\n")
        f.write(f"**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d')}\n")
        f.write(f"**Best Trial:** {trial_number}\n")
        f.write(f"**Evaluation:** Test Set (Hold-Out)\n\n")
        
        f.write("---\n\n")
        
        f.write("## Performance Comparison\n\n")
        f.write("| Metric | Baseline | Optimized | Absolute Δ | Relative Δ (%) |\n")
        f.write("|--------|----------|-----------|------------|----------------|\n")
        
        for _, row in comparison_df.iterrows():
            f.write(
                f"| {row['metric']} | "
                f"{row['baseline']:.6f} | "
                f"{row['optimized']:.6f} | "
                f"{row['absolute_improvement']:+.6f} | "
                f"{row['relative_improvement_%']:+.2f}% |\n"
            )
        
        f.write("\n---\n\n")
        
        f.write("## Key Findings\n\n")
        
        # Identify best improvements
        top_improvement = comparison_df.nlargest(1, 'absolute_improvement').iloc[0]
        f.write(f"**Best Improvement:** {top_improvement['metric']}\n")
        f.write(f"- Absolute: {top_improvement['absolute_improvement']:+.6f}\n")
        f.write(f"- Relative: {top_improvement['relative_improvement_%']:+.2f}%\n\n")
        
        # Check primary metric
        pr_auc_row = comparison_df[comparison_df['metric'] == 'PR AUC'].iloc[0]
        f.write(f"**Primary Metric (PR-AUC):**\n")
        f.write(f"- Baseline: {pr_auc_row['baseline']:.6f}\n")
        f.write(f"- Optimized: {pr_auc_row['optimized']:.6f}\n")
        f.write(f"- Change: {pr_auc_row['absolute_improvement']:+.6f} ({pr_auc_row['relative_improvement_%']:+.2f}%)\n\n")
        
        f.write("---\n\n")
        
        f.write("## Artifacts\n\n")
        f.write("- Comparison plots: `artifacts/comparison/`\n")
        f.write("- Test evaluation: `artifacts/test_evaluation/`\n")
        f.write("- Baseline metrics: `artifacts/models/baseline_metrics.json`\n")
        f.write("\n")
    
    print(f"✓ Report saved to {output_path}")
    print()


def main():
    """Main execution."""
    print("=" * 80)
    print("MILESTONE 1C.11 - BASELINE VS OPTIMIZED COMPARISON")
    print("=" * 80)
    print()
    
    try:
        # Step 1: Check prerequisites
        check_prerequisites()
        
        # Step 2: Load baseline metrics
        baseline_metrics = load_baseline_metrics()
        
        # Step 3: Load test results
        trial_number, test_metrics, test_cm = load_test_results()
        
        # Step 4: Compute improvements
        comparison_df = compute_improvements(baseline_metrics, test_metrics)
        
        # Step 5: Analyze confusion matrices
        analyze_confusion_matrices(test_cm)
        
        # Step 6: Generate plots
        output_dir = Path("artifacts/comparison")
        generate_comparison_plots(comparison_df, output_dir)
        
        # Step 7: Save comparison data
        comparison_df.to_csv(output_dir / "baseline_vs_optimized.csv", index=False)
        print(f"✓ Comparison data saved to {output_dir / 'baseline_vs_optimized.csv'}")
        print()
        
        # Step 8: Generate summary report
        report_path = Path("reports/milestone1/baseline_vs_optimized.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        generate_summary_report(trial_number, comparison_df, report_path)
        
        print("=" * 80)
        print("COMPARISON COMPLETE")
        print("=" * 80)
        print()
        print(f"Primary Metric (PR-AUC):")
        pr_auc = comparison_df[comparison_df['metric'] == 'PR AUC'].iloc[0]
        print(f"  Baseline:  {pr_auc['baseline']:.6f}")
        print(f"  Optimized: {pr_auc['optimized']:.6f}")
        print(f"  Change:    {pr_auc['absolute_improvement']:+.6f} ({pr_auc['relative_improvement_%']:+.2f}%)")
        print()
        
        return 0
        
    except ComparisonError as e:
        print()
        print("=" * 80)
        print("COMPARISON FAILED")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        print("Ensure test evaluation has completed successfully.")
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
