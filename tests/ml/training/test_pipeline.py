"""
Tests for training pipeline functionality.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
import json

from ml.training.pipeline import TrainingPipeline, ExperimentRunner, PipelineConfig
from ml.training.base import TrainingConfig
from ml.training.trainers import XGBoostConfig, IsolationForestConfig


class TestPipelineConfig:
    """Test PipelineConfig functionality."""
    
    def test_pipeline_config_defaults(self):
        """Test default pipeline configuration."""
        config = PipelineConfig()
        
        assert config.pipeline_name == "fraud_detection_training"
        assert config.pipeline_version == "1.0.0"
        assert config.experiment_tracker_type == "auto"
        assert config.experiment_name == "fraud_detection"
        assert config.optimize_thresholds is True
        assert config.save_models is True
        assert config.random_seed == 42
        
    def test_pipeline_config_custom(self, temp_dir):
        """Test custom pipeline configuration."""
        config = PipelineConfig(
            pipeline_name="custom_pipeline",
            dataset_path=temp_dir / "data.csv",
            experiment_tracker_type="local",
            registry_path=temp_dir / "registry",
            optimize_thresholds=False
        )
        
        assert config.pipeline_name == "custom_pipeline"
        assert config.dataset_path == temp_dir / "data.csv"
        assert config.experiment_tracker_type == "local"
        assert config.registry_path == temp_dir / "registry"
        assert config.optimize_thresholds is False
        
    def test_pipeline_config_yaml_roundtrip(self, temp_dir):
        """Test saving and loading configuration from YAML."""
        config = PipelineConfig(
            pipeline_name="yaml_test",
            dataset_path=temp_dir / "data.csv",
            trainer_configs=[
                XGBoostConfig(model_name="xgb_test", n_estimators=200),
                IsolationForestConfig(model_name="if_test", contamination=0.1)
            ]
        )
        
        yaml_path = temp_dir / "config.yaml"
        config.save_yaml(yaml_path)
        
        assert yaml_path.exists()
        
        # Load back
        loaded_config = PipelineConfig.from_yaml(yaml_path)
        
        assert loaded_config.pipeline_name == "yaml_test"
        assert str(loaded_config.dataset_path) == str(temp_dir / "data.csv")
        assert len(loaded_config.trainer_configs) == 2


class TestTrainingPipeline:
    """Test TrainingPipeline functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            
    def create_test_config(self) -> PipelineConfig:
        """Create test pipeline configuration."""
        return PipelineConfig(
            pipeline_name="test_pipeline",
            experiment_tracker_type="local",
            registry_path=self.temp_dir / "registry",
            artifacts_base_dir=self.temp_dir / "artifacts",
            trainer_configs=[
                XGBoostConfig(
                    model_name="xgboost_test",
                    use_cross_validation=False,
                    n_estimators=10  # Small for fast tests
                )
            ]
        )
        
    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        config = self.create_test_config()
        
        with patch('ml.training.pipeline.create_tracker') as mock_create_tracker:
            mock_tracker = Mock()
            mock_create_tracker.return_value = mock_tracker
            
            pipeline = TrainingPipeline(config)
            
            assert pipeline.config == config
            assert pipeline.experiment_tracker == mock_tracker
            assert pipeline.model_registry is not None
            assert pipeline.evaluator is not None
            assert pipeline.threshold_optimizer is not None
            
    def test_load_data_from_csv(self, sample_fraud_data):
        """Test loading data from CSV file."""
        config = self.create_test_config()
        csv_path = self.temp_dir / "test_data.csv"
        sample_fraud_data.to_csv(csv_path, index=False)
        config.dataset_path = csv_path
        
        with patch('ml.training.pipeline.create_tracker'):
            pipeline = TrainingPipeline(config)
            
            loaded_data = pipeline.load_data()
            
            assert len(loaded_data) == len(sample_fraud_data)
            assert list(loaded_data.columns) == list(sample_fraud_data.columns)
            
    def test_load_data_from_parquet(self, sample_fraud_data):
        """Test loading data from Parquet file."""
        config = self.create_test_config()
        parquet_path = self.temp_dir / "test_data.parquet"
        sample_fraud_data.to_parquet(parquet_path, index=False)
        config.dataset_path = parquet_path
        
        with patch('ml.training.pipeline.create_tracker'):
            pipeline = TrainingPipeline(config)
            
            loaded_data = pipeline.load_data()
            
            assert len(loaded_data) == len(sample_fraud_data)
            
    def test_load_data_unsupported_format(self):
        """Test error with unsupported file format."""
        config = self.create_test_config()
        unsupported_path = self.temp_dir / "test_data.xlsx"
        config.dataset_path = unsupported_path
        
        with patch('ml.training.pipeline.create_tracker'):
            pipeline = TrainingPipeline(config)
            
            with pytest.raises(ValueError, match="Unsupported file format"):
                pipeline.load_data()
                
    def test_load_data_no_source(self):
        """Test error when no data source configured."""
        config = self.create_test_config()
        config.dataset_path = None
        config.feature_store_path = None
        
        with patch('ml.training.pipeline.create_tracker'):
            pipeline = TrainingPipeline(config)
            
            with pytest.raises(ValueError, match="Either dataset_path or feature_store configuration must be provided"):
                pipeline.load_data()
                
    def test_load_data_empty_file(self):
        """Test error with empty dataset."""
        config = self.create_test_config()
        csv_path = self.temp_dir / "empty_data.csv"
        pd.DataFrame().to_csv(csv_path, index=False)
        config.dataset_path = csv_path
        
        with patch('ml.training.pipeline.create_tracker'):
            pipeline = TrainingPipeline(config)
            
            with pytest.raises((ValueError, pd.errors.EmptyDataError), match="(Loaded dataset is empty|No columns to parse from file)"):
                pipeline.load_data()
                
    @patch('ml.training.trainers.XGBoostTrainer')
    @patch('ml.training.evaluation.ModelEvaluator')
    def test_run_single_trainer(self, mock_evaluator_class, mock_trainer_class, sample_fraud_data):
        """Test running single trainer."""
        config = self.create_test_config()
        
        # Mock trainer
        mock_trainer = Mock()
        mock_result = Mock()
        mock_result.model_name = "xgboost_test"
        mock_result.training_time = 10.0
        mock_result.model = {"type": "mock_model"}
        mock_result.feature_names = ["f1", "f2", "f3"]
        mock_result.train_metrics = {"accuracy": 0.95}
        mock_result.validation_metrics = {"accuracy": 0.93}
        mock_result.test_metrics = {"accuracy": 0.91}
        mock_result.cv_metrics = {"cv_roc_auc_mean": 0.88}
        mock_result.feature_importance = {"f1": 0.5, "f2": 0.3, "f3": 0.2}
        mock_result.test_predictions = np.array([0, 1, 0, 1])
        
        mock_trainer.train.return_value = mock_result
        mock_trainer._predict_proba.return_value = np.array([0.1, 0.9, 0.2, 0.8])
        mock_trainer.y_test = np.array([0, 1, 0, 1])
        mock_trainer_class.return_value = mock_trainer
        
        # Mock evaluator
        mock_evaluator = Mock()
        mock_evaluator.generate_evaluation_report.return_value = {
            "model_id": "test_model",
            "metrics": {"accuracy": 0.91},
            "artifact_paths": {"metrics": "metrics.json", "confusion_matrix": "cm.png"},
            "feature_importance": {"f1": 0.5}
        }
        mock_evaluator_class.return_value = mock_evaluator
        
        with patch('ml.training.pipeline.create_tracker'):
            with patch('ml.training.registry.generate_model_id', return_value="test_model_123"):
                pipeline = TrainingPipeline(config)
                
                result = pipeline._run_single_trainer(
                    sample_fraud_data, 
                    config.trainer_configs[0], 
                    "xgb_test"
                )
                
                assert result.model_name == "xgboost_test"
                assert result.training_time == 10.0
                
                # Check trainer was created and called
                mock_trainer_class.assert_called_once()
                mock_trainer.train.assert_called_once_with(sample_fraud_data)
                
    @patch('ml.training.trainers.XGBoostTrainer')
    @patch('ml.training.evaluation.ModelEvaluator')
    def test_run_pipeline_success(self, mock_evaluator_class, mock_trainer_class, sample_fraud_data):
        """Test successful pipeline execution."""
        config = self.create_test_config()
        
        # Setup mocks (similar to previous test)
        mock_trainer = Mock()
        mock_result = Mock()
        mock_result.model_name = "xgboost_test"
        mock_result.training_time = 10.0
        mock_result.model = {"type": "mock_model"}
        mock_result.feature_names = ["f1", "f2", "f3"]
        mock_result.train_metrics = {"accuracy": 0.95}
        mock_result.validation_metrics = {"accuracy": 0.93}
        mock_result.test_metrics = {"accuracy": 0.91}
        mock_result.cv_metrics = {}
        mock_result.feature_importance = {"f1": 0.5}
        mock_result.test_predictions = np.array([0, 1])
        mock_result.config = {"model_name": "xgboost_test"}
        
        mock_trainer.train.return_value = mock_result
        mock_trainer._predict_proba.return_value = np.array([0.1, 0.9])
        mock_trainer.y_test = np.array([0, 1])
        mock_trainer_class.return_value = mock_trainer
        
        mock_evaluator = Mock()
        mock_evaluator.generate_evaluation_report.return_value = {
            "model_id": "test",
            "metrics": {"accuracy": 0.91},
            "artifact_paths": {"metrics": "metrics.json"},
            "feature_importance": None
        }
        mock_evaluator_class.return_value = mock_evaluator
        
        with patch('ml.training.pipeline.create_tracker'):
            with patch('ml.training.registry.generate_model_id', return_value="test_model_123"):
                pipeline = TrainingPipeline(config)
                
                results = pipeline.run(sample_fraud_data)
                
                assert len(results) == 1
                assert "xgboost_test_0" in results
                assert results["xgboost_test_0"].model_name == "xgboost_test"
                
    def test_run_pipeline_trainer_failure(self, sample_fraud_data):
        """Test pipeline handling trainer failure."""
        config = self.create_test_config()
        
        # Add second trainer to ensure pipeline continues after failure
        config.trainer_configs.append(
            IsolationForestConfig(model_name="isolation_test", use_cross_validation=False)
        )
        
        with patch('ml.training.trainers.XGBoostTrainer') as mock_xgb:
            with patch('ml.training.trainers.IsolationForestTrainer') as mock_if:
                # First trainer fails
                mock_xgb.return_value.train.side_effect = ValueError("Training failed")
                
                # Second trainer succeeds
                mock_if_trainer = Mock()
                mock_result = Mock()
                mock_result.model_name = "isolation_test"
                mock_result.training_time = 5.0
                mock_result.model = {"type": "isolation_forest"}
                mock_result.feature_names = ["f1", "f2"]
                mock_result.train_metrics = {"accuracy": 0.85}
                mock_result.validation_metrics = {"accuracy": 0.83}
                mock_result.test_metrics = {"accuracy": 0.81}
                mock_result.cv_metrics = {}
                mock_result.feature_importance = None
                mock_result.test_predictions = np.array([0, 1])
                mock_result.config = {"model_name": "isolation_test"}
                
                mock_if_trainer.train.return_value = mock_result
                mock_if_trainer._predict_proba.return_value = np.array([0.3, 0.7])
                mock_if_trainer.y_test = np.array([0, 1])
                mock_if.return_value = mock_if_trainer
                
                with patch('ml.training.evaluation.ModelEvaluator'):
                    with patch('ml.training.pipeline.create_tracker'):
                        with patch('ml.training.registry.generate_model_id', return_value="test_model_456"):
                            pipeline = TrainingPipeline(config)
                            
                            results = pipeline.run(sample_fraud_data)
                            
                            # Only successful trainer should be in results
                            assert len(results) == 1
                            assert "isolation_test_1" in results
                            
    @patch('matplotlib.pyplot.subplots')
    @patch('matplotlib.pyplot.close')
    def test_generate_comparative_analysis(self, mock_close, mock_subplots, sample_fraud_data):
        """Test comparative analysis generation."""
        config = self.create_test_config()
        
        # Create mock results
        from ml.training.base import TrainingResult
        
        result1 = TrainingResult(
            run_id="run1",
            model_name="xgboost",
            model_version="1.0",
            training_time=10.0,
            model=None,
            train_metrics={"roc_auc": 0.95, "f1_score": 0.85},
            validation_metrics={"roc_auc": 0.93, "f1_score": 0.83},
            test_metrics={"roc_auc": 0.91, "f1_score": 0.81},
            feature_names=["f1", "f2"]
        )
        
        result2 = TrainingResult(
            run_id="run2", 
            model_name="isolation_forest",
            model_version="1.0",
            training_time=5.0,
            model=None,
            train_metrics={"roc_auc": 0.85, "f1_score": 0.75},
            validation_metrics={"roc_auc": 0.83, "f1_score": 0.73},
            test_metrics={"roc_auc": 0.81, "f1_score": 0.71},
            feature_names=["f1", "f2"]
        )
        
        results = {"xgb": result1, "if": result2}
        
        # Mock matplotlib
        mock_fig = Mock()
        mock_axes = [Mock() for _ in range(6)]
        mock_subplots.return_value = (mock_fig, np.array(mock_axes).reshape(2, 3))
        
        with patch('ml.training.pipeline.create_tracker'):
            pipeline = TrainingPipeline(config)
            
            pipeline._generate_comparative_analysis(results)
            
            # Check CSV was saved
            comparison_file = config.artifacts_base_dir / "model_comparison" / "model_comparison.csv"
            assert comparison_file.exists()
            
            # Check CSV content
            comparison_df = pd.read_csv(comparison_file)
            assert len(comparison_df) == 2
            assert "model_name" in comparison_df.columns
            assert "test_roc_auc" in comparison_df.columns


class TestExperimentRunner:
    """Test ExperimentRunner functionality."""
    
    def test_experiment_runner_initialization(self):
        """Test experiment runner initialization."""
        base_config = PipelineConfig(pipeline_name="base_test")
        
        runner = ExperimentRunner(base_config)
        
        assert runner.base_config == base_config
        assert runner.experiments == []
        assert runner.results == {}
        
    def test_add_experiment(self):
        """Test adding experiments to runner."""
        base_config = PipelineConfig()
        runner = ExperimentRunner(base_config)
        
        trainer_configs = [XGBoostConfig(model_name="xgb_exp1")]
        
        runner.add_experiment(
            "experiment_1",
            trainer_configs,
            experiment_tracker_type="local"
        )
        
        assert len(runner.experiments) == 1
        
        exp = runner.experiments[0]
        assert exp["name"] == "experiment_1"
        assert exp["config"].pipeline_name == f"{base_config.pipeline_name}_experiment_1"
        assert exp["config"].experiment_tracker_type == "local"
        assert len(exp["config"].trainer_configs) == 1
        
    @patch('ml.training.pipeline.TrainingPipeline')
    def test_run_all_experiments(self, mock_pipeline_class, sample_fraud_data):
        """Test running all experiments."""
        base_config = PipelineConfig()
        runner = ExperimentRunner(base_config)
        
        # Add experiments
        runner.add_experiment("exp1", [XGBoostConfig(model_name="xgb1")])
        runner.add_experiment("exp2", [IsolationForestConfig(model_name="if1")])
        
        # Mock pipeline results
        mock_pipeline1 = Mock()
        mock_pipeline1.run.return_value = {"model1": Mock(model_name="xgb1")}
        
        mock_pipeline2 = Mock()
        mock_pipeline2.run.return_value = {"model2": Mock(model_name="if1")}
        
        mock_pipeline_class.side_effect = [mock_pipeline1, mock_pipeline2]
        
        results = runner.run_all_experiments(sample_fraud_data)
        
        assert len(results) == 2
        assert "exp1" in results
        assert "exp2" in results
        assert len(results["exp1"]) == 1
        assert len(results["exp2"]) == 1
        
        # Check pipelines were created and run
        assert mock_pipeline_class.call_count == 2
        mock_pipeline1.run.assert_called_once_with(sample_fraud_data)
        mock_pipeline2.run.assert_called_once_with(sample_fraud_data)
        
    @patch('ml.training.pipeline.TrainingPipeline')
    def test_run_experiments_with_failure(self, mock_pipeline_class, sample_fraud_data):
        """Test experiment runner handling failures."""
        base_config = PipelineConfig()
        runner = ExperimentRunner(base_config)
        
        runner.add_experiment("exp1", [XGBoostConfig(model_name="xgb1")])
        runner.add_experiment("exp2", [IsolationForestConfig(model_name="if1")])
        
        # First pipeline fails, second succeeds
        mock_pipeline1 = Mock()
        mock_pipeline1.run.side_effect = ValueError("Pipeline failed")
        
        mock_pipeline2 = Mock()
        mock_pipeline2.run.return_value = {"model2": Mock(model_name="if1")}
        
        mock_pipeline_class.side_effect = [mock_pipeline1, mock_pipeline2]
        
        results = runner.run_all_experiments(sample_fraud_data)
        
        assert len(results) == 2
        assert "exp1" in results
        assert "exp2" in results
        assert len(results["exp1"]) == 0  # Failed experiment has empty results
        assert len(results["exp2"]) == 1  # Successful experiment has results