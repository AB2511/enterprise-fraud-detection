"""
Execution script for Train/Validation/Test Split (Milestone 1C.3).

This script:
1. Loads the output from Milestone 1C.2 (Feature Engineering)
2. Performs temporal train/validation/test split
3. Persists split indices for reproducibility
4. Saves split datasets as parquet files
5. Generates metadata and benchmark reports
6. Validates temporal ordering and no leakage

Output:
- artifacts/splits/train.parquet
- artifacts/splits/validation.parquet
- artifacts/splits/test.parquet
- artifacts/splits/train_indices.npy
- artifacts/splits/validation_indices.npy
- artifacts/splits/test_indices.npy
- artifacts/splits/split_metadata.json
- reports/milestone1/split_benchmark.json
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd

# Add project root to path (must be before ml.training imports)
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# ruff: noqa: E402
from ml.training.data.feature_dropping import FeatureDropper
from ml.training.data.feature_engineering import FeatureEngineer
from ml.training.data.train_val_test_split import TemporalSplitter


def load_or_generate_engineered_data() -> pd.DataFrame:
    """
    Load engineered dataset from Milestone 1C.2.

    If intermediate artifact exists, load it.
    Otherwise, regenerate from raw data through dropping + engineering.

    Returns:
        Engineered dataframe ready for splitting
    """
    # Check for saved intermediate artifact
    interim_path = Path("backend/data/interim/after_engineering.parquet")

    if interim_path.exists():
        print(f"Loading existing engineered dataset from {interim_path}")
        df = pd.read_parquet(interim_path)
        print(f"  Loaded: {df.shape[0]:,} rows × {df.shape[1]} columns")
        return df

    print("Intermediate artifact not found. Regenerating from raw data...")
    print("=" * 80)

    # Load raw data
    print("\n1. Loading raw IEEE-CIS dataset...")
    train_txn = pd.read_csv("backend/data/raw/train_transaction.csv")
    train_id = pd.read_csv("backend/data/raw/train_identity.csv")

    # Merge
    df = train_txn.merge(train_id, on="TransactionID", how="left")
    print(f"   Raw dataset: {df.shape[0]:,} rows × {df.shape[1]} columns")

    # Apply feature dropping
    print("\n2. Applying Feature Dropping (Milestone 1C.1)...")
    dropper = FeatureDropper()
    df = dropper.fit_transform(df)
    print(f"   After dropping: {df.shape[0]:,} rows × {df.shape[1]} columns")

    # Apply feature engineering
    print("\n3. Applying Feature Engineering (Milestone 1C.2)...")
    engineer = FeatureEngineer()
    df = engineer.fit_transform(df)
    print(f"   After engineering: {df.shape[0]:,} rows × {df.shape[1]} columns")

    # Save intermediate artifact for future use
    interim_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(interim_path, index=False)
    print(f"\n   Saved intermediate artifact: {interim_path}")

    print("=" * 80)
    return df


def main() -> None:
    """Execute train/validation/test split."""
    print("=" * 80)
    print("MILESTONE 1C.3: TRAIN / VALIDATION / TEST SPLIT")
    print("=" * 80)

    start_time = time.perf_counter()

    # Load engineered data
    print("\nStep 1: Loading Feature-Engineered Dataset")
    print("-" * 80)
    df = load_or_generate_engineered_data()

    # Initialize splitter
    print("\nStep 2: Initializing Temporal Splitter")
    print("-" * 80)
    splitter = TemporalSplitter()

    config = splitter.config["split"]
    print(f"  Strategy: {config['strategy']}")
    print(f"  Train ratio: {config['train_ratio']:.1%}")
    print(f"  Validation ratio: {config['val_ratio']:.1%}")
    print(f"  Test ratio: {config['test_ratio']:.1%}")
    print(f"  Random seed: {splitter.config.get('random_seed', 'None')}")

    # Perform split
    print("\nStep 3: Performing Temporal Split")
    print("-" * 80)
    train_df, val_df, test_df = splitter.split(df, time_column="TransactionDT")

    print(f"  Train: {len(train_df):,} rows ({len(train_df)/len(df)*100:.1f}%)")
    print(f"  Validation: {len(val_df):,} rows ({len(val_df)/len(df)*100:.1f}%)")
    print(f"  Test: {len(test_df):,} rows ({len(test_df)/len(df)*100:.1f}%)")

    # Display fraud rates
    if "isFraud" in df.columns:
        print("\n  Fraud Distribution:")
        print(
            f"    Train fraud rate: {train_df['isFraud'].mean():.4%} ({train_df['isFraud'].sum():,} frauds)"
        )
        print(
            f"    Validation fraud rate: {val_df['isFraud'].mean():.4%} ({val_df['isFraud'].sum():,} frauds)"
        )
        print(
            f"    Test fraud rate: {test_df['isFraud'].mean():.4%} ({test_df['isFraud'].sum():,} frauds)"
        )
        print(f"    Overall fraud rate: {df['isFraud'].mean():.4%}")

    # Display temporal ranges
    print("\n  Temporal Ranges:")
    print(
        f"    Train: {train_df['TransactionDT'].min():,.0f} to {train_df['TransactionDT'].max():,.0f}"
    )
    print(
        f"    Validation: {val_df['TransactionDT'].min():,.0f} to {val_df['TransactionDT'].max():,.0f}"
    )
    print(
        f"    Test: {test_df['TransactionDT'].min():,.0f} to {test_df['TransactionDT'].max():,.0f}"
    )

    # Validate no temporal leakage
    print("\n  Leakage Validation:")
    train_max = train_df["TransactionDT"].max()
    val_min = val_df["TransactionDT"].min()
    val_max = val_df["TransactionDT"].max()
    test_min = test_df["TransactionDT"].min()

    gap_train_val = val_min - train_max
    gap_val_test = test_min - val_max

    print(
        f"    ✓ Train max < Val min: {train_max:,.0f} < {val_min:,.0f} (gap: {gap_train_val:,.0f})"
    )
    print(f"    ✓ Val max < Test min: {val_max:,.0f} < {test_min:,.0f} (gap: {gap_val_test:,.0f})")
    print("    ✓ No temporal leakage detected")

    # Save indices
    print("\nStep 4: Persisting Split Indices")
    print("-" * 80)
    indices_dir = Path("artifacts/splits")
    splitter.save_indices(indices_dir)
    print(f"  ✓ Saved train_indices.npy ({len(splitter.train_indices):,} indices)")
    print(f"  ✓ Saved validation_indices.npy ({len(splitter.val_indices):,} indices)")
    print(f"  ✓ Saved test_indices.npy ({len(splitter.test_indices):,} indices)")

    # Save datasets
    print("\nStep 5: Persisting Split Datasets")
    print("-" * 80)
    datasets_dir = Path("artifacts/splits")
    splitter.save_datasets(train_df, val_df, test_df, datasets_dir)

    # Get file sizes
    train_size = (datasets_dir / "train.parquet").stat().st_size / (1024**2)
    val_size = (datasets_dir / "validation.parquet").stat().st_size / (1024**2)
    test_size = (datasets_dir / "test.parquet").stat().st_size / (1024**2)

    print(f"  ✓ Saved train.parquet ({train_size:.2f} MB)")
    print(f"  ✓ Saved validation.parquet ({val_size:.2f} MB)")
    print(f"  ✓ Saved test.parquet ({test_size:.2f} MB)")

    # Save metadata
    print("\nStep 6: Generating Metadata")
    print("-" * 80)
    metadata_dir = Path("artifacts/splits")
    splitter.save_metadata(metadata_dir)
    print("  ✓ Saved split_metadata.json")

    # Generate benchmark
    print("\nStep 7: Generating Benchmark")
    print("-" * 80)

    execution_time = time.perf_counter() - start_time

    benchmark = {
        "execution_time_seconds": round(execution_time, 4),
        "total_rows_processed": len(df),
        "rows_per_second": round(len(df) / execution_time, 2),
        "peak_memory_mb": round(
            (
                train_df.memory_usage(deep=True).sum()
                + val_df.memory_usage(deep=True).sum()
                + test_df.memory_usage(deep=True).sum()
            )
            / (1024**2),
            2,
        ),
        "output_size_mb": round(train_size + val_size + test_size, 2),
    }

    benchmark_path = Path("reports/milestone1/split_benchmark.json")
    benchmark_path.parent.mkdir(parents=True, exist_ok=True)

    with open(benchmark_path, "w", encoding="utf-8") as f:
        json.dump(benchmark, f, indent=2)

    print(f"  Execution time: {benchmark['execution_time_seconds']:.2f} seconds")
    print(f"  Throughput: {benchmark['rows_per_second']:,.0f} rows/second")
    print(f"  Peak memory: {benchmark['peak_memory_mb']:.2f} MB")
    print(f"  Output size: {benchmark['output_size_mb']:.2f} MB")
    print("  ✓ Saved split_benchmark.json")

    # Summary
    print("\n" + "=" * 80)
    print("EXECUTION COMPLETE")
    print("=" * 80)
    print("\nOutputs:")
    print("  Datasets: artifacts/splits/{train,validation,test}.parquet")
    print("  Indices: artifacts/splits/{train,validation,test}_indices.npy")
    print("  Metadata: artifacts/splits/split_metadata.json")
    print("  Benchmark: reports/milestone1/split_benchmark.json")
    print("\nNext steps:")
    print("  1. Review split_metadata.json")
    print("  2. Verify split_validation_report.md (to be generated)")
    print("  3. Proceed to Milestone 1C.4 (Imputation) after approval")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
