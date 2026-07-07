#!/usr/bin/env python3
"""
Manual Test Runner for Dataset Adapters

Runs adapter tests manually without relying on pytest configuration.
"""

import sys
import traceback
from pathlib import Path
import tempfile
import shutil
import pandas as pd
import numpy as np

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def create_temp_directory():
    """Create temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    return Path(temp_dir)

def cleanup_temp_directory(temp_dir):
    """Clean up temporary directory."""
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

def test_adapter_imports():
    """Test that all adapter modules can be imported."""
    print("🔍 Testing adapter imports...")
    
    try:
        from ml.data.adapters import DatasetAdapter, CreditCardAdapter, IEEECISAdapter
        from ml.validation.schemas import DatasetType
        from ml.testing.fixtures import MockDatasetGenerator
        from ml.testing.assertions import (
            assert_dataframe_not_empty, assert_dataframe_schema,
            assert_dataframe_no_duplicates, assert_metadata_valid
        )
        print("✅ All adapter imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False

def test_creditcard_adapter():
    """Test CreditCard adapter functionality."""
    print("\n🔍 Testing CreditCard adapter...")
    
    temp_dir = create_temp_directory()
    
    try:
        from ml.data.adapters import CreditCardAdapter
        from ml.validation.schemas import DatasetType
        
        # Create mock CreditCard data
        n_rows = 100
        mock_data = {
            'Time': np.linspace(0, 172800, n_rows),
            'Amount': np.random.lognormal(3, 1, n_rows),
            'Class': np.random.choice([0, 1], n_rows, p=[0.998, 0.002]),
        }
        
        # Add V1-V28 PCA features
        for i in range(1, 29):
            mock_data[f'V{i}'] = np.random.normal(0, 1, n_rows)
        
        df = pd.DataFrame(mock_data)
        csv_path = temp_dir / "creditcard.csv"
        df.to_csv(csv_path, index=False)
        
        # Test adapter
        adapter = CreditCardAdapter(temp_dir)
        
        # Test dataset type
        assert adapter._get_dataset_type() == DatasetType.CREDITCARD
        print("  ✅ Dataset type correct")
        
        # Test raw data loading
        raw_df = adapter.load_raw_data()
        assert len(raw_df) == n_rows
        assert 'Time' in raw_df.columns
        assert 'Amount' in raw_df.columns
        assert 'Class' in raw_df.columns
        print("  ✅ Raw data loading works")
        
        # Test schema mapping
        standardized_df = adapter.map_to_standard_schema(raw_df)
        required_cols = ['transaction_id', 'timestamp', 'amount', 'is_fraud']
        for col in required_cols:
            assert col in standardized_df.columns
        print("  ✅ Schema mapping works")
        
        # Test full load process
        loaded_df = adapter.load()
        assert adapter.raw_df is not None
        assert adapter.metadata is not None
        assert len(loaded_df) == n_rows
        print("  ✅ Full load process works")
        
        # Test validation
        validation_results = adapter.validate(loaded_df)
        assert isinstance(validation_results, dict)
        assert 'schema_valid' in validation_results
        print("  ✅ Validation works")
        
        # Test normalization
        normalized_df = adapter.normalize(loaded_df)
        assert len(normalized_df) <= len(loaded_df)  # May remove duplicates
        print("  ✅ Normalization works")
        
        # Test transformation
        transformed_df = adapter.transform(normalized_df)
        assert len(transformed_df.columns) > len(normalized_df.columns)  # New features added
        print("  ✅ Transformation works")
        
        # Test export
        for format in ['parquet', 'csv', 'feather']:
            output_path = adapter.export(transformed_df, temp_dir, format=format)
            assert output_path.exists()
        print("  ✅ Export works")
        
        print("✅ CreditCard adapter tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ CreditCard adapter test failed: {e}")
        traceback.print_exc()
        return False
    finally:
        cleanup_temp_directory(temp_dir)

def test_ieee_cis_adapter():
    """Test IEEE-CIS adapter functionality."""
    print("\n🔍 Testing IEEE-CIS adapter...")
    
    temp_dir = create_temp_directory()
    
    try:
        from ml.data.adapters import IEEECISAdapter
        from ml.validation.schemas import DatasetType
        
        # Create mock IEEE-CIS data
        n_rows = 100
        transaction_data = {
            'TransactionID': range(1, n_rows + 1),
            'isFraud': np.random.choice([0, 1], n_rows, p=[0.97, 0.03]),
            'TransactionDT': np.random.randint(1, 1000000, n_rows),
            'TransactionAmt': np.random.lognormal(4, 1, n_rows),
            'ProductCD': np.random.choice(['W', 'C', 'R', 'H', 'S'], n_rows),
            'card1': np.random.randint(1000, 9999, n_rows),
            'card2': np.random.choice([100, 200, 300], n_rows),
            'addr1': np.random.randint(100, 999, n_rows),
            'addr2': np.random.randint(10, 99, n_rows),
            'dist1': np.random.uniform(0, 100, n_rows),
        }
        
        # Add some C, D, V features
        for i in range(1, 6):
            transaction_data[f'C{i}'] = np.random.randint(0, 10, n_rows)
            transaction_data[f'D{i}'] = np.random.uniform(0, 1000, n_rows)
        
        for i in range(1, 11):
            transaction_data[f'V{i}'] = np.random.normal(0, 1, n_rows)
        
        df = pd.DataFrame(transaction_data)
        csv_path = temp_dir / "train_transaction.csv"
        df.to_csv(csv_path, index=False)
        
        # Test adapter
        adapter = IEEECISAdapter(temp_dir)
        
        # Test dataset type
        assert adapter._get_dataset_type() == DatasetType.IEEE_CIS
        print("  ✅ Dataset type correct")
        
        # Test raw data loading
        raw_df = adapter.load_raw_data()
        assert len(raw_df) == n_rows
        assert 'TransactionID' in raw_df.columns
        assert 'TransactionAmt' in raw_df.columns
        assert 'isFraud' in raw_df.columns
        print("  ✅ Raw data loading works")
        
        # Test schema mapping
        standardized_df = adapter.map_to_standard_schema(raw_df)
        required_cols = ['transaction_id', 'timestamp', 'amount', 'is_fraud']
        for col in required_cols:
            assert col in standardized_df.columns
        print("  ✅ Schema mapping works")
        
        # Test full load process
        loaded_df = adapter.load()
        assert adapter.raw_df is not None
        assert adapter.metadata is not None
        assert len(loaded_df) == n_rows
        print("  ✅ Full load process works")
        
        # Test validation
        validation_results = adapter.validate(loaded_df)
        assert isinstance(validation_results, dict)
        assert 'schema_valid' in validation_results
        print("  ✅ Validation works")
        
        # Test normalization
        normalized_df = adapter.normalize(loaded_df)
        assert len(normalized_df) <= len(loaded_df)
        print("  ✅ Normalization works")
        
        # Test transformation
        transformed_df = adapter.transform(normalized_df)
        assert len(transformed_df.columns) > len(normalized_df.columns)
        print("  ✅ Transformation works")
        
        # Test export
        for format in ['parquet', 'csv']:  # Skip feather for now
            output_path = adapter.export(transformed_df, temp_dir, format=format)
            assert output_path.exists()
        print("  ✅ Export works")
        
        print("✅ IEEE-CIS adapter tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ IEEE-CIS adapter test failed: {e}")
        traceback.print_exc()
        return False
    finally:
        cleanup_temp_directory(temp_dir)

def test_adapter_compatibility():
    """Test that both adapters produce compatible schemas."""
    print("\n🔍 Testing adapter compatibility...")
    
    temp_dir = create_temp_directory()
    
    try:
        from ml.data.adapters import CreditCardAdapter, IEEECISAdapter
        
        # Create CreditCard data
        cc_data = pd.DataFrame({
            'Time': np.linspace(0, 172800, 50),
            'Amount': np.random.lognormal(3, 1, 50),
            'Class': np.random.choice([0, 1], 50, p=[0.98, 0.02]),
            **{f'V{i}': np.random.normal(0, 1, 50) for i in range(1, 29)}
        })
        
        cc_path = temp_dir / "creditcard"
        cc_path.mkdir()
        cc_data.to_csv(cc_path / "creditcard.csv", index=False)
        
        # Create IEEE-CIS data
        ieee_data = pd.DataFrame({
            'TransactionID': range(1, 51),
            'isFraud': np.random.choice([0, 1], 50, p=[0.97, 0.03]),
            'TransactionDT': np.random.randint(1, 1000000, 50),
            'TransactionAmt': np.random.lognormal(4, 1, 50),
            'ProductCD': np.random.choice(['W', 'C', 'R'], 50),
            'card1': np.random.randint(1000, 9999, 50),
            'addr1': np.random.randint(100, 999, 50),
        })
        
        ieee_path = temp_dir / "ieee_cis"
        ieee_path.mkdir()
        ieee_data.to_csv(ieee_path / "train_transaction.csv", index=False)
        
        # Load both datasets
        cc_adapter = CreditCardAdapter(cc_path)
        ieee_adapter = IEEECISAdapter(ieee_path)
        
        cc_df = cc_adapter.load()
        ieee_df = ieee_adapter.load()
        
        # Check that both have required standard columns
        required_cols = ['transaction_id', 'timestamp', 'amount', 'is_fraud']
        
        for col in required_cols:
            assert col in cc_df.columns, f"CreditCard missing {col}"
            assert col in ieee_df.columns, f"IEEE-CIS missing {col}"
        
        print("  ✅ Both adapters have required columns")
        
        # Check compatible data types
        for col in required_cols:
            cc_dtype = cc_df[col].dtype
            ieee_dtype = ieee_df[col].dtype
            
            if col == 'amount':
                assert pd.api.types.is_numeric_dtype(cc_dtype)
                assert pd.api.types.is_numeric_dtype(ieee_dtype)
            elif col == 'is_fraud':
                assert pd.api.types.is_bool_dtype(cc_dtype) or pd.api.types.is_integer_dtype(cc_dtype)
                assert pd.api.types.is_bool_dtype(ieee_dtype) or pd.api.types.is_integer_dtype(ieee_dtype)
        
        print("  ✅ Compatible data types")
        
        print("✅ Adapter compatibility tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Adapter compatibility test failed: {e}")
        traceback.print_exc()
        return False
    finally:
        cleanup_temp_directory(temp_dir)

def test_pipeline_stages():
    """Test pipeline stages integration."""
    print("\n🔍 Testing pipeline stages...")
    
    temp_dir = create_temp_directory()
    
    try:
        from ml.data.pipeline_stages import (
            DatasetLoadingStage, DatasetValidationStage
        )
        
        # Create mock CreditCard data
        mock_data = {
            'Time': np.linspace(0, 172800, 20),
            'Amount': np.random.lognormal(3, 1, 20),
            'Class': np.random.choice([0, 1], 20, p=[0.95, 0.05]),
            **{f'V{i}': np.random.normal(0, 1, 20) for i in range(1, 29)}
        }
        
        df = pd.DataFrame(mock_data)
        csv_path = temp_dir / "creditcard.csv"
        df.to_csv(csv_path, index=False)
        
        # Test loading stage
        loading_stage = DatasetLoadingStage(dataset_type="creditcard")
        loading_outputs = loading_stage.execute({"raw_data_path": str(temp_dir)})
        
        assert "dataset" in loading_outputs
        assert "adapter" in loading_outputs
        assert "dataset_type" in loading_outputs
        print("  ✅ Dataset loading stage works")
        
        # Test validation stage
        validation_stage = DatasetValidationStage()
        validation_outputs = validation_stage.execute(loading_outputs)
        
        assert "validation_results" in validation_outputs
        assert "validation_summary" in validation_outputs
        print("  ✅ Dataset validation stage works")
        
        print("✅ Pipeline stages tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Pipeline stages test failed: {e}")
        traceback.print_exc()
        return False
    finally:
        cleanup_temp_directory(temp_dir)

def main():
    """Run all tests."""
    print("🚀 Running Dataset Adapter Tests")
    print("=" * 60)
    
    tests = [
        ("Adapter Imports", test_adapter_imports),
        ("CreditCard Adapter", test_creditcard_adapter),
        ("IEEE-CIS Adapter", test_ieee_cis_adapter),
        ("Adapter Compatibility", test_adapter_compatibility),
        ("Pipeline Stages", test_pipeline_stages),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 60)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dataset adapters are working correctly.")
        return 0
    else:
        print(f"💥 {total - passed} tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())