#!/usr/bin/env python3
"""
Feature Engineering Test Runner

Comprehensive test runner for the feature engineering framework.
Tests all components including transformers, registry, store, and pipeline integration.
"""

import sys
import traceback
from pathlib import Path
import tempfile
import shutil
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))


def create_test_data():
    """Create comprehensive test dataset."""
    np.random.seed(42)
    n_rows = 200
    
    base_time = datetime(2024, 1, 1)
    timestamps = [base_time + timedelta(hours=i*0.5) for i in range(n_rows)]
    
    data = {
        # Core fields
        'transaction_id': [f'txn_{i:06d}' for i in range(n_rows)],
        'timestamp': timestamps,
        'amount': np.random.lognormal(mean=4, sigma=1, size=n_rows),
        'is_fraud': np.random.choice([0, 1], n_rows, p=[0.95, 0.05]),
        
        # Entity fields
        'customer_id': [f'cust_{i//20:03d}' for i in range(n_rows)],  # 10 customers
        'merchant_id': [f'merch_{i//40:03d}' for i in range(n_rows)],  # 5 merchants
        'device_id': [f'dev_{i//50:03d}' for i in range(n_rows)],  # 4 devices
        
        # Geographic fields
        'country': np.random.choice(['US', 'CA', 'UK', 'FR', 'DE'], n_rows),
        'billing_country': np.random.choice(['US', 'CA', 'UK', 'FR', 'DE'], n_rows),
        
        # Device fields
        'browser': np.random.choice(['Chrome', 'Firefox', 'Safari', 'Edge'], n_rows),
        'os': np.random.choice(['Windows', 'Mac', 'Linux', 'iOS', 'Android'], n_rows),
        
        # Optional fields for testing
        'birthdate': pd.to_datetime('1990-01-01') - pd.to_timedelta(np.random.randint(0, 365*30, n_rows), unit='D'),
    }
    
    return pd.DataFrame(data)


def test_base_transformer():
    """Test base transformer functionality."""
    print("🔍 Testing BaseFeatureTransformer...")
    
    try:
        from ml.features.transformers.base import BaseFeatureTransformer, FeatureMetadata, ValidationResult
        
        # Test metadata creation
        metadata = FeatureMetadata(
            name="test_transformer",
            version="1.0.0", 
            description="Test transformer",
            dependencies=["amount"]
        )
        
        assert metadata.name == "test_transformer"
        assert metadata.version == "1.0.0"
        print("  ✅ Base transformer classes work")
        return True
        
    except Exception as e:
        print(f"  ❌ Base transformer test failed: {e}")
        traceback.print_exc()
        return False


def test_transaction_transformers():
    """Test transaction feature transformers."""
    print("\n🔍 Testing Transaction Transformers...")
    
    try:
        from ml.features.transformers.transaction import (
            AmountTransformer, AmountBucketTransformer, AmountPercentileTransformer
        )
        
        test_data = create_test_data()
        
        # Test AmountTransformer
        amount_transformer = AmountTransformer()
        result = amount_transformer.fit_transform(test_data)
        
        expected_features = ['amount', 'log_amount', 'normalized_amount']
        for feature in expected_features:
            assert feature in result.columns
        
        print("  ✅ AmountTransformer works")
        
        # Test AmountBucketTransformer
        bucket_transformer = AmountBucketTransformer(n_buckets=5)
        result = bucket_transformer.fit_transform(test_data)
        
        assert 'amount_bucket' in result.columns
        bucket_cols = [col for col in result.columns if col.startswith('amount_bucket_')]
        assert len(bucket_cols) == 5
        
        print("  ✅ AmountBucketTransformer works")
        
        # Test AmountPercentileTransformer
        percentile_transformer = AmountPercentileTransformer()
        result = percentile_transformer.fit_transform(test_data)
        
        assert 'amount_percentile_rank' in result.columns
        assert (result['amount_percentile_rank'] >= 0).all()
        assert (result['amount_percentile_rank'] <= 1).all()
        
        print("  ✅ AmountPercentileTransformer works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Transaction transformers test failed: {e}")
        traceback.print_exc()
        return False


def test_temporal_transformers():
    """Test temporal feature transformers."""
    print("\n🔍 Testing Temporal Transformers...")
    
    try:
        from ml.features.transformers.temporal import TemporalTransformer, HolidayTransformer
        
        test_data = create_test_data()
        
        # Test TemporalTransformer
        temporal_transformer = TemporalTransformer()
        result = temporal_transformer.fit_transform(test_data)
        
        expected_features = [
            'hour', 'minute', 'day', 'weekday', 'month',
            'is_weekend', 'is_business_hours', 'is_night_transaction'
        ]
        
        for feature in expected_features:
            assert feature in result.columns
        
        # Check value ranges
        assert result['hour'].min() >= 0
        assert result['hour'].max() <= 23
        assert result['is_weekend'].isin([0, 1]).all()
        
        print("  ✅ TemporalTransformer works")
        
        # Test HolidayTransformer
        holiday_transformer = HolidayTransformer()
        result = holiday_transformer.fit_transform(test_data)
        
        holiday_features = ['is_holiday', 'is_holiday_period']
        for feature in holiday_features:
            assert feature in result.columns
            assert result[feature].isin([0, 1]).all()
        
        print("  ✅ HolidayTransformer works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Temporal transformers test failed: {e}")
        traceback.print_exc()
        return False


def test_customer_transformers():
    """Test customer and merchant transformers."""
    print("\n🔍 Testing Customer & Merchant Transformers...")
    
    try:
        from ml.features.transformers.customer import CustomerTransformer, MerchantTransformer
        
        test_data = create_test_data()
        
        # Test CustomerTransformer
        customer_transformer = CustomerTransformer(birthdate_column='birthdate')
        result = customer_transformer.fit_transform(test_data)
        
        expected_features = [
            'customer_age_years', 'historical_fraud_count', 'historical_fraud_rate',
            'transaction_frequency_per_day', 'customer_lifetime_value'
        ]
        
        for feature in expected_features:
            assert feature in result.columns
        
        # Check value ranges
        assert (result['historical_fraud_rate'] >= 0).all()
        assert (result['historical_fraud_rate'] <= 1).all()
        assert (result['customer_age_years'] > 0).all()
        
        print("  ✅ CustomerTransformer works")
        
        # Test MerchantTransformer
        merchant_transformer = MerchantTransformer()
        result = merchant_transformer.fit_transform(test_data)
        
        merchant_features = [
            'merchant_fraud_rate', 'merchant_volume', 'merchant_avg_amount'
        ]
        
        for feature in merchant_features:
            assert feature in result.columns
        
        assert (result['merchant_fraud_rate'] >= 0).all()
        assert (result['merchant_fraud_rate'] <= 1).all()
        
        print("  ✅ MerchantTransformer works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Customer/Merchant transformers test failed: {e}")
        traceback.print_exc()
        return False


def test_device_geographic_transformers():
    """Test device and geographic transformers."""
    print("\n🔍 Testing Device & Geographic Transformers...")
    
    try:
        from ml.features.transformers.device import DeviceTransformer, GeographicTransformer
        
        test_data = create_test_data()
        
        # Test DeviceTransformer
        device_transformer = DeviceTransformer(
            browser_column='browser',
            os_column='os'
        )
        result = device_transformer.fit_transform(test_data)
        
        device_features = [
            'device_reuse_count', 'device_customer_count', 'customer_device_count',
            'is_shared_device', 'browser_diversity_score'
        ]
        
        for feature in device_features:
            assert feature in result.columns
        
        assert (result['device_reuse_count'] >= 0).all()
        assert result['is_shared_device'].isin([0, 1]).all()
        
        print("  ✅ DeviceTransformer works")
        
        # Test GeographicTransformer
        geo_transformer = GeographicTransformer(
            billing_country_column='billing_country'
        )
        result = geo_transformer.fit_transform(test_data)
        
        geo_features = [
            'country_transaction_count', 'customer_location_count',
            'billing_country_mismatch', 'is_foreign_transaction'
        ]
        
        for feature in geo_features:
            assert feature in result.columns
        
        assert result['billing_country_mismatch'].isin([0, 1]).all()
        assert (result['customer_location_count'] >= 0).all()
        
        print("  ✅ GeographicTransformer works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Device/Geographic transformers test failed: {e}")
        traceback.print_exc()
        return False


def test_risk_transformers():
    """Test risk feature transformers."""
    print("\n🔍 Testing Risk Transformers...")
    
    try:
        from ml.features.transformers.risk import RiskTransformer
        
        test_data = create_test_data()
        
        # Test RiskTransformer
        risk_transformer = RiskTransformer()
        result = risk_transformer.fit_transform(test_data)
        
        risk_features = [
            'is_high_value_transaction', 'is_rapid_transaction',
            'is_suspicious_merchant', 'basic_risk_score', 'advanced_risk_score',
            'total_risk_flags', 'risk_category'
        ]
        
        for feature in risk_features:
            assert feature in result.columns
        
        # Check binary flags
        binary_features = ['is_high_value_transaction', 'is_rapid_transaction', 'is_suspicious_merchant']
        for feature in binary_features:
            assert result[feature].isin([0, 1]).all()
        
        # Check risk scores are bounded
        assert (result['basic_risk_score'] >= 0).all()
        assert (result['basic_risk_score'] <= 1).all()
        assert (result['advanced_risk_score'] >= 0).all()
        assert (result['advanced_risk_score'] <= 1).all()
        
        # Check risk categories
        valid_categories = ['LOW', 'MEDIUM', 'HIGH']
        assert result['risk_category'].isin(valid_categories).all()
        
        print("  ✅ RiskTransformer works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Risk transformers test failed: {e}")
        traceback.print_exc()
        return False


def test_feature_registry():
    """Test feature registry functionality."""
    print("\n🔍 Testing Feature Registry...")
    
    try:
        from ml.features.registry import FeatureRegistry
        from ml.features.transformers.transaction import AmountTransformer
        
        # Create temporary registry
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = FeatureRegistry(Path(temp_dir))
            
            # Register a transformer
            transformer = AmountTransformer()
            registry_key = registry.register_transformer(transformer)
            
            assert registry_key == f"{transformer.name}:{transformer.version()}"
            
            # Get transformer info
            info = registry.get_transformer_info(transformer.name)
            assert info is not None
            assert info.name == transformer.name
            
            # List transformers
            transformers = registry.list_transformers()
            assert len(transformers) == 1
            
            # Export feature dictionary
            feature_dict = registry.export_feature_dictionary()
            assert "transformers" in feature_dict
            assert "features" in feature_dict
            
            print("  ✅ FeatureRegistry works")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Feature registry test failed: {e}")
        traceback.print_exc()
        return False


def test_feature_store():
    """Test feature store functionality."""
    print("\n🔍 Testing Feature Store...")
    
    try:
        from ml.features.store import LocalFeatureStore
        
        test_data = create_test_data()
        
        # Create temporary store
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Store features
            feature_set_key = store.store_features(
                features_df=test_data,
                feature_set_name="test_features",
                version="v1.0.0",
                description="Test feature set"
            )
            
            assert feature_set_key == "test_features:v1.0.0"
            
            # Load features
            loaded_df, metadata = store.load_features("test_features", "v1.0.0")
            
            assert len(loaded_df) == len(test_data)
            assert list(loaded_df.columns) == list(test_data.columns)
            
            # List feature sets
            feature_sets = store.list_feature_sets()
            assert len(feature_sets) == 1
            
            # Get feature info
            info = store.get_feature_info("amount")
            assert len(info) == 1
            
            # Export catalog
            catalog = store.export_catalog()
            assert "feature_sets" in catalog
            assert "feature_index" in catalog
            
            print("  ✅ LocalFeatureStore works")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Feature store test failed: {e}")
        traceback.print_exc()
        return False


def test_feature_pipeline():
    """Test feature engineering pipeline."""
    print("\n🔍 Testing Feature Engineering Pipeline...")
    
    try:
        from ml.features.pipeline import FeatureEngineeringStage
        from ml.features.transformers import (
            AmountTransformer, TemporalTransformer, CustomerTransformer
        )
        
        test_data = create_test_data()
        
        # Create transformers
        transformers = [
            AmountTransformer(),
            TemporalTransformer(),
            CustomerTransformer(),
        ]
        
        # Create pipeline stage
        feature_stage = FeatureEngineeringStage(transformers=transformers)
        
        # Execute pipeline
        inputs = {"dataset": test_data}
        outputs = feature_stage.execute(inputs)
        
        # Check outputs
        assert "engineered_features" in outputs
        assert "feature_engineering_metadata" in outputs
        
        engineered_df = outputs["engineered_features"]
        
        # Check that features were added
        assert len(engineered_df.columns) > len(test_data.columns)
        
        # Check metadata
        metadata = outputs["feature_engineering_metadata"]
        assert metadata["n_transformers_applied"] == 3
        assert metadata["total_features_added"] > 0
        
        print("  ✅ FeatureEngineeringStage works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Feature pipeline test failed: {e}")
        traceback.print_exc()
        return False


def test_end_to_end_workflow():
    """Test complete end-to-end feature engineering workflow."""
    print("\n🔍 Testing End-to-End Workflow...")
    
    try:
        from ml.features import (
            LocalFeatureStore, FeatureRegistry, FeatureEngineeringStage,
            AmountTransformer, TemporalTransformer, CustomerTransformer, RiskTransformer
        )
        
        test_data = create_test_data()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create feature store and registry
            store = LocalFeatureStore(Path(temp_dir) / "store")
            registry = FeatureRegistry(Path(temp_dir) / "registry")
            
            # Create transformers
            transformers = [
                AmountTransformer(),
                TemporalTransformer(),
                CustomerTransformer(),
                RiskTransformer(),
            ]
            
            # Register transformers
            for transformer in transformers:
                registry.register_transformer(transformer)
            
            # Create and execute pipeline
            feature_stage = FeatureEngineeringStage(
                transformers=transformers,
                feature_registry=registry,
                feature_store=store
            )
            
            inputs = {
                "dataset": test_data,
                "feature_set_name": "complete_features"
            }
            
            outputs = feature_stage.execute(inputs)
            
            # Verify results
            engineered_features = outputs["engineered_features"]
            
            # Check that all transformer types added features
            expected_feature_types = [
                'amount', 'log_amount',  # Amount features
                'hour', 'is_weekend',   # Temporal features
                'historical_fraud_rate',  # Customer features
                'basic_risk_score',     # Risk features
            ]
            
            for feature in expected_feature_types:
                assert feature in engineered_features.columns
            
            # Check feature store integration
            feature_set_key = outputs.get("feature_set_key")
            if feature_set_key:
                # Verify features were stored
                stored_df, stored_metadata = store.load_features(
                    feature_set_key.split(":")[0],
                    feature_set_key.split(":")[1]
                )
                
                assert len(stored_df) == len(engineered_features)
            
            # Check registry integration
            registered_transformers = registry.list_transformers()
            assert len(registered_transformers) == 4
            
            print("  ✅ End-to-end workflow works")
            print(f"    Original features: {len(test_data.columns)}")
            print(f"    Final features: {len(engineered_features.columns)}")
            print(f"    Features added: {len(engineered_features.columns) - len(test_data.columns)}")
            
        return True
        
    except Exception as e:
        print(f"  ❌ End-to-end workflow test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all feature engineering tests."""
    print("🚀 Running Feature Engineering Framework Tests")
    print("=" * 60)
    
    tests = [
        ("Base Transformer", test_base_transformer),
        ("Transaction Transformers", test_transaction_transformers),
        ("Temporal Transformers", test_temporal_transformers),
        ("Customer & Merchant Transformers", test_customer_transformers),
        ("Device & Geographic Transformers", test_device_geographic_transformers),
        ("Risk Transformers", test_risk_transformers),
        ("Feature Registry", test_feature_registry),
        ("Feature Store", test_feature_store),
        ("Feature Pipeline", test_feature_pipeline),
        ("End-to-End Workflow", test_end_to_end_workflow),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"🏁 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All feature engineering tests passed!")
        print("✅ Feature engineering framework is ready for production use")
        return 0
    else:
        print(f"💥 {total - passed} tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())