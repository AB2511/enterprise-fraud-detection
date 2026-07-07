"""
Test fixtures for ML Training tests.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil
from typing import Tuple

from ml.training.base import TrainingConfig
from ml.training.tracking import LocalTracker
from ml.training.registry import ModelRegistry


@pytest.fixture
def sample_fraud_data() -> pd.DataFrame:
    """Create sample fraud detection dataset for testing."""
    np.random.seed(42)
    n_samples = 1000
    
    # Generate features
    data = {
        'amount': np.random.exponential(100, n_samples),
        'hour': np.random.randint(0, 24, n_samples),
        'day_of_week': np.random.randint(0, 7, n_samples),
        'merchant_category': np.random.choice(['grocery', 'gas', 'restaurant', 'online'], n_samples),
        'customer_age': np.random.randint(18, 80, n_samples),
        'transaction_count_1d': np.random.poisson(5, n_samples),
        'amount_std_7d': np.random.exponential(50, n_samples),
        'is_weekend': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        'velocity_1h': np.random.exponential(2, n_samples),
        'distance_from_home': np.random.exponential(10, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Create fraud labels (10% fraud rate)
    fraud_probability = (
        0.01 +  # Base rate
        0.1 * (df['amount'] > df['amount'].quantile(0.95)) +  # High amounts
        0.05 * (df['hour'].isin([2, 3, 4])) +  # Late night
        0.03 * (df['velocity_1h'] > 5) +  # High velocity
        0.02 * (df['distance_from_home'] > 50)  # Far from home
    )
    
    df['is_fraud'] = np.random.binomial(1, fraud_probability.clip(0, 1), n_samples)
    
    return df


@pytest.fixture
def sample_training_config() -> TrainingConfig:
    """Create sample training configuration."""
    return TrainingConfig(
        model_name="test_model",
        model_version="1.0.0",
        target_column="is_fraud",
        test_size=0.2,
        validation_size=0.15,
        random_seed=42,
        use_cross_validation=True,
        cv_folds=3,  # Reduced for faster tests
        early_stopping=False,
        save_model=True,
        save_predictions=True
    )


@pytest.fixture
def temp_dir():
    """Create temporary directory for test artifacts."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def local_tracker(temp_dir):
    """Create local experiment tracker for testing."""
    tracker_dir = temp_dir / "experiments"
    return LocalTracker("test_experiment", tracker_dir)


@pytest.fixture
def model_registry(temp_dir):
    """Create model registry for testing."""
    registry_dir = temp_dir / "registry"
    return ModelRegistry(registry_dir)


@pytest.fixture
def train_val_test_split(sample_fraud_data) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split sample data into train/val/test sets."""
    from sklearn.model_selection import train_test_split
    
    # First split: train+val vs test
    train_val, test = train_test_split(
        sample_fraud_data, 
        test_size=0.2, 
        random_state=42, 
        stratify=sample_fraud_data['is_fraud']
    )
    
    # Second split: train vs val
    train, val = train_test_split(
        train_val, 
        test_size=0.1875,  # 0.15 / 0.8 
        random_state=42, 
        stratify=train_val['is_fraud']
    )
    
    return train, val, test


@pytest.fixture
def sample_predictions():
    """Create sample predictions for evaluation tests."""
    np.random.seed(42)
    n_samples = 100
    
    y_true = np.random.binomial(1, 0.1, n_samples)  # 10% fraud rate
    
    # Generate correlated predictions (better than random)
    fraud_mask = y_true == 1
    y_pred_proba = np.random.beta(2, 8, n_samples)  # Skewed toward 0
    y_pred_proba[fraud_mask] = np.random.beta(4, 2, sum(fraud_mask))  # Higher for fraud
    
    y_pred = (y_pred_proba > 0.5).astype(int)
    
    return y_true, y_pred, y_pred_proba