"""
Monitor Hyperparameter Optimization Progress
Checks completion status and estimates time remaining
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

def main():
    print("=" * 80)
    print("HYPERPARAMETER OPTIMIZATION PROGRESS MONITOR")
    print("=" * 80)
    print()
    
    # Check summary file
    summary_path = Path("artifacts/experiments/experiment_summary.csv")
    
    if not summary_path.exists():
        print("[ERROR] No summary file found. Optimization may not have started.")
        return
    
    # Load results
    df = pd.read_csv(summary_path)
    
    # Count trials
    total_trials = len(df)
    successful_trials = df['training_success'].sum()
    failed_trials = total_trials - successful_trials
    
    # Target
    target_trials = 50
    remaining_trials = target_trials - total_trials
    completion_pct = (total_trials / target_trials) * 100
    
    print(f"COMPLETION STATUS")
    print(f"  Completed trials: {total_trials} / {target_trials}")
    print(f"  Successful: {successful_trials}")
    print(f"  Failed: {failed_trials}")
    print(f"  Remaining: {remaining_trials}")
    print(f"  Progress: {completion_pct:.1f}%")
    print()
    
    # Time estimates
    if total_trials > 0:
        avg_time = df['training_time'].mean()
        median_time = df['training_time'].median()
        
        estimated_remaining_seconds = avg_time * remaining_trials
        estimated_remaining_hours = estimated_remaining_seconds / 3600
        
        print(f"TIME STATISTICS")
        print(f"  Average training time: {avg_time:.1f} seconds ({avg_time/60:.1f} minutes)")
        print(f"  Median training time: {median_time:.1f} seconds ({median_time/60:.1f} minutes)")
        print(f"  Estimated remaining: {estimated_remaining_hours:.1f} hours")
        print()
        
        # Best trial so far
        successful_df = df[df['training_success'] == True]
        if len(successful_df) > 0:
            best_idx = successful_df['metric_pr_auc'].idxmax()
            best_trial = successful_df.loc[best_idx]
            
            print(f"BEST TRIAL SO FAR")
            print(f"  Trial number: {best_trial['trial_number']}")
            print(f"  PR-AUC: {best_trial['metric_pr_auc']:.6f}")
            print(f"  ROC-AUC: {best_trial['metric_roc_auc']:.6f}")
            print(f"  MCC: {best_trial['metric_mcc']:.6f}")
            print(f"  F1: {best_trial['metric_f1']:.6f}")
            print()
    
    # Check experiment directories
    exp_dir = Path("artifacts/experiments")
    exp_dirs = sorted([d for d in exp_dir.iterdir() if d.is_dir() and d.name.startswith("experiment_")])
    
    print(f"EXPERIMENT DIRECTORIES")
    print(f"  Total directories: {len(exp_dirs)}")
    print()
    
    # Check if optimization is likely still running
    if remaining_trials > 0:
        print(f"STATUS: OPTIMIZATION IN PROGRESS")
        print(f"  {remaining_trials} trials remaining")
        print(f"  Estimated completion: ~{estimated_remaining_hours:.1f} hours from now")
    else:
        print(f"STATUS: OPTIMIZATION COMPLETE")
        print(f"  All {target_trials} trials finished")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
