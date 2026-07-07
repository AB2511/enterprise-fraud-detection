"""
Tests for base training framework.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import joblib
from unittest.mock import Mock, patch

from ml.training.base import BaseTrainer, TrainingConfig, TrainingResult


class MockModel:
    """Mock model class that is compatible with sklearn interfaces."""
    
    def __init__(self):
        self.fitted = False
        self.n_features = None
        self.n_samples = None
        self.classes_ = np.array([0, 1])  # Required for classifier recognition
        
    def fit(self, X, y):
        """Mock fit method for sklearn compatibility."""
        self.fitted = True
        self.n_features = len(X.columns)
        self.n_samples = len(X)
        self.classes_ = np.unique(y)  # Set actual classes from data
        return self
        
    def predict(self, X):
        """Mock predict method."""
        if not self.fitted:
            raise ValueError("Model not fitted")
        return np.random.randint(0, 2, len(X))
        
    def predict_proba(self, X):
        """Mock predict_proba method."""
        if not self.fitted:
            raise ValueError("Model not fitted")
        proba = np.random.rand(len(X), 2)
        return proba / proba.sum(axis=1, keepdims=True)
    
    def get_params(self, deep=True):
        """Get parameters for sklearn compatibility."""
        return {}
    
    def set_params(self, **params):
        """Set parameters for sklearn compatibility."""
        return self
        
    @property
    def _estimator_type(self):
        """Identify this as a classifier for sklearn."""
        return "classifier"


class MockTrainer(BaseTrainer):
    """Mock trainer implementation for testing BaseTrainer."""
    
    def __init__(self, config, experiment_tracker=None, fail_fit=False):
        super().__init__(config, experiment_tracker)
        self.fail_fit = fail_fit
        self.model_fitted = False
        
    def _create_model(self):
        """Create mock model."""
        return MockModel()
        
    def _fit_model(self, X, y):
        """Fit mock model."""
        if self.fail_fit:
            raise ValueError("Mock training failure")
            
        model = self._create_model()
        model.fit(X, y)
        self.model_fitted = True
        return model
        
    def _predict(self, model, X):
        """Generate mock predictions."""
        if not model.fitted:
            raise ValueError("Model not fitted")
        return np.random.randint(0, 2, len(X))
        
    def _predict_proba(self, model, X):
        """Generate mock prediction probabilities."""
        if not model.fitted:
            raise ValueError("Model not fitted")
        proba = np.random.rand(len(X), 2)
        proba = proba / proba.sum(axis=1, keepdims=True)
        return proba
        
    def _get_feature_importance(self, model):
        """Get mock feature importance."""
        if not model.fitted:
            return None
        return {f"feature_{i}": np.random.rand() for i in range(model.n_features)}


class TestTrainingConfig:
    """Test TrainingConfig functionality."""
    
    def test_training_config_defaults(self):
        """Test default configuration values."""
        config = TrainingConfig(model_name="test_model")
        
        assert config.model_name == "test_model"
        assert config.model_version == "1.0.0"
        assert config.target_column == "is_fraud"
        assert config.test_size == 0.2
        assert config.validation_size == 0.15
        assert config.random_seed == 42
        assert config.stratify is True
        assert config.use_cross_validation is True
        assert config.cv_folds == 5
        
    def test_training_config_custom_values(self):
        """Test configuration with custom values."""
        config = TrainingConfig(
            model_name="custom_model",
            model_version="2.1.0",
            target_column="fraud_label",
            test_size=0.3,
            random_seed=123,
            use_cross_validation=False
        )
        
        assert config.model_name == "custom_model"
        assert config.model_version == "2.1.0"
        assert config.target_column == "fraud_label"
        assert config.test_size == 0.3
        assert config.random_seed == 123
        assert config.use_cross_validation is False
        
    def test_config_to_dict(self, sample_training_config):
        """Test configuration serialization to dict."""
        config_dict = sample_training_config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["model_name"] == "test_model"
        assert config_dict["random_seed"] == 42
        assert config_dict["use_cross_validation"] is True
        
    def test_config_from_dict(self):
        """Test configuration deserialization from dict."""
        config_dict = {
            "model_name": "dict_model",
            "model_version": "1.5.0",
            "random_seed": 999
        }
        
        config = TrainingConfig.from_dict(config_dict)
        
        assert config.model_name == "dict_model"
        assert config.model_version == "1.5.0"
        assert config.random_seed == 999
        # Check defaults are still applied
        assert config.target_column == "is_fraud"


class TestTrainingResult:
    """Test TrainingResult functionality."""
    
    def test_training_result_creation(self):
        """Test basic TrainingResult creation."""
        result = TrainingResult(
            run_id="test-run",
            model_name="test_model",
            model_version="1.0.0", 
            training_time=123.45,
            model={"type": "mock"}
        )
        
        assert result.run_id == "test-run"
        assert result.model_name == "test_model"
        assert result.training_time == 123.45
        assert result.model == {"type": "mock"}
        assert result.train_metrics == {}
        assert result.feature_names == []
        
    def test_training_result_to_dict(self):
        """Test result serialization (excluding large objects)."""
        result = TrainingResult(
            run_id="test-run",
            model_name="test_model",
            model_version="1.0.0",
            training_time=100.0,
            model={"large": "object"},
            train_metrics={"accuracy": 0.95},
            feature_names=["f1", "f2"]
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["run_id"] == "test-run"
        assert result_dict["train_metrics"]["accuracy"] == 0.95
        assert result_dict["feature_names"] == ["f1", "f2"]
        # Model object should not be in dict (too large)
        assert "model" not in result_dict


class TestBaseTrainer:
    """Test BaseTrainer functionality."""
    
    def test_trainer_initialization(self, sample_training_config):
        """Test trainer initialization."""
        trainer = MockTrainer(sample_training_config)
        
        assert trainer.config == sample_training_config
        assert trainer.tracker is None
        assert trainer.model is None
        assert not trainer.is_trained
        assert trainer.feature_names == []
        
    def test_trainer_with_tracker(self, sample_training_config, local_tracker):
        """Test trainer initialization with tracker."""
        trainer = MockTrainer(sample_training_config, local_tracker)
        
        assert trainer.tracker == local_tracker
        
    def test_prepare_data_default_target(self, sample_fraud_data):
        """Test data preparation with default target column."""
        config = TrainingConfig(model_name="test", target_column="is_fraud")
        trainer = MockTrainer(config)
        
        X, y = trainer.prepare_data(sample_fraud_data)
        
        assert len(X) == len(sample_fraud_data)
        assert len(y) == len(sample_fraud_data)
        assert "is_fraud" not in X.columns
        assert y.name == "is_fraud"
        assert trainer.feature_names == list(X.columns)
        
    def test_prepare_data_specific_features(self, sample_fraud_data):
        """Test data preparation with specific feature columns."""
        feature_cols = ["amount", "hour", "customer_age"]
        config = TrainingConfig(
            model_name="test", 
            target_column="is_fraud",
            feature_columns=feature_cols
        )
        trainer = MockTrainer(config)
        
        X, y = trainer.prepare_data(sample_fraud_data)
        
        assert list(X.columns) == feature_cols
        assert len(X.columns) == 3
        assert trainer.feature_names == feature_cols
        
    def test_prepare_data_missing_target(self, sample_fraud_data):
        """Test error when target column is missing."""
        config = TrainingConfig(model_name="test", target_column="missing_column")
        trainer = MockTrainer(config)
        
        with pytest.raises(ValueError, match="Target column 'missing_column' not found"):
            trainer.prepare_data(sample_fraud_data)
            
    def test_prepare_data_missing_features(self, sample_fraud_data):
        """Test error when feature columns are missing."""
        config = TrainingConfig(
            model_name="test",
            feature_columns=["existing_col", "missing_col"]
        )
        trainer = MockTrainer(config)
        
        with pytest.raises(ValueError, match="Feature columns not found"):
            trainer.prepare_data(sample_fraud_data)
            
    def test_split_data(self, sample_fraud_data, sample_training_config):
        """Test data splitting."""
        trainer = MockTrainer(sample_training_config)
        X, y = trainer.prepare_data(sample_fraud_data)
        
        X_train, X_val, X_test, y_train, y_val, y_test = trainer.split_data(X, y)
        
        # Check sizes
        total_size = len(X)
        expected_test_size = int(total_size * 0.2)
        expected_val_size = int(total_size * 0.15)
        
        assert len(X_test) == expected_test_size
        assert len(X_val) >= expected_val_size - 5  # Allow some variance due to stratification
        assert len(X_train) + len(X_val) + len(X_test) == total_size
        
        # Check no overlap
        train_idx = X_train.index
        val_idx = X_val.index
        test_idx = X_test.index
        
        assert len(set(train_idx) & set(val_idx)) == 0
        assert len(set(train_idx) & set(test_idx)) == 0
        assert len(set(val_idx) & set(test_idx)) == 0
        
    @patch('sklearn.model_selection.cross_val_score')
    def test_cross_validate(self, mock_cv_score, sample_fraud_data, sample_training_config):
        """Test cross-validation."""
        # Mock cross-validation scores
        mock_scores = np.array([0.85, 0.87, 0.83, 0.89, 0.86])
        mock_cv_score.return_value = mock_scores
        
        trainer = MockTrainer(sample_training_config)
        X, y = trainer.prepare_data(sample_fraud_data)
        
        cv_metrics = trainer.cross_validate(X, y)
        
        assert cv_metrics["cv_roc_auc_mean"] == mock_scores.mean()
        assert cv_metrics["cv_roc_auc_std"] == mock_scores.std()
        assert cv_metrics["cv_roc_auc_min"] == mock_scores.min()
        assert cv_metrics["cv_roc_auc_max"] == mock_scores.max()
        
        # Check cross_val_score was called correctly
        mock_cv_score.assert_called_once()
        args, kwargs = mock_cv_score.call_args
        assert kwargs["scoring"] == "roc_auc"
        assert kwargs["cv"].n_splits == 3  # Configured in conftest
        
    def test_cross_validate_disabled(self, sample_fraud_data):
        """Test cross-validation when disabled."""
        config = TrainingConfig(model_name="test", use_cross_validation=False)
        trainer = MockTrainer(config)
        X, y = trainer.prepare_data(sample_fraud_data)
        
        cv_metrics = trainer.cross_validate(X, y)
        
        assert cv_metrics == {}
        
    @patch('ml.training.evaluation.ModelEvaluator')
    def test_train_success(self, mock_evaluator_class, sample_fraud_data, sample_training_config, local_tracker):
        """Test successful training pipeline."""
        # Mock evaluator
        mock_evaluator = Mock()
        mock_evaluator.compute_classification_metrics.return_value = {
            "accuracy": 0.95,
            "precision": 0.90,
            "recall": 0.85,
            "f1_score": 0.87,
            "roc_auc": 0.92
        }
        mock_evaluator_class.return_value = mock_evaluator
        
        trainer = MockTrainer(sample_training_config, local_tracker)
        
        with patch.object(trainer, 'cross_validate', return_value={"cv_roc_auc_mean": 0.88}):
            result = trainer.train(sample_fraud_data)
        
        # Check result
        assert isinstance(result, TrainingResult)
        assert result.model_name == "test_model"
        assert result.training_time > 0
        assert result.model is not None
        assert result.train_metrics["accuracy"] == 0.95
        assert result.validation_metrics["accuracy"] == 0.95
        assert result.test_metrics["accuracy"] == 0.95
        assert result.cv_metrics["cv_roc_auc_mean"] == 0.88
        
        # Check trainer state
        assert trainer.is_trained
        assert trainer.model is not None
        assert len(trainer.feature_names) > 0
        
    def test_train_failure(self, sample_fraud_data, sample_training_config):
        """Test training failure handling."""
        # Disable cross-validation to avoid mock model compatibility issues
        sample_training_config.use_cross_validation = False
        trainer = MockTrainer(sample_training_config, fail_fit=True)
        
        with pytest.raises(ValueError, match="Mock training failure"):
            trainer.train(sample_fraud_data)
            
    def test_save_load_model_pickle(self, sample_fraud_data, sample_training_config, temp_dir):
        """Test model saving and loading with pickle."""
        trainer = MockTrainer(sample_training_config)
        
        # Train model
        with patch('ml.training.evaluation.ModelEvaluator'):
            trainer.train(sample_fraud_data)
        
        # Save model
        model_path = temp_dir / "test_model.pkl"
        saved_path = trainer.save_model(model_path, format="pickle")
        
        assert saved_path == model_path
        assert model_path.exists()
        
        # Load model
        new_trainer = MockTrainer(sample_training_config)
        loaded_model = new_trainer.load_model(model_path, format="pickle")
        
        assert loaded_model.fitted is True
        assert new_trainer.is_trained
        
    def test_save_load_model_joblib(self, sample_fraud_data, sample_training_config, temp_dir):
        """Test model saving and loading with joblib."""
        trainer = MockTrainer(sample_training_config)
        
        # Train model
        with patch('ml.training.evaluation.ModelEvaluator'):
            trainer.train(sample_fraud_data)
        
        # Save model
        model_path = temp_dir / "test_model.joblib"
        saved_path = trainer.save_model(model_path, format="joblib")
        
        assert saved_path == model_path
        assert model_path.exists()
        
        # Load model
        new_trainer = MockTrainer(sample_training_config)
        loaded_model = new_trainer.load_model(model_path, format="joblib")
        
        assert loaded_model.fitted is True
        assert new_trainer.is_trained
        
    def test_save_model_not_trained(self, sample_training_config, temp_dir):
        """Test error when saving untrained model."""
        trainer = MockTrainer(sample_training_config)
        model_path = temp_dir / "model.pkl"
        
        with pytest.raises(ValueError, match="Model must be trained before saving"):
            trainer.save_model(model_path)
            
    def test_load_model_file_not_found(self, sample_training_config, temp_dir):
        """Test error when loading non-existent model."""
        trainer = MockTrainer(sample_training_config)
        model_path = temp_dir / "nonexistent.pkl"
        
        with pytest.raises(FileNotFoundError, match="Model file not found"):
            trainer.load_model(model_path)
            
    def test_unsupported_format(self, sample_fraud_data, sample_training_config, temp_dir):
        """Test error with unsupported format."""
        trainer = MockTrainer(sample_training_config)
        
        with patch('ml.training.evaluation.ModelEvaluator'):
            trainer.train(sample_fraud_data)
        
        model_path = temp_dir / "model.unknown"
        
        # Test unsupported save format
        with pytest.raises(ValueError, match="Unsupported format"):
            trainer.save_model(model_path, format="unknown")
            
        # Test unsupported load format - create a dummy file first
        dummy_file = temp_dir / "dummy.unknown"
        dummy_file.write_text("dummy content")
        
        with pytest.raises(ValueError, match="Unsupported format"):
            trainer.load_model(dummy_file, format="unknown")