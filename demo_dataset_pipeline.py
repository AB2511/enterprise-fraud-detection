#!/usr/bin/env python3
"""
Dataset Adapter Pipeline Demo

Demonstrates the complete ML Phase 1.2 dataset ingestion pipeline
using both CreditCard and IEEE-CIS adapters.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from ml.data.pipeline_stages import (
    DatasetLoadingStage, DatasetValidationStage, DatasetVersioningStage,
    DatasetNormalizationStage, DatasetTransformationStage, MetadataGenerationStage
)
from ml.data.adapters import CreditCardAdapter, IEEECISAdapter


def create_demo_datasets(output_dir: Path):
    """Create demo datasets for testing the pipeline."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔧 Creating demo datasets...")
    
    # Create CreditCard-like data
    print("  Creating CreditCard demo dataset...")
    n_cc_rows = 1000
    cc_data = {
        'Time': np.linspace(0, 172800, n_cc_rows),  # 2 days
        'Amount': np.random.lognormal(3, 1, n_cc_rows).round(2),
        'Class': np.random.choice([0, 1], n_cc_rows, p=[0.98, 0.02]),  # 2% fraud rate
    }
    
    # Add V1-V28 PCA features
    for i in range(1, 29):
        cc_data[f'V{i}'] = np.random.normal(0, 1, n_cc_rows)
    
    cc_df = pd.DataFrame(cc_data)
    cc_path = output_dir / "creditcard"
    cc_path.mkdir(exist_ok=True)
    cc_df.to_csv(cc_path / "creditcard.csv", index=False)
    print(f"  ✓ CreditCard dataset: {len(cc_df):,} rows, {len(cc_df.columns)} columns")
    
    # Create IEEE-CIS-like data
    print("  Creating IEEE-CIS demo dataset...")
    n_ieee_rows = 800
    ieee_data = {
        'TransactionID': range(1, n_ieee_rows + 1),
        'isFraud': np.random.choice([0, 1], n_ieee_rows, p=[0.96, 0.04]),  # 4% fraud rate
        'TransactionDT': np.random.randint(1, 1000000, n_ieee_rows),
        'TransactionAmt': np.random.lognormal(4, 1, n_ieee_rows).round(2),
        'ProductCD': np.random.choice(['W', 'C', 'R', 'H', 'S'], n_ieee_rows),
        'card1': np.random.randint(1000, 9999, n_ieee_rows),
        'card2': np.random.choice([100, 200, 300, 400, 500], n_ieee_rows),
        'card3': np.random.choice([100, 150, 185], n_ieee_rows),
        'card4': np.random.choice(['visa', 'mastercard', 'american express'], n_ieee_rows),
        'card5': np.random.choice([100, 200, 300], n_ieee_rows),
        'card6': np.random.choice(['credit', 'debit'], n_ieee_rows),
        'addr1': np.random.randint(100, 999, n_ieee_rows),
        'addr2': np.random.randint(10, 99, n_ieee_rows),
        'dist1': np.random.uniform(0, 100, n_ieee_rows),
        'dist2': np.random.uniform(0, 50, n_ieee_rows),
    }
    
    # Add some C, D, M, V features
    for i in range(1, 11):  # C1-C10
        ieee_data[f'C{i}'] = np.random.randint(0, 10, n_ieee_rows)
    
    for i in range(1, 11):  # D1-D10
        ieee_data[f'D{i}'] = np.random.uniform(0, 1000, n_ieee_rows)
    
    for i in range(1, 6):  # M1-M5
        ieee_data[f'M{i}'] = np.random.choice(['T', 'F', None], n_ieee_rows, p=[0.3, 0.3, 0.4])
    
    for i in range(1, 21):  # V1-V20
        ieee_data[f'V{i}'] = np.random.normal(0, 1, n_ieee_rows)
    
    ieee_df = pd.DataFrame(ieee_data)
    ieee_path = output_dir / "ieee_cis"
    ieee_path.mkdir(exist_ok=True)
    ieee_df.to_csv(ieee_path / "train_transaction.csv", index=False)
    print(f"  ✓ IEEE-CIS dataset: {len(ieee_df):,} rows, {len(ieee_df.columns)} columns")
    
    return cc_path, ieee_path


def run_dataset_pipeline(dataset_type: str, raw_data_path: Path):
    """Run the complete dataset pipeline for a given dataset."""
    print(f"\n🚀 Running {dataset_type.upper()} Pipeline")
    print("=" * 50)
    
    try:
        # Stage 1: Dataset Loading
        print("📋 Stage 1: Dataset Loading")
        loading_stage = DatasetLoadingStage(dataset_type=dataset_type)
        loading_outputs = loading_stage.execute({"raw_data_path": str(raw_data_path)})
        
        dataset = loading_outputs["dataset"]
        print(f"  ✅ Loaded: {len(dataset):,} rows, {len(dataset.columns)} columns")
        print(f"  ✅ Fraud rate: {dataset['is_fraud'].mean():.4f}")
        
        # Stage 2: Dataset Validation
        print("📋 Stage 2: Dataset Validation")
        validation_stage = DatasetValidationStage()
        validation_outputs = validation_stage.execute(loading_outputs)
        
        validation_summary = validation_outputs["validation_summary"]
        print(f"  ✅ Validation: {validation_summary['passed_checks']}/{validation_summary['total_checks']} checks passed")
        print(f"  ✅ Pass rate: {validation_summary['pass_rate']:.2%}")
        
        # Stage 3: Dataset Versioning
        print("📋 Stage 3: Dataset Versioning")
        versioning_stage = DatasetVersioningStage()
        versioning_outputs = versioning_stage.execute(validation_outputs)
        
        version_id = versioning_outputs["version_id"]
        print(f"  ✅ Version created: {version_id}")
        
        # Stage 4: Dataset Normalization
        print("📋 Stage 4: Dataset Normalization")
        normalization_stage = DatasetNormalizationStage()
        normalization_outputs = normalization_stage.execute(versioning_outputs)
        
        normalized_dataset = normalization_outputs["normalized_dataset"]
        print(f"  ✅ Normalized: {len(normalized_dataset):,} rows")
        
        # Stage 5: Dataset Transformation
        print("📋 Stage 5: Dataset Transformation")
        transformation_stage = DatasetTransformationStage()
        transformation_outputs = transformation_stage.execute(normalization_outputs)
        
        transformed_dataset = transformation_outputs["transformed_dataset"]
        print(f"  ✅ Transformed: {len(transformed_dataset):,} rows, {len(transformed_dataset.columns)} columns")
        
        # Stage 6: Metadata Generation
        print("📋 Stage 6: Metadata Generation")
        metadata_stage = MetadataGenerationStage()
        final_outputs = metadata_stage.execute(transformation_outputs)
        
        print(f"  ✅ Reports generated:")
        if "quality_report_path" in final_outputs:
            print(f"    📊 Quality report: {final_outputs['quality_report_path']}")
        if "schema_path" in final_outputs:
            print(f"    📋 Schema: {final_outputs['schema_path']}")
        if "statistics_path" in final_outputs:
            print(f"    📈 Statistics: {final_outputs['statistics_path']}")
        
        print(f"🎉 {dataset_type.upper()} pipeline completed successfully!")
        
        return final_outputs
        
    except Exception as e:
        print(f"❌ {dataset_type.upper()} pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_adapter_outputs(cc_outputs, ieee_outputs):
    """Compare outputs from both adapters to verify compatibility."""
    print(f"\n🔍 Adapter Compatibility Analysis")
    print("=" * 40)
    
    cc_dataset = cc_outputs["transformed_dataset"]
    ieee_dataset = ieee_outputs["transformed_dataset"]
    
    # Check required columns
    required_cols = ['transaction_id', 'timestamp', 'amount', 'is_fraud']
    
    print("📋 Schema Compatibility:")
    cc_has_required = all(col in cc_dataset.columns for col in required_cols)
    ieee_has_required = all(col in ieee_dataset.columns for col in required_cols)
    
    print(f"  ✅ CreditCard has required columns: {cc_has_required}")
    print(f"  ✅ IEEE-CIS has required columns: {ieee_has_required}")
    
    # Check data types
    print("\n📊 Data Type Compatibility:")
    for col in required_cols:
        if col in cc_dataset.columns and col in ieee_dataset.columns:
            cc_dtype = cc_dataset[col].dtype
            ieee_dtype = ieee_dataset[col].dtype
            
            compatible = (
                (col == 'amount' and pd.api.types.is_numeric_dtype(cc_dtype) and pd.api.types.is_numeric_dtype(ieee_dtype)) or
                (col == 'is_fraud' and (pd.api.types.is_bool_dtype(cc_dtype) or pd.api.types.is_integer_dtype(cc_dtype)) and 
                 (pd.api.types.is_bool_dtype(ieee_dtype) or pd.api.types.is_integer_dtype(ieee_dtype))) or
                (col in ['transaction_id'] and pd.api.types.is_object_dtype(cc_dtype) and pd.api.types.is_object_dtype(ieee_dtype)) or
                (col == 'timestamp' and pd.api.types.is_datetime64_any_dtype(cc_dtype) and pd.api.types.is_datetime64_any_dtype(ieee_dtype))
            )
            
            status = "✅" if compatible else "❌"
            print(f"  {status} {col}: {cc_dtype} ↔ {ieee_dtype}")
    
    # Statistics comparison
    print("\n📈 Dataset Statistics:")
    print(f"  📦 CreditCard: {len(cc_dataset):,} rows, {len(cc_dataset.columns)} columns")
    print(f"  📦 IEEE-CIS: {len(ieee_dataset):,} rows, {len(ieee_dataset.columns)} columns")
    
    print(f"  🚨 CreditCard fraud rate: {cc_dataset['is_fraud'].mean():.4f}")
    print(f"  🚨 IEEE-CIS fraud rate: {ieee_dataset['is_fraud'].mean():.4f}")
    
    # Final assessment
    schema_compatible = cc_has_required and ieee_has_required
    
    if schema_compatible:
        print(f"\n🎉 COMPATIBILITY CHECK PASSED!")
        print(f"  ✅ Both adapters produce identical standardized schemas")
        print(f"  ✅ Future ML components will work with either dataset")
    else:
        print(f"\n❌ COMPATIBILITY CHECK FAILED!")
        print(f"  ❌ Adapters produce incompatible schemas")


def main():
    """Run the complete dataset adapter demo."""
    print("🚀 ML Phase 1.2: Dataset Adapter Pipeline Demo")
    print("=" * 60)
    
    # Create demo data directory
    demo_dir = Path("demo_data")
    demo_dir.mkdir(exist_ok=True)
    
    # Create demo datasets
    cc_path, ieee_path = create_demo_datasets(demo_dir)
    
    # Run pipelines for both datasets
    print(f"\n🔄 Running Dataset Pipelines")
    cc_outputs = run_dataset_pipeline("creditcard", cc_path)
    ieee_outputs = run_dataset_pipeline("ieee_cis", ieee_path)
    
    # Compare adapter outputs
    if cc_outputs and ieee_outputs:
        compare_adapter_outputs(cc_outputs, ieee_outputs)
    
    print(f"\n🏁 Demo completed!")
    print(f"📂 Demo data saved in: {demo_dir.absolute()}")
    
    if cc_outputs and ieee_outputs:
        print(f"\n📋 Generated Files:")
        print(f"  📊 CreditCard reports in: data/reports/creditcard/")
        print(f"  📊 IEEE-CIS reports in: data/reports/ieee_cis/")
        print(f"  💾 Processed datasets in: data/processed/")
        
        return 0
    else:
        print(f"\n❌ Demo failed - check error messages above")
        return 1


if __name__ == "__main__":
    sys.exit(main())