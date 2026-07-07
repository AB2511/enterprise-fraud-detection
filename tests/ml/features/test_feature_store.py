#!/usr/bin/env python3
"""
Tests for Feature Store

Test suite for the local feature store implementation.
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
from pathlib import Path
from datetime import datetime

from ml.features.store import LocalFeatureStore, FeatureSetMetadata


@pytest.fixture
def sample_features():
    """Create sample feature data for testing."""
    np.random.seed(42)
    n_rows = 50
    
    data = {
        'transaction_id': [f'txn_{i:06d}' for i in range(n_rows)],
        'amount': np.random.lognormal(mean=3, sigma=1, size=n_rows),
        'log_amount': np.random.normal(3, 1, n_rows),
        'normalized_amount': np.random.normal(0, 1, n_rows),
        'hour': np.random.randint(0, 24, n_rows),
        'is_weekend': np.random.choice([0, 1], n_rows),
        'customer_fraud_rate': np.random.uniform(0, 0.1, n_rows),
        'is_fraud': np.random.choice([0, 1], n_rows, p=[0.9, 0.1]),
    }
    
    return pd.DataFrame(data)


class TestLocalFeatureStore:
    """Test LocalFeatureStore."""
    
    def test_initialization(self):
        """Test feature store initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            assert store.store_path.exists()
            assert (store.store_path / "features").exists()
            assert (store.store_path / "metadata").exists()
            assert (store.store_path / "statistics").exists()
    
    def test_store_features_parquet(self, sample_features):
        """Test storing features in Parquet format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            feature_set_key = store.store_features(
                features_df=sample_features,
                feature_set_name="test_features",
                version="v1.0.0",
                description="Test feature set",
                format="parquet"
            )
            
            assert feature_set_key == "test_features:v1.0.0"
            assert feature_set_key in store.feature_sets
            
            metadata = store.feature_sets[feature_set_key]
            assert metadata.name == "test_features"
            assert metadata.version == "v1.0.0"
            assert metadata.n_records == len(sample_features)
            assert metadata.n_features == len(sample_features.columns)
    
    def test_store_features_csv(self, sample_features):
        """Test storing features in CSV format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            feature_set_key = store.store_features(
                features_df=sample_features,
                feature_set_name="test_features_csv",
                format="csv"
            )
            
            # Check file exists
            csv_file = store.store_path / "features" / f"test_features_csv_{feature_set_key.split(':')[1]}.csv"
            assert csv_file.exists()
    
    def test_load_features(self, sample_features):
        """Test loading features from store."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Store features
            feature_set_key = store.store_features(
                features_df=sample_features,
                feature_set_name="test_features",
                version="v1.0.0"
            )
            
            # Load features
            loaded_df, metadata = store.load_features("test_features", "v1.0.0")
            
            assert len(loaded_df) == len(sample_features)
            assert list(loaded_df.columns) == list(sample_features.columns)
            assert metadata.name == "test_features"
            
            # Check data integrity
            pd.testing.assert_frame_equal(loaded_df, sample_features, check_dtype=False)
    
    def test_load_specific_features(self, sample_features):
        """Test loading specific features from store."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Store features
            store.store_features(
                features_df=sample_features,
                feature_set_name="test_features",
                version="v1.0.0"
            )
            
            # Load specific features
            selected_features = ['amount', 'hour', 'is_fraud']
            loaded_df, metadata = store.load_features(
                "test_features", 
                "v1.0.0", 
                features=selected_features
            )
            
            assert list(loaded_df.columns) == selected_features
            assert len(loaded_df) == len(sample_features)
    
    def test_list_feature_sets(self, sample_features):
        """Test listing feature sets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Store multiple feature sets
            store.store_features(sample_features, "features_v1", "1.0.0")
            store.store_features(sample_features, "features_v2", "1.0.0") 
            store.store_features(sample_features, "features_v1", "1.1.0")
            
            # List all feature sets
            feature_sets = store.list_feature_sets()
            assert len(feature_sets) == 3
            
            # Filter by pattern
            v1_feature_sets = store.list_feature_sets(pattern="v1")
            assert len(v1_feature_sets) == 2
    
    def test_get_feature_info(self, sample_features):
        """Test getting feature information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Store features
            store.store_features(
                sample_features, 
                "test_features", 
                "v1.0.0",
                source_dataset="test_dataset"
            )
            
            # Get feature info
            info = store.get_feature_info("amount")
            assert len(info) == 1
            assert info[0]["feature_set_name"] == "test_features"
            assert info[0]["source_dataset"] == "test_dataset"
    
    def test_delete_feature_set(self, sample_features):
        """Test deleting feature sets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Store features
            store.store_features(sample_features, "test_features", "v1.0.0")
            store.store_features(sample_features, "test_features", "v1.1.0")
            
            # Delete specific version
            store.delete_feature_set("test_features", "v1.0.0")
            
            feature_sets = store.list_feature_sets()
            feature_set_names = [f"{fs.name}:{fs.version}" for fs in feature_sets]
            assert "test_features:v1.0.0" not in feature_set_names
            assert "test_features:v1.1.0" in feature_set_names
            
            # Delete all versions
            store.delete_feature_set("test_features")
            
            feature_sets = store.list_feature_sets()
            assert len(feature_sets) == 0
    
    def test_get_statistics(self, sample_features):
        """Test getting feature statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Store features
            store.store_features(sample_features, "test_features", "v1.0.0")
            
            # Get statistics
            stats = store.get_statistics("test_features", "v1.0.0")
            
            assert "n_records" in stats
            assert "n_features" in stats
            assert "memory_usage_mb" in stats
            assert "missing_values" in stats
            assert "numeric_features" in stats
            assert stats["n_records"] == len(sample_features)
    
    def test_update_statistics(self, sample_features):
        """Test updating feature statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Store features
            feature_set_key = store.store_features(sample_features, "test_features", "v1.0.0")
            
            # Update statistics
            new_stats = {"custom_metric": 0.85, "quality_score": 0.92}
            store.update_statistics("test_features", "v1.0.0", new_stats)
            
            # Check updated statistics
            updated_stats = store.get_statistics("test_features", "v1.0.0")
            assert updated_stats["custom_metric"] == 0.85
            assert updated_stats["quality_score"] == 0.92
    
    def test_export_catalog(self, sample_features):
        """Test exporting feature catalog."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Store multiple feature sets
            store.store_features(sample_features, "features_a", "v1.0.0")
            store.store_features(sample_features, "features_b", "v1.0.0")
            
            # Export catalog
            catalog = store.export_catalog()
            
            assert "metadata" in catalog
            assert "feature_sets" in catalog
            assert "feature_index" in catalog
            
            assert catalog["metadata"]["n_feature_sets"] == 2
            assert len(catalog["feature_sets"]) == 2
            
            # Check feature index
            assert "amount" in catalog["feature_index"]
            assert len(catalog["feature_index"]["amount"]) == 2  # In both feature sets
    
    def test_auto_version_generation(self, sample_features):
        """Test automatic version generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Store without specifying version
            feature_set_key = store.store_features(
                sample_features, 
                "test_features"
            )
            
            # Check version was generated
            assert ":" in feature_set_key
            name, version = feature_set_key.split(":", 1)
            assert name == "test_features"
            assert version.startswith("v")
    
    def test_checksum_verification(self, sample_features):
        """Test checksum verification during load."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Store features
            feature_set_key = store.store_features(sample_features, "test_features", "v1.0.0")
            
            # Load and verify checksum matches
            loaded_df, metadata = store.load_features("test_features", "v1.0.0")
            
            # Checksums should match for unmodified data
            original_checksum = store.feature_sets[feature_set_key].checksum
            current_checksum = store._compute_dataframe_checksum(loaded_df)
            assert original_checksum == current_checksum
    
    def test_latest_version_loading(self, sample_features):
        """Test loading latest version when version not specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Store multiple versions
            store.store_features(sample_features, "test_features", "v1.0.0")
            store.store_features(sample_features, "test_features", "v1.1.0")
            store.store_features(sample_features, "test_features", "v2.0.0")
            
            # Load latest version
            loaded_df, metadata = store.load_features("test_features")
            
            # Should load v2.0.0 (latest)
            assert metadata.version == "v2.0.0"
    
    def test_error_handling(self, sample_features):
        """Test error handling for various scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalFeatureStore(Path(temp_dir))
            
            # Test empty DataFrame
            with pytest.raises(ValueError, match="empty"):
                store.store_features(pd.DataFrame(), "empty_features")
            
            # Test loading non-existent feature set
            with pytest.raises(ValueError, match="not found"):
                store.load_features("non_existent", "v1.0.0")
            
            # Test loading with missing features
            store.store_features(sample_features, "test_features", "v1.0.0")
            with pytest.raises(ValueError, match="not found"):
                store.load_features("test_features", "v1.0.0", features=["missing_feature"])
    
    def test_persistence_across_instances(self, sample_features):
        """Test that feature store persists data across instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # First instance - store features
            store1 = LocalFeatureStore(Path(temp_dir))
            feature_set_key = store1.store_features(sample_features, "persistent_features", "v1.0.0")
            
            # Second instance - should load existing data
            store2 = LocalFeatureStore(Path(temp_dir))
            
            # Check feature set exists in new instance
            assert feature_set_key in store2.feature_sets
            
            # Load features from new instance
            loaded_df, metadata = store2.load_features("persistent_features", "v1.0.0")
            pd.testing.assert_frame_equal(loaded_df, sample_features, check_dtype=False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])