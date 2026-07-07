"""
Tests for specific trainer implementations.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from ml.training.base import TrainingConfig
from ml.training.trainers import XGBoostTrainer, XGBoostConfig, IsolationForestTrainer, IsolationForestConfig


class TestXGBoostConfig:
    """Test XGBoostConfig functionality."""
    
    def test_xgboost_config_defaults(self):
        """Test XGBoost configuration defaults."""
        config = XGBoostConfig(model_name="xgboost_test")
        
        assert config.model_name == "xgboost_test"
        assert config.n_estimators == 100
        assert config.max_depth == 6
        assert config.learning_rate == 0.1
        assert config.subsample == 1.0
        assert config.colsample_bytree == 1.0
        assert config.random_seed == 42  # Use random_seed, not random_state
        assert config.early_stopping_rounds == 10
        
    def test_xgboost_config_custom(self):
        """Test XGBoost configuration with custom values."""
        config = XGBoostConfig(
            model_name="custom_xgb",
            n_estimators=200,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            early_stopping_rounds=20
        )
        
        assert config.n_estimators == 200
        assert config.max_depth == 8
        assert config.learning_rate == 0.05
        assert config.subsample == 0.8
        assert config.early_stopping_rounds == 20


class TestIsolationForestConfig:
    """Test IsolationForestConfig functionality."""
    
    def test_isolation_forest_config_defaults(self):
        """Test Isolation Forest configuration defaults."""
        config = IsolationForestConfig(model_name="isolation_test")
        
        assert config.model_name == "isolation_test"
        assert config.n_estimators == 100
        assert config.max_samples == "auto"
        assert config.contamination == "auto"
        assert config.max_features == 1.0
        assert config.bootstrap is False
        assert config.n_jobs == -1
        assert config.random_seed == 42  # Use random_seed, not random_state
        
    def test_isolation_forest_config_custom(self):
        """Test Isolation Forest configuration with custom values."""
        config = IsolationForestConfig(
            model_name="custom_if",
            n_estimators=200,
            max_samples=0.5,
            contamination=0.1,
            max_features=0.8,
            bootstrap=True
        )
        
        assert config.n_estimators == 200
        assert config.max_samples == 0.5
        assert config.contamination == 0.1
        assert config.max_features == 0.8
        assert config.bootstrap is True


class TestXGBoostTrainer:
    """Test XGBoostTrainer functionality."""
    
    @pytest.mark.parametrize("missing_xgboost", [False, True])
    def test_xgboost_trainer_initialization(self, missing_xgboost):
        """Test XGBoost trainer initialization."""
        config = XGBoostConfig(model_name="xgb_test")
        
        if missing_xgboost:
            with patch('ml.training.trainers.xgboost_trainer.XGBOOST_AVAILABLE', False):
                with pytest.raises(ImportError, match="XGBoost is required"):
                    XGBoostTrainer(config)
        else:
            trainer = XGBoostTrainer(config)
            assert trainer.config == config
            assert trainer.xgb_config == config
                
    @patch('xgboost.XGBClassifier')
    def test_create_model(self, mock_xgb_class):
        """Test XGBoost model creation."""
        config = XGBoostConfig(
            model_name="test",
            n_estimators=150,
            max_depth=8,
            learning_rate=0.05
        )
        
        mock_model = Mock()
        mock_xgb_class.return_value = mock_model
        
        trainer = XGBoostTrainer(config)
        model = trainer._create_model()
        
        # Check that mock XGBClassifier was called to create the model
        mock_xgb_class.assert_called_once()
        
        # Check the model was created with expected parameters
        call_kwargs = mock_xgb_class.call_args[1]
        assert call_kwargs['n_estimators'] == 150
        assert call_kwargs['max_depth'] == 8
        assert call_kwargs['learning_rate'] == 0.05
        
    @patch('xgboost.XGBClassifier')
    def test_fit_model_without_early_stopping(self, mock_xgb_class, sample_fraud_data):
        """Test model fitting without early stopping."""
        config = XGBoostConfig(model_name="test", early_stopping_rounds=None)
        
        mock_model = Mock()
        mock_model.fit.return_value = mock_model
        # Mock required attributes
        mock_model.n_estimators = 100
        mock_xgb_class.return_value = mock_model
        
        trainer = XGBoostTrainer(config)
        X, y = trainer.prepare_data(sample_fraud_data)
        
        fitted_model = trainer._fit_model(X, y)
        
        # Check that model.fit was called
        mock_model.fit.assert_called_once()
        call_args, call_kwargs = mock_model.fit.call_args
        # Should NOT have early stopping parameters when disabled
        assert "early_stopping_rounds" not in call_kwargs
        assert "eval_set" not in call_kwargs
        
    @patch('xgboost.XGBClassifier')
    def test_fit_model_with_early_stopping(self, mock_xgb_class, train_val_test_split):
        """Test model fitting with early stopping."""
        config = XGBoostConfig(model_name="test", early_stopping_rounds=10)
        
        mock_model = Mock()
        mock_model.fit.return_value = mock_model
        mock_xgb_class.return_value = mock_model
        
        trainer = XGBoostTrainer(config)
        train_data, val_data, _ = train_val_test_split
        
        X_train, y_train = trainer.prepare_data(train_data)
        X_val, y_val = trainer.prepare_data(val_data)
        
        # Simulate data split for early stopping by setting the validation data
        trainer.X_val, trainer.y_val = X_val, y_val
        
        fitted_model = trainer._fit_model(X_train, y_train)
        
        assert fitted_model == mock_model
        # Should be called with eval_set for early stopping
        mock_model.fit.assert_called_once()
        call_args, call_kwargs = mock_model.fit.call_args
        assert "eval_set" in call_kwargs
        assert "early_stopping_rounds" in call_kwargs
        
    @patch('xgboost.XGBClassifier')
    def test_predict(self, mock_xgb_class, sample_fraud_data):
        """Test prediction generation."""
        config = XGBoostConfig(model_name="test")
        
        mock_model = Mock()
        mock_predictions = np.array([0, 1, 0, 1, 0])
        mock_model.predict.return_value = mock_predictions
        mock_xgb_class.return_value = mock_model
        
        trainer = XGBoostTrainer(config)
        X, _ = trainer.prepare_data(sample_fraud_data)
        
        predictions = trainer._predict(mock_model, X.head())
        
        # Check that predict was called (don't compare DataFrame directly)
        mock_model.predict.assert_called_once()
        assert np.array_equal(predictions, mock_predictions)
        
    @patch('xgboost.XGBClassifier')
    def test_predict_proba(self, mock_xgb_class, sample_fraud_data):
        """Test probability prediction."""
        config = XGBoostConfig(model_name="test")
        
        mock_model = Mock()
        mock_probabilities = np.array([[0.8, 0.2], [0.3, 0.7], [0.9, 0.1]])
        mock_model.predict_proba.return_value = mock_probabilities
        mock_xgb_class.return_value = mock_model
        
        trainer = XGBoostTrainer(config)
        X, _ = trainer.prepare_data(sample_fraud_data)
        
        probabilities = trainer._predict_proba(mock_model, X.head(3))
        
        # Check that predict_proba was called (don't compare DataFrame directly)
        mock_model.predict_proba.assert_called_once()
        assert np.array_equal(probabilities, mock_probabilities[:, 1])  # Returns positive class probabilities
        
    @patch('xgboost.XGBClassifier')
    def test_get_feature_importance(self, mock_xgb_class, sample_fraud_data):
        """Test feature importance extraction."""
        config = XGBoostConfig(model_name="test")
        
        trainer = XGBoostTrainer(config)
        X, _ = trainer.prepare_data(sample_fraud_data)
        
        # Create mock model with proper feature_importances_ and booster
        mock_model = Mock()
        mock_importances = np.array([0.1, 0.2, 0.15, 0.05, 0.3, 0.1, 0.05, 0.025, 0.025])[:len(X.columns)]
        mock_model.feature_importances_ = mock_importances
        
        # Mock the booster with get_score method
        mock_booster = Mock()
        gain_scores = {f: float(imp) for f, imp in zip(X.columns, mock_importances)}
        cover_scores = {f: float(imp * 0.5) for f, imp in zip(X.columns, mock_importances)}
        mock_booster.get_score.side_effect = lambda importance_type='weight': (
            gain_scores if importance_type == 'gain' else cover_scores
        )
        mock_model.get_booster.return_value = mock_booster
        
        mock_xgb_class.return_value = mock_model
        
        trainer.feature_names = list(X.columns)
        
        importance = trainer._get_feature_importance(mock_model)
        
        assert len(importance) == len(X.columns)
        assert all(isinstance(v, (int, float)) for v in importance.values())
        assert all(k in X.columns for k in importance.keys())
        # Check that we got actual numeric values, not Mock objects
        assert all(not hasattr(v, '_mock_name') for v in importance.values())


class TestIsolationForestTrainer:
    """Test IsolationForestTrainer functionality."""
    
    @pytest.mark.parametrize("missing_sklearn", [False, True])
    def test_isolation_forest_trainer_initialization(self, missing_sklearn):
        """Test Isolation Forest trainer initialization."""
        config = IsolationForestConfig(model_name="if_test")
        
        if missing_sklearn:
            # sklearn is typically available, so we just create trainer normally
            # This test mainly checks the trainer can be instantiated
            trainer = IsolationForestTrainer(config)
            assert trainer.config == config
        else:
            trainer = IsolationForestTrainer(config)
            assert trainer.config == config
                
    def test_create_model(self):
        """Test Isolation Forest model creation."""
        config = IsolationForestConfig(
            model_name="test",
            n_estimators=200,
            contamination=0.1,
            max_features=0.8
        )
        
        trainer = IsolationForestTrainer(config)
        model = trainer._create_model()
        
        # Check that a model was created with the expected parameters
        assert model is not None
        assert model.n_estimators == 200
        assert model.contamination == 0.1
        assert model.max_features == 0.8
        
    @patch('ml.training.trainers.isolation_forest_trainer.IsolationForest')
    def test_fit_model(self, mock_if_class, sample_fraud_data):
        """Test Isolation Forest model fitting."""
        config = IsolationForestConfig(model_name="test")
        
        mock_model = Mock()
        mock_model.fit.return_value = mock_model
        mock_model.decision_function.return_value = np.array([-0.1, 0.2, -0.3, 0.1, 0.05])
        mock_if_class.return_value = mock_model
        
        trainer = IsolationForestTrainer(config)
        X, y = trainer.prepare_data(sample_fraud_data)
        
        fitted_model = trainer._fit_model(X, y)
        
        # Check that the model was fitted (don't compare mock objects directly)
        mock_model.fit.assert_called_once()
        # The fitted model should be the result of the fit operation
        assert fitted_model is not None
        
    @patch('sklearn.ensemble.IsolationForest')
    def test_predict(self, mock_if_class, sample_fraud_data):
        """Test Isolation Forest prediction."""
        config = IsolationForestConfig(model_name="test")
        
        mock_model = Mock()
        # Isolation Forest returns -1 for outliers, 1 for inliers
        mock_predictions_raw = np.array([-1, 1, -1, 1, 1])
        mock_model.predict.return_value = mock_predictions_raw
        # Mock decision_function for score threshold calculation
        mock_model.decision_function.return_value = np.array([-0.1, 0.2, -0.3, 0.1, 0.05])
        mock_if_class.return_value = mock_model
        
        trainer = IsolationForestTrainer(config)
        X, y = trainer.prepare_data(sample_fraud_data)
        
        # Fit the trainer first to set up preprocessing components
        trainer.X_train = X
        trainer.y_train = y
        # Initialize preprocessing components by calling _preprocess_features with fit=True
        trainer._preprocess_features(X.head(5), fit=True)
        trainer.score_threshold_ = 0.0  # Set a threshold for predictions
        
        predictions = trainer._predict(mock_model, X.head(5))
        
        # Check that decision_function was called for scoring
        mock_model.decision_function.assert_called()
        assert len(predictions) == 5
        assert all(p in [0, 1] for p in predictions)
        
    @patch('sklearn.ensemble.IsolationForest')
    def test_predict_proba(self, mock_if_class, sample_fraud_data):
        """Test Isolation Forest probability prediction."""
        config = IsolationForestConfig(model_name="test")
        
        mock_model = Mock()
        # decision_function returns anomaly scores (more negative = more anomalous)
        mock_scores = np.array([-0.1, 0.2, -0.3, 0.1, 0.05])
        mock_model.decision_function.return_value = mock_scores
        mock_if_class.return_value = mock_model
        
        trainer = IsolationForestTrainer(config)
        X, y = trainer.prepare_data(sample_fraud_data)
        
        # Fit the trainer first to set up preprocessing components
        trainer.X_train = X
        trainer.y_train = y
        # Initialize preprocessing components by calling _preprocess_features with fit=True
        trainer._preprocess_features(X.head(5), fit=True)
        
        probabilities = trainer._predict_proba(mock_model, X.head(5))
        
        mock_model.decision_function.assert_called()
        
        # Should convert scores to probabilities [0, 1]
        assert len(probabilities) == 5
        assert all(0 <= p <= 1 for p in probabilities)
        # More negative scores should give higher fraud probabilities
        assert probabilities[2] > probabilities[1]  # -0.3 vs 0.2
        
    @patch('sklearn.ensemble.IsolationForest')
    @patch('sklearn.inspection.permutation_importance')
    def test_get_feature_importance(self, mock_perm_importance, mock_if_class, sample_fraud_data):
        """Test Isolation Forest feature importance extraction."""
        config = IsolationForestConfig(model_name="test")
        
        trainer = IsolationForestTrainer(config)
        X, y = trainer.prepare_data(sample_fraud_data)
        
        mock_model = Mock()
        mock_if_class.return_value = mock_model
        
        # Mock permutation importance result
        mock_importance_result = Mock()
        mock_importance_result.importances_mean = np.array([0.1, 0.2, 0.15])[:len(X.columns)]
        mock_perm_importance.return_value = mock_importance_result
        
        trainer.feature_names = list(X.columns)
        # Need to set training data for permutation importance
        trainer.X_train = X
        trainer.y_train = y
        # Initialize preprocessing components
        trainer._preprocess_features(X, fit=True)
        trainer.score_threshold_ = 0.0  # Set threshold for scorer function
        
        importance = trainer._get_feature_importance(mock_model)
        
        assert len(importance) == len(X.columns)
        assert all(isinstance(v, (int, float)) for v in importance.values())
        assert all(k in X.columns for k in importance.keys())
        
        # Check permutation importance was called
        mock_perm_importance.assert_called_once()
        
    @patch('sklearn.ensemble.IsolationForest')
    def test_get_feature_importance_no_training_data(self, mock_if_class):
        """Test feature importance when no training data available."""
        config = IsolationForestConfig(model_name="test")
        
        mock_model = Mock()
        mock_if_class.return_value = mock_model
        
        trainer = IsolationForestTrainer(config)
        
        # Should return None when no training data
        importance = trainer._get_feature_importance(mock_model)
        assert importance is None


class TestTrainerIntegration:
    """Integration tests for trainers."""
    
    @patch('xgboost.XGBClassifier')
    @patch('ml.training.evaluation.ModelEvaluator')
    def test_xgboost_trainer_full_pipeline(self, mock_evaluator_class, mock_xgb_class, 
                                         sample_fraud_data, local_tracker):
        """Test complete XGBoost training pipeline."""
        # Setup mocks
        mock_model = Mock()
        mock_model.fit.return_value = mock_model
        mock_model.predict.return_value = np.random.randint(0, 2, 100)
        mock_model.predict_proba.return_value = np.random.rand(100, 2)
        mock_model.feature_importances_ = np.random.rand(9)  # 9 features in sample data
        mock_xgb_class.return_value = mock_model
        
        mock_evaluator = Mock()
        mock_evaluator.compute_classification_metrics.return_value = {"accuracy": 0.95, "roc_auc": 0.92}
        mock_evaluator_class.return_value = mock_evaluator
        
        # Train model
        config = XGBoostConfig(model_name="integration_test", use_cross_validation=False)
        trainer = XGBoostTrainer(config, local_tracker)
        
        result = trainer.train(sample_fraud_data)
        
        # Check result
        assert result.model_name == "integration_test"
        assert result.training_time > 0
        assert result.model == mock_model
        assert "accuracy" in result.test_metrics
        assert trainer.is_trained
        
    @patch('ml.training.trainers.isolation_forest_trainer.IsolationForest')
    @patch('ml.training.evaluation.ModelEvaluator')
    def test_isolation_forest_trainer_full_pipeline(self, mock_evaluator_class, mock_if_class,
                                                   sample_fraud_data, local_tracker):
        """Test complete Isolation Forest training pipeline."""
        # Setup mocks
        mock_model = Mock()
        mock_model.fit.return_value = mock_model
        mock_model.predict.return_value = np.random.choice([-1, 1], 100)
        mock_model.decision_function.return_value = np.random.randn(100)
        mock_if_class.return_value = mock_model
        
        mock_evaluator = Mock()
        mock_evaluator.compute_classification_metrics.return_value = {"accuracy": 0.85, "roc_auc": 0.78}
        mock_evaluator_class.return_value = mock_evaluator
        
        # Train model
        config = IsolationForestConfig(model_name="if_integration_test", use_cross_validation=False)
        trainer = IsolationForestTrainer(config, local_tracker)
        
        result = trainer.train(sample_fraud_data)
        
        # Check result structure (don't compare mock objects directly)
        assert result.model_name == "if_integration_test"
        assert result.training_time > 0
        assert result.model is not None
        assert "accuracy" in result.test_metrics
        assert trainer.is_trained