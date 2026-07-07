#!/usr/bin/env python3
"""
Tests for Feature Transformers

Comprehensive test suite for all feature transformers in the fraud detection system.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
from pathlib import Path

# Import transformers
from ml.features.transformers import (
    AmountTransformer, AmountBucketTransformer, AmountPercentileTransformer,
    TemporalTransformer, HolidayTransformer,
    VelocityTransformer, RollingStatisticsTransformer,
    CustomerTransformer, MerchantTransformer,
    DeviceTransformer, GeographicTransformer,
    RiskTransformer
)


@pytest.fixture
def sample_transaction_data():
    """Create sample transaction data for testing."""
    np.random.seed(42)
    n_rows = 100
    
    # Base timestamp
    base_time = datetime(2024, 1, 1)
    timestamps = [base_time + timedelta(hours=i*0.1) for i in range(n_rows)]
    
    data = {
        'transaction_id': [f'txn_{i:06d}' for i in range(n_rows)],
        'timestamp': timestamps,
        'amount': np.random.lognormal(mean=4, sigma=1, size=n_rows),
        'customer_id': [f'cust_{i//10:03d}' for i in range(n_rows)],  # 10 customers
        'merchant_id': [f'merch_{i//20:03d}' for i in range(n_rows)],  # 5 merchants
        'device_id': [f'dev_{i//25:03d}' for i in range(n_rows)],  # 4 devices
        'country': np.random.choice(['US', 'CA', 'UK', 'FR', 'DE'], n_rows),
        'is_fraud': np.random.choice([0, 1], n_rows, p=[0.95, 0.05]),
    }
    
    return pd.DataFrame(data)


class TestAmountTransformer:
    """Test AmountTransformer."""
    
    def test_init(self):
        """Test transformer initialization."""
        transformer = AmountTransformer()
        assert transformer.name == "amount_transformer"
        assert transformer.version() == "1.0.0"
        assert not transformer.is_fitted
    
    def test_fit_transform(self, sample_transaction_data):
        """Test fit and transform functionality."""
        transformer = AmountTransformer()
        
        # Test fit
        transformer.fit(sample_transaction_data)
        assert transformer.is_fitted
        assert transformer.amount_mean_ is not None
        assert transformer.amount_std_ is not None
    
    def test_transform_creates_expected_features(self, sample_transaction_data):
        """Test that transform creates expected features."""
        transformer = AmountTransformer()
        result = transformer.fit_transform(sample_transaction_data)
        
        expected_features = ['amount', 'log_amount', 'normalized_amount']
        for feature in expected_features:
            assert feature in result.columns
        
        # Check feature properties
        assert (result['log_amount'] >= 0).all()
        assert result['normalized_amount'].mean() == pytest.approx(0, abs=1e-10)
    
    def test_validation(self, sample_transaction_data):
        """Test transformer validation."""
        transformer = AmountTransformer()
        validation_result = transformer.validation(sample_transaction_data)
        
        assert validation_result.is_valid
        assert len(validation_result.errors) == 0


class TestAmountBucketTransformer:
    """Test AmountBucketTransformer."""
    
    def test_quantile_bucketing(self, sample_transaction_data):
        """Test quantile-based bucketing."""
        transformer = AmountBucketTransformer(n_buckets=5, bucket_method="quantile")
        result = transformer.fit_transform(sample_transaction_data)
        
        # Check bucket features exist
        assert 'amount_bucket' in result.columns
        
        # Check one-hot encoded buckets
        bucket_cols = [col for col in result.columns if col.startswith('amount_bucket_')]
        assert len(bucket_cols) == 5
        
        # Check bucket values are valid
        assert result['amount_bucket'].min() >= 0
        assert result['amount_bucket'].max() < 5
    
    def test_custom_bucketing(self, sample_transaction_data):
        """Test custom threshold bucketing."""
        transformer = AmountBucketTransformer(
            bucket_method="custom",
            custom_thresholds=[10, 50, 100, 500]
        )
        result = transformer.fit_transform(sample_transaction_data)
        
        assert 'amount_bucket' in result.columns
        bucket_cols = [col for col in result.columns if col.startswith('amount_bucket_')]
        assert len(bucket_cols) == 5  # 4 thresholds + 1 = 5 buckets


class TestTemporalTransformer:
    """Test TemporalTransformer."""
    
    def test_temporal_features(self, sample_transaction_data):
        """Test temporal feature creation."""
        transformer = TemporalTransformer()
        result = transformer.fit_transform(sample_transaction_data)
        
        expected_features = [
            'hour', 'minute', 'day', 'weekday', 'month',
            'is_weekend', 'is_business_hours', 'is_night_transaction',
            'hour_sin', 'hour_cos', 'day_sin', 'day_cos',
            'month_sin', 'month_cos', 'weekday_sin', 'weekday_cos'
        ]
        
        for feature in expected_features:
            assert feature in result.columns
        
        # Check value ranges
        assert result['hour'].min() >= 0
        assert result['hour'].max() <= 23
        assert result['weekday'].min() >= 0
        assert result['weekday'].max() <= 6
        assert result['is_weekend'].isin([0, 1]).all()
    
    def test_cyclical_encodings(self, sample_transaction_data):
        """Test cyclical encodings are bounded."""
        transformer = TemporalTransformer()
        result = transformer.fit_transform(sample_transaction_data)
        
        cyclical_cols = [col for col in result.columns if col.endswith('_sin') or col.endswith('_cos')]
        
        for col in cyclical_cols:
            assert result[col].min() >= -1
            assert result[col].max() <= 1


class TestVelocityTransformer:
    """Test VelocityTransformer."""
    
    def test_velocity_features(self, sample_transaction_data):
        """Test velocity feature creation."""
        transformer = VelocityTransformer(time_windows=["1H", "24H"])
        
        # Sort data as expected by transformer
        sorted_data = sample_transaction_data.sort_values(['customer_id', 'timestamp'])
        result = transformer.fit_transform(sorted_data)
        
        expected_features = [
            'txn_count_1H', 'amount_mean_1H', 'amount_max_1H', 'amount_min_1H',
            'txn_count_24H', 'amount_mean_24H', 'amount_max_24H', 'amount_min_24H'
        ]
        
        for feature in expected_features:
            assert feature in result.columns
        
        # Check non-negative counts
        assert (result['txn_count_1H'] >= 0).all()
        assert (result['txn_count_24H'] >= 0).all()


class TestCustomerTransformer:
    """Test CustomerTransformer."""
    
    def test_customer_features(self, sample_transaction_data):
        """Test customer feature creation."""
        transformer = CustomerTransformer()
        result = transformer.fit_transform(sample_transaction_data)
        
        expected_features = [
            'historical_fraud_count', 'historical_fraud_rate',
            'transaction_frequency_per_day', 'customer_lifetime_value',
            'is_new_customer', 'is_high_frequency_customer'
        ]
        
        for feature in expected_features:
            assert feature in result.columns
        
        # Check value ranges
        assert (result['historical_fraud_rate'] >= 0).all()
        assert (result['historical_fraud_rate'] <= 1).all()
        assert (result['customer_lifetime_value'] >= 0).all()
    
    def test_customer_age_features(self, sample_transaction_data):
        """Test customer age features when birthdate is available."""
        # Add birthdate column
        data_with_birthdate = sample_transaction_data.copy()
        data_with_birthdate['birthdate'] = pd.to_datetime('1990-01-01')
        
        transformer = CustomerTransformer(birthdate_column='birthdate')
        result = transformer.fit_transform(data_with_birthdate)
        
        assert 'customer_age_years' in result.columns
        assert (result['customer_age_years'] > 0).all()


class TestRiskTransformer:
    """Test RiskTransformer."""
    
    def test_risk_features(self, sample_transaction_data):
        """Test risk feature creation."""
        transformer = RiskTransformer()
        result = transformer.fit_transform(sample_transaction_data)
        
        expected_features = [
            'is_high_value_transaction', 'is_rapid_transaction',
            'is_suspicious_merchant', 'is_foreign_transaction',
            'basic_risk_score', 'advanced_risk_score',
            'total_risk_flags', 'risk_category'
        ]
        
        for feature in expected_features:
            assert feature in result.columns
        
        # Check binary flags
        binary_features = [
            'is_high_value_transaction', 'is_rapid_transaction',
            'is_suspicious_merchant', 'is_foreign_transaction'
        ]
        for feature in binary_features:
            assert result[feature].isin([0, 1]).all()
        
        # Check risk scores are bounded
        assert (result['basic_risk_score'] >= 0).all()
        assert (result['basic_risk_score'] <= 1).all()
        assert (result['advanced_risk_score'] >= 0).all()
        assert (result['advanced_risk_score'] <= 1).all()


class TestTransformerValidation:
    """Test transformer validation functionality."""
    
    def test_missing_dependencies(self, sample_transaction_data):
        """Test validation fails with missing dependencies."""
        transformer = AmountTransformer(amount_column="missing_column")
        
        validation_result = transformer.validation(sample_transaction_data)
        assert not validation_result.is_valid
        assert len(validation_result.errors) > 0
    
    def test_empty_dataframe_validation(self):
        """Test validation fails with empty DataFrame."""
        transformer = AmountTransformer()
        empty_df = pd.DataFrame()
        
        validation_result = transformer.validation(empty_df)
        assert not validation_result.is_valid
        assert "empty" in validation_result.errors[0].lower()


class TestTransformerMetadata:
    """Test transformer metadata functionality."""
    
    def test_metadata_creation(self):
        """Test metadata is properly created."""
        transformer = AmountTransformer()
        metadata = transformer.metadata()
        
        assert metadata.name == "amount_transformer"
        assert metadata.version == "1.0.0"
        assert metadata.description != ""
        assert "amount" in metadata.dependencies
    
    def test_metadata_update_after_fit(self, sample_transaction_data):
        """Test metadata is updated after fitting."""
        transformer = AmountTransformer()
        
        # Metadata before fit
        metadata_before = transformer.metadata()
        assert metadata_before.fitted_at is None
        
        # Fit transformer
        transformer.fit(sample_transaction_data)
        
        # Metadata after fit
        metadata_after = transformer.metadata()
        assert metadata_after.fitted_at is not None
        assert len(metadata_after.statistics) > 0


class TestTransformerSerialization:
    """Test transformer serialization and deserialization."""
    
    def test_save_load_metadata(self, sample_transaction_data):
        """Test saving and loading transformer metadata."""
        transformer = AmountTransformer()
        transformer.fit(sample_transaction_data)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = Path(temp_dir) / "metadata.json"
            
            # Save metadata
            transformer.save_metadata(metadata_path)
            assert metadata_path.exists()
            
            # Create new transformer and load metadata
            new_transformer = AmountTransformer()
            new_transformer.load_metadata(metadata_path)
            
            # Check metadata is loaded
            original_metadata = transformer.metadata()
            loaded_metadata = new_transformer.metadata()
            
            assert original_metadata.name == loaded_metadata.name
            assert original_metadata.version == loaded_metadata.version


class TestTransformerChaining:
    """Test chaining multiple transformers."""
    
    def test_transformer_chain(self, sample_transaction_data):
        """Test applying multiple transformers in sequence."""
        transformers = [
            AmountTransformer(),
            TemporalTransformer(),
            CustomerTransformer(),
        ]
        
        # Apply transformers sequentially
        current_data = sample_transaction_data.copy()
        
        for transformer in transformers:
            current_data = transformer.fit_transform(current_data)
        
        # Check all expected features exist
        amount_features = ['amount', 'log_amount', 'normalized_amount']
        temporal_features = ['hour', 'weekday', 'is_weekend']
        customer_features = ['historical_fraud_rate', 'customer_lifetime_value']
        
        all_expected = amount_features + temporal_features + customer_features
        
        for feature in all_expected:
            assert feature in current_data.columns
        
        # Check data integrity
        assert len(current_data) == len(sample_transaction_data)
        assert not current_data.isnull().all().any()  # No columns are all null


if __name__ == "__main__":
    pytest.main([__file__, "-v"])