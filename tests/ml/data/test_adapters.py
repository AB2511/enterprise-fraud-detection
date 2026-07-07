"""
Tests for Dataset Adapters

Comprehensive tests for CreditCard and IEEE-CIS dataset adapters.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

from ml.data.adapters import CreditCardAdapter, IEEECISAdapter, DatasetAdapter
from ml.validation.schemas import DatasetType
from ml.testing.fixtures import MockDatasetGenerator
from ml.testing.assertions import (
    assert_dataframe_not_empty, assert_dataframe_schema,
    assert_dataframe_no_duplicates, assert_metadata_valid
)


class TestDatasetAdapterBase:
    """Base test class for common adapter functionality."""
    
    def test_adapter_inheritance(self):
        """Test that adapters inherit from DatasetAdapter."""
        assert issubclass(CreditCardAdapter, DatasetAdapter)
        assert issubclass(IEEECISAdapter, DatasetAdapter)
    
    def test_adapter_initialization(self, temp_directory):
        """Test adapter initialization."""
        # Test CreditCard adapter
        cc_adapter = CreditCardAdapter(temp_directory)
        assert cc_adapter._get_dataset_type() == DatasetType.CREDITCARD
        assert cc_adapter.raw_data_path == temp_directory
        
        # Test IEEE-CIS adapter
        ieee_adapter = IEEECISAdapter(temp_directory)
        assert ieee_adapter._get_dataset_type() == DatasetType.IEEE_CIS
        assert ieee_adapter.raw_data_path == temp_directory


class TestCreditCardAdapter:
    """Tests for CreditCard dataset adapter."""
    
    @pytest.fixture
    def mock_creditcard_data(self, temp_directory):
        """Create mock CreditCard dataset."""
        # Generate realistic CreditCard-like data
        n_rows = 1000
        
        data = {
            'Time': np.linspace(0, 172800, n_rows),  # 2 days worth of seconds
            'Amount': np.random.lognormal(3, 1, n_rows).round(2),
            'Class': np.random.choice([0, 1], n_rows, p=[0.998, 0.002]),  # 0.2% fraud rate
        }
        
        # Add V1-V28 PCA features
        for i in range(1, 29):
            data[f'V{i}'] = np.random.normal(0, 1, n_rows)
        
        df = pd.DataFrame(data)
        
        # Save to CSV
        csv_path = temp_directory / "creditcard.csv"
        df.to_csv(csv_path, index=False)
        
        return csv_path, df
    
    def test_load_raw_data(self, mock_creditcard_data):
        """Test loading raw CreditCard data."""
        csv_path, expected_df = mock_creditcard_data
        adapter = CreditCardAdapter(csv_path.parent)
        
        raw_df = adapter.load_raw_data()
        
        assert_dataframe_not_empty(raw_df)
        assert len(raw_df) == len(expected_df)
        assert set(raw_df.columns) == set(expected_df.columns)
        
        # Check data types
        assert raw_df['Time'].dtype == 'float64'
        assert raw_df['Amount'].dtype == 'float64'
        assert raw_df['Class'].dtype == 'int8'
    
    def test_load_raw_data_file_not_found(self, temp_directory):
        """Test error handling when CSV file not found."""
        adapter = CreditCardAdapter(temp_directory)
        
        with pytest.raises(FileNotFoundError) as exc_info:
            adapter.load_raw_data()
        
        assert "creditcard.csv" in str(exc_info.value)
    
    def test_schema_validation(self, mock_creditcard_data):
        """Test CreditCard schema validation."""
        csv_path, _ = mock_creditcard_data
        adapter = CreditCardAdapter(csv_path.parent)
        
        raw_df = adapter.load_raw_data()
        
        # Should not raise any exceptions
        adapter._validate_creditcard_schema(raw_df)
    
    def test_schema_validation_missing_columns(self, temp_directory):
        """Test schema validation with missing columns."""
        # Create invalid dataset
        invalid_data = pd.DataFrame({
            'Time': [1, 2, 3],
            'Amount': [10, 20, 30],
            # Missing 'Class' column and V features
        })
        
        csv_path = temp_directory / "creditcard.csv"
        invalid_data.to_csv(csv_path, index=False)
        
        adapter = CreditCardAdapter(temp_directory)
        raw_df = adapter.load_raw_data()
        
        with pytest.raises(ValueError) as exc_info:
            adapter._validate_creditcard_schema(raw_df)
        
        assert "Missing expected columns" in str(exc_info.value)
    
    def test_map_to_standard_schema(self, mock_creditcard_data):
        """Test mapping to standard schema."""
        csv_path, _ = mock_creditcard_data
        adapter = CreditCardAdapter(csv_path.parent)
        
        raw_df = adapter.load_raw_data()
        standardized_df = adapter.map_to_standard_schema(raw_df)
        
        # Check required standard columns
        required_cols = ['transaction_id', 'timestamp', 'amount', 'is_fraud']
        assert_dataframe_schema(
            standardized_df, 
            required_cols,
            expected_dtypes={
                'amount': 'float64',
                'is_fraud': 'bool'
            }
        )
        
        # Check that all transactions have unique IDs
        assert_dataframe_no_duplicates(standardized_df, subset=['transaction_id'])
        
        # Check derived features
        assert 'amount_log' in standardized_df.columns
        assert 'hour' in standardized_df.columns
        assert 'day_of_week' in standardized_df.columns
        
        # Check PCA features were preserved
        pca_cols = [col for col in standardized_df.columns if col.startswith('pca_feature_')]
        assert len(pca_cols) == 28  # V1-V28 mapped to pca_feature_01-28
    
    def test_get_schema_mapping(self, temp_directory):
        """Test schema mapping dictionary."""
        adapter = CreditCardAdapter(temp_directory)
        mapping = adapter.get_schema_mapping()
        
        assert isinstance(mapping, dict)
        assert mapping['amount'] == 'Amount'
        assert mapping['is_fraud'] == 'Class'
        assert mapping['pca_feature_01'] == 'V1'
        assert mapping['pca_feature_28'] == 'V28'
        
        # Check synthetic fields
        assert mapping['transaction_id'] is None
        assert mapping['timestamp'] is None
        assert mapping['customer_id'] is None
    
    def test_full_load_process(self, mock_creditcard_data):
        """Test complete load process."""
        csv_path, _ = mock_creditcard_data
        adapter = CreditCardAdapter(csv_path.parent)
        
        standardized_df = adapter.load()
        
        # Check that adapter state is updated
        assert adapter.raw_df is not None
        assert adapter.metadata is not None
        
        # Validate metadata
        assert_metadata_valid(adapter.metadata, ['dataset_name', 'fraud_rate', 'num_records'])
        assert adapter.metadata.dataset_type == DatasetType.CREDITCARD
        
        # Check dataset
        assert_dataframe_not_empty(standardized_df)
        required_cols = ['transaction_id', 'timestamp', 'amount', 'is_fraud']
        for col in required_cols:
            assert col in standardized_df.columns
    
    def test_validate_method(self, mock_creditcard_data):
        """Test adapter validation method."""
        csv_path, _ = mock_creditcard_data
        adapter = CreditCardAdapter(csv_path.parent)
        
        standardized_df = adapter.load()
        validation_results = adapter.validate(standardized_df)
        
        assert isinstance(validation_results, dict)
        assert 'schema_valid' in validation_results
        assert 'issues' in validation_results
        assert 'warnings' in validation_results
        assert 'statistics' in validation_results
        
        # Should be valid for mock data
        assert validation_results['schema_valid'] is True
    
    def test_normalize_method(self, mock_creditcard_data):
        """Test adapter normalization method."""
        csv_path, _ = mock_creditcard_data
        adapter = CreditCardAdapter(csv_path.parent)
        
        standardized_df = adapter.load()
        normalized_df = adapter.normalize(standardized_df)
        
        assert_dataframe_not_empty(normalized_df)
        assert len(normalized_df) <= len(standardized_df)  # May remove duplicates
        
        # Check data types are preserved/corrected
        assert normalized_df['is_fraud'].dtype == 'bool'
        assert normalized_df['amount'].dtype == 'float64'
    
    def test_transform_method(self, mock_creditcard_data):
        """Test adapter transformation method."""
        csv_path, _ = mock_creditcard_data
        adapter = CreditCardAdapter(csv_path.parent)
        
        standardized_df = adapter.load()
        normalized_df = adapter.normalize(standardized_df)
        transformed_df = adapter.transform(normalized_df)
        
        assert_dataframe_not_empty(transformed_df)
        assert len(transformed_df.columns) > len(normalized_df.columns)  # New features added
        
        # Check for expected new features
        assert 'amount_zscore' in transformed_df.columns
        assert 'hour_sin' in transformed_df.columns
        assert 'hour_cos' in transformed_df.columns
    
    def test_export_method(self, mock_creditcard_data, temp_directory):
        """Test adapter export method."""
        csv_path, _ = mock_creditcard_data
        adapter = CreditCardAdapter(csv_path.parent)
        
        standardized_df = adapter.load()
        
        # Test different export formats
        for format in ['parquet', 'csv', 'feather']:
            output_path = adapter.export(standardized_df, temp_directory, format=format)
            
            assert output_path.exists()
            assert output_path.suffix == f'.{format}'
            
            # Verify we can read the exported file back
            if format == 'parquet':
                reloaded = pd.read_parquet(output_path)
            elif format == 'csv':
                reloaded = pd.read_csv(output_path)
            elif format == 'feather':
                reloaded = pd.read_feather(output_path)
            
            assert len(reloaded) == len(standardized_df)


class TestIEEECISAdapter:
    """Tests for IEEE-CIS dataset adapter."""
    
    @pytest.fixture
    def mock_ieee_cis_data(self, temp_directory):
        """Create mock IEEE-CIS dataset."""
        n_rows = 1000
        
        # Transaction data
        transaction_data = {
            'TransactionID': range(1, n_rows + 1),
            'isFraud': np.random.choice([0, 1], n_rows, p=[0.97, 0.03]),  # 3% fraud rate
            'TransactionDT': np.random.randint(1, 1000000, n_rows),
            'TransactionAmt': np.random.lognormal(4, 1, n_rows).round(2),
            'ProductCD': np.random.choice(['W', 'C', 'R', 'H', 'S'], n_rows),
            'card1': np.random.randint(1000, 9999, n_rows),
            'card2': np.random.choice([100, 200, 300, 400, 500], n_rows),
            'card3': np.random.choice([100, 150, 185], n_rows),
            'card4': np.random.choice(['visa', 'mastercard', 'american express'], n_rows),
            'card5': np.random.choice([100, 200, 300], n_rows),
            'card6': np.random.choice(['credit', 'debit'], n_rows),
            'addr1': np.random.randint(100, 999, n_rows),
            'addr2': np.random.randint(10, 99, n_rows),
            'dist1': np.random.uniform(0, 100, n_rows),
            'dist2': np.random.uniform(0, 50, n_rows),
        }
        
        # Add some C, D, M, V features
        for i in range(1, 6):  # C1-C5
            transaction_data[f'C{i}'] = np.random.randint(0, 10, n_rows)
        
        for i in range(1, 6):  # D1-D5
            transaction_data[f'D{i}'] = np.random.uniform(0, 1000, n_rows)
        
        for i in range(1, 4):  # M1-M3
            transaction_data[f'M{i}'] = np.random.choice(['T', 'F', None], n_rows, p=[0.3, 0.3, 0.4])
        
        for i in range(1, 11):  # V1-V10
            transaction_data[f'V{i}'] = np.random.normal(0, 1, n_rows)
        
        transaction_df = pd.DataFrame(transaction_data)
        
        # Identity data (subset of transactions)
        identity_ids = np.random.choice(transaction_df['TransactionID'], size=n_rows//2, replace=False)
        identity_data = {
            'TransactionID': identity_ids,
            'id_01': np.random.uniform(0, 1, len(identity_ids)),
            'id_02': np.random.uniform(0, 100, len(identity_ids)),
            'DeviceType': np.random.choice(['desktop', 'mobile'], len(identity_ids)),
            'DeviceInfo': np.random.choice(['Windows', 'iOS', 'Android'], len(identity_ids)),
        }
        
        identity_df = pd.DataFrame(identity_data)
        
        # Save to CSV files
        train_transaction_path = temp_directory / "train_transaction.csv"
        train_identity_path = temp_directory / "train_identity.csv"
        
        transaction_df.to_csv(train_transaction_path, index=False)
        identity_df.to_csv(train_identity_path, index=False)
        
        return train_transaction_path, train_identity_path, transaction_df, identity_df
    
    def test_load_raw_data(self, mock_ieee_cis_data):
        """Test loading raw IEEE-CIS data."""
        train_trans_path, train_id_path, expected_trans, expected_id = mock_ieee_cis_data
        adapter = IEEECISAdapter(train_trans_path.parent)
        
        raw_df = adapter.load_raw_data()
        
        assert_dataframe_not_empty(raw_df)
        
        # Should have merged transaction and identity data
        assert len(raw_df) == len(expected_trans)  # Same number of transactions
        
        # Should have columns from both transaction and identity data
        trans_cols = set(expected_trans.columns)
        id_cols = set(expected_id.columns) - {'TransactionID'}  # Exclude join key
        
        expected_cols = trans_cols | id_cols
        assert expected_cols.issubset(set(raw_df.columns))
    
    def test_load_raw_data_transaction_only(self, mock_ieee_cis_data):
        """Test loading when only transaction file exists."""
        train_trans_path, train_id_path, expected_trans, _ = mock_ieee_cis_data
        
        # Remove identity file
        train_id_path.unlink()
        
        adapter = IEEECISAdapter(train_trans_path.parent)
        raw_df = adapter.load_raw_data()
        
        assert_dataframe_not_empty(raw_df)
        assert len(raw_df) == len(expected_trans)
        assert set(raw_df.columns) == set(expected_trans.columns)
    
    def test_load_raw_data_file_not_found(self, temp_directory):
        """Test error handling when transaction file not found."""
        adapter = IEEECISAdapter(temp_directory)
        
        with pytest.raises(FileNotFoundError) as exc_info:
            adapter.load_raw_data()
        
        assert "train_transaction.csv" in str(exc_info.value)
    
    def test_map_to_standard_schema(self, mock_ieee_cis_data):
        """Test mapping IEEE-CIS to standard schema."""
        train_trans_path, _, _, _ = mock_ieee_cis_data
        adapter = IEEECISAdapter(train_trans_path.parent)
        
        raw_df = adapter.load_raw_data()
        standardized_df = adapter.map_to_standard_schema(raw_df)
        
        # Check required standard columns
        required_cols = ['transaction_id', 'timestamp', 'amount', 'is_fraud']
        assert_dataframe_schema(
            standardized_df,
            required_cols,
            expected_dtypes={
                'amount': 'float64', 
                'is_fraud': 'bool'
            }
        )
        
        # Check IEEE-CIS specific features are mapped
        assert 'product_code' in standardized_df.columns
        
        # Check card features
        card_cols = [col for col in standardized_df.columns if col.startswith('card_')]
        assert len(card_cols) > 0
        
        # Check feature mappings
        count_cols = [col for col in standardized_df.columns if col.startswith('count_feature_')]
        timedelta_cols = [col for col in standardized_df.columns if col.startswith('timedelta_feature_')]
        vesta_cols = [col for col in standardized_df.columns if col.startswith('vesta_feature_')]
        
        assert len(count_cols) > 0  # C features
        assert len(timedelta_cols) > 0  # D features 
        assert len(vesta_cols) > 0  # V features
    
    def test_get_schema_mapping(self, temp_directory):
        """Test IEEE-CIS schema mapping."""
        adapter = IEEECISAdapter(temp_directory)
        mapping = adapter.get_schema_mapping()
        
        assert isinstance(mapping, dict)
        assert mapping['transaction_id'] == 'TransactionID'
        assert mapping['amount'] == 'TransactionAmt'
        assert mapping['is_fraud'] == 'isFraud'
        assert mapping['product_code'] == 'ProductCD'
        
        # Check feature mappings
        assert mapping['count_feature_1'] == 'C1'
        assert mapping['timedelta_feature_1'] == 'D1'
        assert mapping['vesta_feature_001'] == 'V1'
    
    def test_full_load_process(self, mock_ieee_cis_data):
        """Test complete IEEE-CIS load process."""
        train_trans_path, _, _, _ = mock_ieee_cis_data
        adapter = IEEECISAdapter(train_trans_path.parent)
        
        standardized_df = adapter.load()
        
        # Check adapter state
        assert adapter.raw_df is not None
        assert adapter.metadata is not None
        
        # Validate metadata
        assert_metadata_valid(adapter.metadata, ['dataset_name', 'fraud_rate', 'num_records'])
        assert adapter.metadata.dataset_type == DatasetType.IEEE_CIS
        
        # Check dataset structure
        assert_dataframe_not_empty(standardized_df)
        required_cols = ['transaction_id', 'timestamp', 'amount', 'is_fraud']
        for col in required_cols:
            assert col in standardized_df.columns
    
    def test_validate_method(self, mock_ieee_cis_data):
        """Test IEEE-CIS validation method."""
        train_trans_path, _, _, _ = mock_ieee_cis_data
        adapter = IEEECISAdapter(train_trans_path.parent)
        
        standardized_df = adapter.load()
        validation_results = adapter.validate(standardized_df)
        
        assert isinstance(validation_results, dict)
        assert 'schema_valid' in validation_results
        assert 'statistics' in validation_results
        
        stats = validation_results['statistics']
        assert 'unique_customers' in stats
        assert 'unique_merchants' in stats
        assert 'date_range' in stats


class TestAdapterIntegration:
    """Integration tests for adapter functionality."""
    
    def test_adapters_produce_compatible_schemas(self, temp_directory):
        """Test that both adapters produce compatible standardized schemas."""
        # Create mock data for both adapters
        mock_gen = MockDatasetGenerator(seed=42)
        
        # Generate CreditCard-like data
        cc_data = pd.DataFrame({
            'Time': np.linspace(0, 172800, 500),
            'Amount': np.random.lognormal(3, 1, 500),
            'Class': np.random.choice([0, 1], 500, p=[0.998, 0.002]),
            **{f'V{i}': np.random.normal(0, 1, 500) for i in range(1, 29)}
        })
        
        cc_path = temp_directory / "creditcard"
        cc_path.mkdir()
        cc_data.to_csv(cc_path / "creditcard.csv", index=False)
        
        # Generate IEEE-CIS-like data
        ieee_data = pd.DataFrame({
            'TransactionID': range(1, 501),
            'isFraud': np.random.choice([0, 1], 500, p=[0.97, 0.03]),
            'TransactionDT': np.random.randint(1, 1000000, 500),
            'TransactionAmt': np.random.lognormal(4, 1, 500),
            'ProductCD': np.random.choice(['W', 'C', 'R'], 500),
            'card1': np.random.randint(1000, 9999, 500),
            'addr1': np.random.randint(100, 999, 500),
        })
        
        ieee_path = temp_directory / "ieee_cis"
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
        
        # Check compatible data types
        for col in required_cols:
            cc_dtype = cc_df[col].dtype
            ieee_dtype = ieee_df[col].dtype
            
            # Should have compatible types (not necessarily identical)
            if col == 'amount':
                assert pd.api.types.is_numeric_dtype(cc_dtype)
                assert pd.api.types.is_numeric_dtype(ieee_dtype)
            elif col == 'is_fraud':
                assert pd.api.types.is_bool_dtype(cc_dtype) or pd.api.types.is_integer_dtype(cc_dtype)
                assert pd.api.types.is_bool_dtype(ieee_dtype) or pd.api.types.is_integer_dtype(ieee_dtype)
    
    def test_adapter_error_handling(self, temp_directory):
        """Test adapter error handling with invalid data."""
        # Create invalid CreditCard data (missing Class column)
        invalid_cc_data = pd.DataFrame({
            'Time': [1, 2, 3],
            'Amount': [10, 20, 30],
            # Missing Class and V columns
        })
        
        cc_path = temp_directory / "creditcard.csv"
        invalid_cc_data.to_csv(cc_path, index=False)
        
        adapter = CreditCardAdapter(cc_path.parent)
        
        with pytest.raises(ValueError):
            adapter.load_raw_data()
    
    @pytest.mark.parametrize("export_format", ["parquet", "csv", "feather"])
    def test_export_formats(self, temp_directory, export_format):
        """Test export functionality with different formats."""
        # Create minimal test data
        test_data = pd.DataFrame({
            'transaction_id': ['T1', 'T2', 'T3'],
            'timestamp': pd.date_range('2024-01-01', periods=3),
            'amount': [10.0, 20.0, 30.0],
            'is_fraud': [False, True, False]
        })
        
        adapter = CreditCardAdapter(temp_directory)
        output_path = adapter.export(test_data, temp_directory, format=export_format)
        
        assert output_path.exists()
        assert output_path.suffix == f'.{export_format}'
        
        # Verify data integrity by reading back
        if export_format == 'parquet':
            reloaded = pd.read_parquet(output_path)
        elif export_format == 'csv':
            reloaded = pd.read_csv(output_path, parse_dates=['timestamp'])
        elif export_format == 'feather':
            reloaded = pd.read_feather(output_path)
        
        assert len(reloaded) == len(test_data)
        assert list(reloaded.columns) == list(test_data.columns)