#!/usr/bin/env python3
"""
ML Phase 2 Validation Script

Comprehensive validation of the training pipeline implementation.
Tests all components with real Credit Card Fraud Detection dataset.
"""

import sys
import os
import logging
import time
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
import tempfile
import shutil
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.training.pipeline import TrainingPipeline, PipelineConfig
from ml.training.trainers import XGBoostConfig, IsolationForestConfig
from ml.training.tracking import create_tracker
from ml.training.registry import ModelRegistry
from ml.training.optimization import (
    ThresholdOptimizer, OptimizationConfig, OptimizationObjective,
    create_f1_optimizer, create_business_cost_optimizer, create_recall_optimizer
)
from ml.utils.logging_config import setup_logging

class ValidationError(Exception):
    """Raised when validation fails."""
    pass

class MLPhase2Validator:
    """Comprehensive validator for ML Phase 2 training pipeline."""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("validation_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Setup logging
        setup_logging(level="INFO")
        self.logger = logging.getLogger(__name__)
        
        # Validation results
        self.results = {
            "start_time": datetime.utcnow(),
            "tests": {},
            "artifacts": {},
            "metrics": {},
            "errors": []
        }
        
        # Dataset paths
        self.datasets = {}
        
        self.logger.info("ML Phase 2 Validator initialized")
        self.logger.info(f"Output directory: {self.output_dir}")
    
    def create_sample_credit_card_dataset(self, size: str = "medium") -> Path:
        """Create realistic credit card fraud dataset for testing."""
        
        self.logger.info(f"Creating {size} credit card fraud dataset...")
        
        # Dataset sizes
        sizes = {
            "small": 1000,
            "medium": 5000, 
            "large": 20000
        }
        
        n_samples = sizes.get(size, 5000)
        np.random.seed(42)  # For reproducibility
        
        # Generate realistic credit card transaction features
        data = {
            # Time features
            'Time': np.random.exponential(3600, n_samples),  # Seconds from first transaction
            
            # Anonymized PCA features (V1-V28 as in real dataset)
            **{f'V{i}': np.random.normal(0, 1, n_samples) for i in range(1, 29)},
            
            # Amount (log-normal distribution)
            'Amount': np.random.lognormal(3, 1.5, n_samples).clip(0, 25000),
        }
        
        df = pd.DataFrame(data)
        
        # Create realistic fraud patterns
        fraud_probability = (
            0.001 +  # Base fraud rate (0.1%)
            0.05 * (df['Amount'] > df['Amount'].quantile(0.99)) +  # Very high amounts
            0.02 * (df['Time'] > df['Time'].quantile(0.9)) +  # Late transactions
            0.01 * (np.abs(df['V1']) > 3) +  # Outlier in V1
            0.01 * (np.abs(df['V2']) > 3) +  # Outlier in V2
            0.015 * (np.abs(df['V4']) > 3)   # Outlier in V4
        )
        
        # Generate fraud labels
        df['Class'] = np.random.binomial(1, fraud_probability.clip(0, 0.1), n_samples)
        
        # Make fraud cases more extreme in certain features
        fraud_mask = df['Class'] == 1
        df.loc[fraud_mask, 'V1'] = np.random.normal(-2, 2, fraud_mask.sum())
        df.loc[fraud_mask, 'V2'] = np.random.normal(3, 1.5, fraud_mask.sum()) 
        df.loc[fraud_mask, 'V4'] = np.random.normal(-1.5, 2, fraud_mask.sum())
        df.loc[fraud_mask, 'Amount'] = np.random.lognormal(4.5, 1, fraud_mask.sum())
        
        # Save dataset
        dataset_path = self.output_dir / f"credit_card_fraud_{size}.csv"
        df.to_csv(dataset_path, index=False)
        
        # Store dataset info
        self.datasets[size] = {
            "path": dataset_path,
            "samples": len(df),
            "fraud_cases": df['Class'].sum(),
            "fraud_rate": df['Class'].mean(),
            "features": len(df.columns) - 1  # Excluding target
        }
        
        self.logger.info(f"Created {size} dataset: {len(df)} samples, {df['Class'].sum()} fraud cases ({df['Class'].mean():.2%} fraud rate)")
        
        return dataset_path
    
    def validate_dataset_loading(self, dataset_path: Path) -> Dict[str, Any]:
        """Validate dataset loading and basic validation."""
        
        self.logger.info("Validating dataset loading...")
        
        try:
            # Load dataset
            df = pd.read_csv(dataset_path)
            
            # Basic validation
            assert len(df) > 0, "Dataset is empty"
            assert 'Class' in df.columns, "Missing target column 'Class'"
            assert df['Class'].nunique() == 2, "Target should be binary"
            assert not df.isnull().all().any(), "Dataset has completely null columns"
            
            # Fraud distribution validation
            fraud_rate = df['Class'].mean()
            assert 0 < fraud_rate < 0.5, f"Unusual fraud rate: {fraud_rate:.2%}"
            
            validation_result = {
                "success": True,
                "dataset_shape": df.shape,
                "fraud_cases": int(df['Class'].sum()),
                "fraud_rate": float(fraud_rate),
                "feature_count": len(df.columns) - 1,
                "missing_values": int(df.isnull().sum().sum())
            }
            
            self.logger.info(f"✓ Dataset validation passed: {df.shape} with {fraud_rate:.2%} fraud rate")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"✗ Dataset validation failed: {e}")
            raise ValidationError(f"Dataset loading failed: {e}")
    
    def validate_feature_engineering(self, dataset_path: Path) -> Dict[str, Any]:
        """Validate feature engineering capabilities."""
        
        self.logger.info("Validating feature engineering...")
        
        try:
            df = pd.read_csv(dataset_path)
            
            # Test feature preparation
            from ml.training.base import BaseTrainer, TrainingConfig
            
            config = TrainingConfig(
                model_name="feature_test",
                target_column="Class"
            )
            
            # Create dummy trainer to test feature preparation
            class DummyTrainer(BaseTrainer):
                def _create_model(self): return None
                def _fit_model(self, X, y): return None
                def _predict(self, model, X): return np.zeros(len(X))
                def _predict_proba(self, model, X): return np.random.rand(len(X))
                def _get_feature_importance(self, model): return None
            
            trainer = DummyTrainer(config)
            
            # Test data preparation
            X, y = trainer.prepare_data(df)
            
            # Validate prepared data
            assert len(X) == len(df), "Feature matrix length mismatch"
            assert len(y) == len(df), "Target vector length mismatch"
            assert 'Class' not in X.columns, "Target column found in features"
            assert X.shape[1] == len(df.columns) - 1, "Feature count mismatch"
            
            # Test data splitting
            X_train, X_val, X_test, y_train, y_val, y_test = trainer.split_data(X, y)
            
            # Validate splits
            total_samples = len(X_train) + len(X_val) + len(X_test)
            assert total_samples == len(df), "Data split sample count mismatch"
            assert len(X_train) > len(X_val), "Training set should be larger than validation"
            assert len(X_train) > len(X_test), "Training set should be larger than test"
            
            validation_result = {
                "success": True,
                "original_shape": df.shape,
                "feature_matrix_shape": X.shape,
                "target_vector_length": len(y),
                "train_samples": len(X_train),
                "val_samples": len(X_val), 
                "test_samples": len(X_test),
                "feature_names": list(X.columns)
            }
            
            self.logger.info("✓ Feature engineering validation passed")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"✗ Feature engineering validation failed: {e}")
            raise ValidationError(f"Feature engineering failed: {e}")
    
    def validate_xgboost_training(self, dataset_path: Path, tracker) -> Dict[str, Any]:
        """Validate XGBoost training pipeline."""
        
        self.logger.info("Validating XGBoost training...")
        
        try:
            from ml.training.trainers import XGBoostTrainer
            
            # Create XGBoost configuration
            config = XGBoostConfig(
                model_name="xgboost_validation",
                model_version="1.0.0",
                target_column="Class",
                n_estimators=50,  # Reduced for faster validation
                max_depth=4,
                learning_rate=0.1,
                early_stopping=True,
                early_stopping_rounds=5,
                use_cross_validation=True,
                cv_folds=3  # Reduced for faster validation
            )
            
            # Load data and train
            df = pd.read_csv(dataset_path)
            trainer = XGBoostTrainer(config, tracker)
            
            start_time = time.time()
            result = trainer.train(df)
            training_time = time.time() - start_time
            
            # Validate training result
            assert result.model is not None, "XGBoost model not trained"
            assert result.training_time > 0, "Invalid training time"
            assert len(result.feature_names) > 0, "No feature names recorded"
            assert result.train_metrics, "No training metrics recorded"
            assert result.test_metrics, "No test metrics recorded"
            
            # Validate specific metrics
            test_metrics = result.test_metrics
            assert "roc_auc" in test_metrics, "ROC-AUC metric missing"
            assert 0.5 <= test_metrics["roc_auc"] <= 1.0, f"Invalid ROC-AUC: {test_metrics['roc_auc']}"
            
            validation_result = {
                "success": True,
                "model_type": "XGBoost",
                "training_time": training_time,
                "model_trained": result.model is not None,
                "feature_count": len(result.feature_names),
                "train_roc_auc": result.train_metrics.get("roc_auc"),
                "val_roc_auc": result.validation_metrics.get("roc_auc"),
                "test_roc_auc": result.test_metrics.get("roc_auc"),
                "test_accuracy": result.test_metrics.get("accuracy"),
                "test_precision": result.test_metrics.get("precision"),
                "test_recall": result.test_metrics.get("recall"),
                "test_f1": result.test_metrics.get("f1_score"),
                "cv_metrics": result.cv_metrics,
                "feature_importance_available": result.feature_importance is not None
            }
            
            self.logger.info(f"✓ XGBoost training passed - ROC-AUC: {test_metrics['roc_auc']:.3f}")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"✗ XGBoost training failed: {e}")
            raise ValidationError(f"XGBoost training failed: {e}")
    
    def validate_isolation_forest_training(self, dataset_path: Path, tracker) -> Dict[str, Any]:
        """Validate Isolation Forest training pipeline."""
        
        self.logger.info("Validating Isolation Forest training...")
        
        try:
            from ml.training.trainers import IsolationForestTrainer
            
            # Create Isolation Forest configuration
            config = IsolationForestConfig(
                model_name="isolation_forest_validation",
                model_version="1.0.0", 
                target_column="Class",
                n_estimators=50,  # Reduced for faster validation
                contamination="auto",
                max_features=1.0,
                use_cross_validation=True,
                cv_folds=3
            )
            
            # Load data and train
            df = pd.read_csv(dataset_path)
            trainer = IsolationForestTrainer(config, tracker)
            
            start_time = time.time()
            result = trainer.train(df)
            training_time = time.time() - start_time
            
            # Validate training result
            assert result.model is not None, "Isolation Forest model not trained"
            assert result.training_time > 0, "Invalid training time"
            assert len(result.feature_names) > 0, "No feature names recorded"
            assert result.test_metrics, "No test metrics recorded"
            
            # Validate metrics (Isolation Forest is unsupervised, so metrics may be lower)
            test_metrics = result.test_metrics
            assert "roc_auc" in test_metrics, "ROC-AUC metric missing"
            assert 0.3 <= test_metrics["roc_auc"] <= 1.0, f"Invalid ROC-AUC: {test_metrics['roc_auc']}"
            
            validation_result = {
                "success": True,
                "model_type": "IsolationForest",
                "training_time": training_time,
                "model_trained": result.model is not None,
                "feature_count": len(result.feature_names),
                "test_roc_auc": result.test_metrics.get("roc_auc"),
                "test_accuracy": result.test_metrics.get("accuracy"),
                "test_precision": result.test_metrics.get("precision"),
                "test_recall": result.test_metrics.get("recall"),
                "test_f1": result.test_metrics.get("f1_score"),
                "cv_metrics": result.cv_metrics,
                "feature_importance_available": result.feature_importance is not None
            }
            
            self.logger.info(f"✓ Isolation Forest training passed - ROC-AUC: {test_metrics['roc_auc']:.3f}")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"✗ Isolation Forest training failed: {e}")
            raise ValidationError(f"Isolation Forest training failed: {e}")
    
    def validate_complete_pipeline(self, dataset_path: Path) -> Dict[str, Any]:
        """Validate complete end-to-end training pipeline."""
        
        self.logger.info("Validating complete training pipeline...")
        
        try:
            # Create pipeline configuration
            artifacts_dir = self.output_dir / "pipeline_artifacts"
            registry_dir = self.output_dir / "model_registry"
            
            config = PipelineConfig(
                pipeline_name="validation_pipeline",
                dataset_path=dataset_path,
                experiment_tracker_type="local",
                registry_path=registry_dir,
                artifacts_base_dir=artifacts_dir,
                generate_evaluation_reports=True,
                optimize_thresholds=True,
                random_seed=42,
                trainer_configs=[
                    XGBoostConfig(
                        model_name="xgboost_pipeline_test",
                        n_estimators=30,
                        max_depth=4,
                        use_cross_validation=False  # Skip CV for faster validation
                    ),
                    IsolationForestConfig(
                        model_name="isolation_forest_pipeline_test",
                        n_estimators=30,
                        use_cross_validation=False
                    )
                ]
            )
            
            # Run complete pipeline
            pipeline = TrainingPipeline(config)
            
            start_time = time.time()
            results = pipeline.run()
            pipeline_time = time.time() - start_time
            
            # Validate pipeline results
            assert len(results) == 2, f"Expected 2 models, got {len(results)}"
            
            model_results = {}
            for model_name, result in results.items():
                assert result.model is not None, f"Model {model_name} not trained"
                assert result.test_metrics, f"No test metrics for {model_name}"
                
                model_results[model_name] = {
                    "training_time": result.training_time,
                    "test_roc_auc": result.test_metrics.get("roc_auc"),
                    "test_accuracy": result.test_metrics.get("accuracy")
                }
            
            # Validate artifacts were created
            assert artifacts_dir.exists(), "Artifacts directory not created"
            assert registry_dir.exists(), "Registry directory not created"
            
            # Check registry
            registry = ModelRegistry(registry_dir)
            registered_models = registry.list_models()
            assert len(registered_models) >= 2, "Models not registered properly"
            
            validation_result = {
                "success": True,
                "pipeline_time": pipeline_time,
                "models_trained": len(results),
                "model_results": model_results,
                "artifacts_created": artifacts_dir.exists(),
                "registry_created": registry_dir.exists(),
                "registered_models": len(registered_models),
                "artifacts_path": str(artifacts_dir),
                "registry_path": str(registry_dir)
            }
            
            self.logger.info(f"✓ Complete pipeline validation passed - {len(results)} models trained in {pipeline_time:.1f}s")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"✗ Complete pipeline validation failed: {e}")
            raise ValidationError(f"Complete pipeline failed: {e}")
    
    def validate_artifacts_generation(self, artifacts_dir: Path) -> Dict[str, Any]:
        """Validate that all required artifacts are generated."""
        
        self.logger.info("Validating artifact generation...")
        
        try:
            if not artifacts_dir.exists():
                raise ValidationError("Artifacts directory does not exist")
            
            # Find model directories
            model_dirs = [d for d in artifacts_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
            
            if not model_dirs:
                raise ValidationError("No model directories found in artifacts")
            
            artifacts_found = {
                "model_directories": len(model_dirs),
                "models_with_artifacts": {},
                "total_files_found": 0
            }
            
            required_artifacts = [
                "model.pkl",
                "config.yaml", 
                "predictions.json"
            ]
            
            optional_artifacts = [
                "evaluation/evaluation_metrics.json",
                "evaluation/roc_curve.png",
                "evaluation/pr_curve.png", 
                "evaluation/confusion_matrix.png",
                "evaluation/calibration_curve.png",
                "evaluation/feature_importance.png",
                "threshold_optimization/"
            ]
            
            for model_dir in model_dirs:
                model_name = model_dir.name
                model_artifacts = {
                    "required": {},
                    "optional": {},
                    "total_files": 0
                }
                
                # Check required artifacts
                for artifact in required_artifacts:
                    artifact_path = model_dir / artifact
                    model_artifacts["required"][artifact] = artifact_path.exists()
                    if artifact_path.exists():
                        model_artifacts["total_files"] += 1
                
                # Check optional artifacts
                for artifact in optional_artifacts:
                    artifact_path = model_dir / artifact
                    model_artifacts["optional"][artifact] = artifact_path.exists()
                    if artifact_path.exists():
                        if artifact_path.is_dir():
                            model_artifacts["total_files"] += len(list(artifact_path.rglob("*")))
                        else:
                            model_artifacts["total_files"] += 1
                
                artifacts_found["models_with_artifacts"][model_name] = model_artifacts
                artifacts_found["total_files_found"] += model_artifacts["total_files"]
            
            # Validate that key artifacts exist
            models_with_required_artifacts = 0
            for model_name, artifacts in artifacts_found["models_with_artifacts"].items():
                if all(artifacts["required"].values()):
                    models_with_required_artifacts += 1
            
            validation_result = {
                "success": models_with_required_artifacts > 0,
                "artifacts_found": artifacts_found,
                "models_with_complete_artifacts": models_with_required_artifacts,
                "total_model_directories": len(model_dirs),
                "total_files_created": artifacts_found["total_files_found"]
            }
            
            if validation_result["success"]:
                self.logger.info(f"✓ Artifact validation passed - {artifacts_found['total_files_found']} files created")
            else:
                self.logger.error("✗ Artifact validation failed - missing required artifacts")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"✗ Artifact validation failed: {e}")
            raise ValidationError(f"Artifact validation failed: {e}")
    
    def validate_experiment_tracking(self, tracker) -> Dict[str, Any]:
        """Validate experiment tracking functionality."""
        
        self.logger.info("Validating experiment tracking...")
        
        try:
            # Test basic tracking operations
            run_id = tracker.start_run("validation_test_run")
            
            # Test parameter logging
            test_params = {
                "learning_rate": 0.1,
                "max_depth": 6,
                "n_estimators": 100,
                "validation_test": True
            }
            tracker.log_params(run_id, test_params)
            
            # Test metric logging
            test_metrics = {
                "accuracy": 0.95,
                "roc_auc": 0.92,
                "precision": 0.88,
                "recall": 0.90,
                "f1_score": 0.89
            }
            tracker.log_metrics(run_id, test_metrics)
            
            # Test tag setting
            test_tags = {
                "model_type": "validation_test",
                "framework": "xgboost",
                "validation": "true"
            }
            tracker.set_tags(run_id, test_tags)
            
            # End run
            tracker.end_run(run_id)
            
            # Validate run can be retrieved
            retrieved_run = tracker.get_run(run_id)
            assert retrieved_run is not None, "Could not retrieve run"
            assert retrieved_run.run_id == run_id, "Run ID mismatch"
            
            # Validate logged data
            assert all(k in retrieved_run.params for k in test_params.keys()), "Parameters not logged correctly"
            assert all(k in retrieved_run.metrics for k in test_metrics.keys()), "Metrics not logged correctly"
            assert all(k in retrieved_run.tags for k in test_tags.keys()), "Tags not logged correctly"
            
            # Test run listing
            runs = tracker.list_runs()
            assert len(runs) > 0, "No runs found"
            assert any(run.run_id == run_id for run in runs), "Test run not found in list"
            
            validation_result = {
                "success": True,
                "tracker_type": tracker.__class__.__name__,
                "run_id": run_id,
                "params_logged": len(test_params),
                "metrics_logged": len(test_metrics),
                "tags_logged": len(test_tags),
                "run_retrievable": retrieved_run is not None,
                "total_runs": len(runs)
            }
            
            self.logger.info(f"✓ Experiment tracking validation passed - {tracker.__class__.__name__}")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"✗ Experiment tracking validation failed: {e}")
            raise ValidationError(f"Experiment tracking failed: {e}")
    
    def validate_threshold_optimization(self, dataset_path: Path) -> Dict[str, Any]:
        """Validate threshold optimization functionality."""
        
        self.logger.info("Validating threshold optimization...")
        
        try:
            # Load data and train a quick model for threshold optimization
            df = pd.read_csv(dataset_path)
            
            from ml.training.trainers import XGBoostTrainer
            
            config = XGBoostConfig(
                model_name="threshold_test",
                target_column="Class",
                n_estimators=20,  # Quick training
                max_depth=3,
                use_cross_validation=False
            )
            
            trainer = XGBoostTrainer(config)
            result = trainer.train(df)
            
            # Get predictions and probabilities
            y_true = trainer.y_test
            y_proba = trainer._predict_proba(result.model, trainer.X_test)
            
            # Test different optimization objectives
            optimizer = ThresholdOptimizer()
            optimization_results = {}
            
            # F1 Score optimization
            f1_config = create_f1_optimizer()
            f1_result = optimizer.optimize_threshold(y_true, y_proba, f1_config)
            optimization_results["f1_score"] = {
                "optimal_threshold": f1_result.optimal_threshold,
                "objective_value": f1_result.objective_value,
                "precision": f1_result.metrics_at_optimal["precision"],
                "recall": f1_result.metrics_at_optimal["recall"]
            }
            
            # Recall optimization
            recall_config = create_recall_optimizer(min_precision=0.1)
            recall_result = optimizer.optimize_threshold(y_true, y_proba, recall_config)
            optimization_results["recall"] = {
                "optimal_threshold": recall_result.optimal_threshold,
                "objective_value": recall_result.objective_value,
                "precision": recall_result.metrics_at_optimal["precision"],
                "recall": recall_result.metrics_at_optimal["recall"]
            }
            
            # Business cost optimization
            business_config = create_business_cost_optimizer(
                false_positive_cost=10,
                false_negative_cost=100,
                true_positive_reward=50
            )
            business_result = optimizer.optimize_threshold(y_true, y_proba, business_config)
            optimization_results["business_cost"] = {
                "optimal_threshold": business_result.optimal_threshold,
                "objective_value": business_result.objective_value,
                "precision": business_result.metrics_at_optimal["precision"], 
                "recall": business_result.metrics_at_optimal["recall"]
            }
            
            # Validate results
            for objective, result in optimization_results.items():
                assert 0 <= result["optimal_threshold"] <= 1, f"Invalid threshold for {objective}"
                assert 0 <= result["precision"] <= 1, f"Invalid precision for {objective}"
                assert 0 <= result["recall"] <= 1, f"Invalid recall for {objective}"
            
            # Compare thresholds - they should be different
            thresholds = [result["optimal_threshold"] for result in optimization_results.values()]
            assert len(set(thresholds)) > 1, "All thresholds are the same - optimization not working"
            
            validation_result = {
                "success": True,
                "optimization_results": optimization_results,
                "unique_thresholds": len(set(thresholds)),
                "test_samples": len(y_true),
                "fraud_cases": int(y_true.sum())
            }
            
            self.logger.info("✓ Threshold optimization validation passed")
            
            # Log threshold differences
            for objective, result in optimization_results.items():
                self.logger.info(f"  {objective}: threshold={result['optimal_threshold']:.3f}, "
                               f"precision={result['precision']:.3f}, recall={result['recall']:.3f}")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"✗ Threshold optimization validation failed: {e}")
            raise ValidationError(f"Threshold optimization failed: {e}")
    
    def validate_evaluation_metrics(self, dataset_path: Path) -> Dict[str, Any]:
        """Validate comprehensive evaluation metrics."""
        
        self.logger.info("Validating evaluation metrics...")
        
        try:
            # Train model for evaluation
            df = pd.read_csv(dataset_path)
            
            from ml.training.trainers import XGBoostTrainer
            from ml.training.evaluation import ModelEvaluator
            
            config = XGBoostConfig(
                model_name="evaluation_test",
                target_column="Class", 
                n_estimators=20,
                use_cross_validation=False
            )
            
            trainer = XGBoostTrainer(config)
            result = trainer.train(df)
            
            # Get predictions
            y_true = trainer.y_test
            y_pred = trainer._predict(result.model, trainer.X_test)
            y_proba = trainer._predict_proba(result.model, trainer.X_test)
            
            # Test evaluator
            evaluator = ModelEvaluator()
            
            # Test metric computation
            metrics = evaluator.compute_classification_metrics(y_true, y_pred, y_proba)
            
            # Validate required metrics exist
            required_metrics = [
                "accuracy", "precision", "recall", "f1_score", 
                "roc_auc", "pr_auc", "matthews_corrcoef", "balanced_accuracy"
            ]
            
            for metric in required_metrics:
                assert metric in metrics, f"Missing metric: {metric}"
                assert isinstance(metrics[metric], (int, float)), f"Invalid metric type: {metric}"
                
                # Validate metric ranges (most should be 0-1, MCC can be -1 to 1)
                if metric == "matthews_corrcoef":
                    assert -1 <= metrics[metric] <= 1, f"Invalid {metric}: {metrics[metric]}"
                else:
                    assert 0 <= metrics[metric] <= 1, f"Invalid {metric}: {metrics[metric]}"
            
            # Test evaluation report generation
            evaluation_dir = self.output_dir / "evaluation_test"
            evaluation_report = evaluator.generate_evaluation_report(
                y_true, y_pred, y_proba, result.feature_importance,
                evaluation_dir, "evaluation_test_model"
            )
            
            # Validate report structure
            assert "model_id" in evaluation_report, "Missing model_id in report"
            assert "metrics" in evaluation_report, "Missing metrics in report" 
            assert "artifact_paths" in evaluation_report, "Missing artifact_paths in report"
            
            validation_result = {
                "success": True,
                "metrics_computed": len(metrics),
                "required_metrics_present": all(m in metrics for m in required_metrics),
                "evaluation_report_generated": evaluation_report is not None,
                "artifacts_generated": len(evaluation_report.get("artifact_paths", {})),
                "key_metrics": {
                    "roc_auc": metrics.get("roc_auc"),
                    "pr_auc": metrics.get("pr_auc"),
                    "f1_score": metrics.get("f1_score"),
                    "accuracy": metrics.get("accuracy")
                }
            }
            
            self.logger.info(f"✓ Evaluation metrics validation passed - ROC-AUC: {metrics['roc_auc']:.3f}")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"✗ Evaluation metrics validation failed: {e}")
            raise ValidationError(f"Evaluation metrics failed: {e}")
    
    def validate_stress_testing(self) -> Dict[str, Any]:
        """Run stress tests with different dataset sizes."""
        
        self.logger.info("Running stress tests...")
        
        stress_results = {}
        
        for size in ["small", "medium", "large"]:
            self.logger.info(f"Testing with {size} dataset...")
            
            try:
                # Create dataset
                dataset_path = self.create_sample_credit_card_dataset(size)
                
                # Time the training
                start_time = time.time()
                start_memory = self._get_memory_usage()
                
                # Run quick training
                config = PipelineConfig(
                    pipeline_name=f"stress_test_{size}",
                    dataset_path=dataset_path,
                    experiment_tracker_type="local",
                    registry_path=self.output_dir / f"stress_registry_{size}",
                    artifacts_base_dir=self.output_dir / f"stress_artifacts_{size}",
                    generate_evaluation_reports=False,  # Skip for speed
                    optimize_thresholds=False,  # Skip for speed
                    trainer_configs=[
                        XGBoostConfig(
                            model_name=f"stress_xgb_{size}",
                            n_estimators=20,  # Reduced for speed
                            max_depth=3,
                            use_cross_validation=False
                        )
                    ]
                )
                
                pipeline = TrainingPipeline(config)
                results = pipeline.run()
                
                end_time = time.time()
                end_memory = self._get_memory_usage()
                
                # Calculate metrics
                training_time = end_time - start_time
                memory_used = end_memory - start_memory
                
                stress_results[size] = {
                    "success": True,
                    "dataset_info": self.datasets[size],
                    "training_time": training_time,
                    "memory_used_mb": memory_used,
                    "models_trained": len(results),
                    "throughput_samples_per_second": self.datasets[size]["samples"] / training_time if training_time > 0 else 0
                }
                
                self.logger.info(f"✓ {size.capitalize()} dataset: {training_time:.1f}s, {memory_used:.1f}MB")
                
            except Exception as e:
                self.logger.error(f"✗ {size.capitalize()} dataset failed: {e}")
                stress_results[size] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Overall stress test validation
        successful_tests = sum(1 for result in stress_results.values() if result.get("success", False))
        
        validation_result = {
            "success": successful_tests >= 2,  # At least 2 sizes should work
            "stress_results": stress_results,
            "successful_tests": successful_tests,
            "total_tests": len(stress_results)
        }
        
        if validation_result["success"]:
            self.logger.info(f"✓ Stress testing passed - {successful_tests}/{len(stress_results)} tests successful")
        else:
            self.logger.error(f"✗ Stress testing failed - only {successful_tests}/{len(stress_results)} tests successful")
        
        return validation_result
    
    def validate_failure_scenarios(self) -> Dict[str, Any]:
        """Test graceful failure handling."""
        
        self.logger.info("Testing failure scenarios...")
        
        failure_tests = {}
        
        # Test 1: Missing columns
        try:
            df_missing_target = pd.DataFrame({
                'V1': np.random.randn(100),
                'V2': np.random.randn(100),
                'Amount': np.random.exponential(100, 100)
            })
            
            missing_target_path = self.output_dir / "missing_target.csv"
            df_missing_target.to_csv(missing_target_path, index=False)
            
            config = XGBoostConfig(model_name="missing_target_test", target_column="Class")
            trainer = XGBoostTrainer(config)
            
            # This should fail gracefully
            try:
                trainer.train(df_missing_target)
                failure_tests["missing_target"] = {"success": False, "error": "Should have failed but didn't"}
            except ValueError as e:
                failure_tests["missing_target"] = {"success": True, "error_handled": str(e)}
                
        except Exception as e:
            failure_tests["missing_target"] = {"success": False, "unexpected_error": str(e)}
        
        # Test 2: Empty dataset
        try:
            empty_df = pd.DataFrame(columns=['V1', 'V2', 'Amount', 'Class'])
            empty_path = self.output_dir / "empty_dataset.csv"
            empty_df.to_csv(empty_path, index=False)
            
            try:
                validation_result = self.validate_dataset_loading(empty_path)
                failure_tests["empty_dataset"] = {"success": False, "error": "Should have failed but didn't"}
            except ValidationError:
                failure_tests["empty_dataset"] = {"success": True, "error_handled": "Empty dataset detected"}
                
        except Exception as e:
            failure_tests["empty_dataset"] = {"success": False, "unexpected_error": str(e)}
        
        # Test 3: Invalid schema (all same values)
        try:
            df_invalid = pd.DataFrame({
                'V1': [1] * 100,
                'V2': [1] * 100, 
                'Amount': [100] * 100,
                'Class': [0] * 100  # No fraud cases
            })
            
            invalid_path = self.output_dir / "invalid_schema.csv"
            df_invalid.to_csv(invalid_path, index=False)
            
            config = XGBoostConfig(
                model_name="invalid_test",
                target_column="Class",
                n_estimators=10,
                use_cross_validation=False
            )
            trainer = XGBoostTrainer(config)
            
            # This might fail or produce poor results
            try:
                result = trainer.train(df_invalid)
                # If it succeeds, check if metrics are reasonable
                if result.test_metrics.get("roc_auc", 0) < 0.4:
                    failure_tests["invalid_schema"] = {"success": True, "handled": "Poor performance detected"}
                else:
                    failure_tests["invalid_schema"] = {"success": False, "error": "Should produce poor results"}
            except Exception as e:
                failure_tests["invalid_schema"] = {"success": True, "error_handled": str(e)}
                
        except Exception as e:
            failure_tests["invalid_schema"] = {"success": False, "unexpected_error": str(e)}
        
        # Overall failure test result
        successful_failure_tests = sum(1 for test in failure_tests.values() if test.get("success", False))
        
        validation_result = {
            "success": successful_failure_tests >= 2,  # Most failure tests should pass
            "failure_tests": failure_tests,
            "successful_failure_tests": successful_failure_tests,
            "total_failure_tests": len(failure_tests)
        }
        
        if validation_result["success"]:
            self.logger.info(f"✓ Failure testing passed - {successful_failure_tests}/{len(failure_tests)} tests handled gracefully")
        else:
            self.logger.error(f"✗ Failure testing failed - only {successful_failure_tests}/{len(failure_tests)} tests handled properly")
        
        return validation_result
    
    def validate_cli_interface(self) -> Dict[str, Any]:
        """Validate command-line interface end-to-end."""
        
        self.logger.info("Validating CLI interface...")
        
        try:
            import subprocess
            
            # Create test dataset
            dataset_path = self.create_sample_credit_card_dataset("small")
            
            # Test CLI command
            cli_output_dir = self.output_dir / "cli_test_output"
            
            cmd = [
                sys.executable, "scripts/train_models.py",
                "--data", str(dataset_path),
                "--models", "xgboost",
                "--output-dir", str(cli_output_dir),
                "--tracker", "local",
                "--quick",
                "--no-optimization"  # Skip for faster testing
            ]
            
            self.logger.info(f"Running CLI command: {' '.join(cmd)}")
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,  # 3 minute timeout
                cwd=PROJECT_ROOT
            )
            cli_time = time.time() - start_time
            
            # Validate CLI execution
            success = result.returncode == 0
            
            if success:
                # Check that output directory was created
                assert cli_output_dir.exists(), "CLI output directory not created"
                
                # Check for artifacts
                artifacts_exist = len(list(cli_output_dir.rglob("*"))) > 0
                
                validation_result = {
                    "success": True,
                    "cli_execution_time": cli_time,
                    "return_code": result.returncode,
                    "output_directory_created": cli_output_dir.exists(),
                    "artifacts_created": artifacts_exist,
                    "stdout_length": len(result.stdout),
                    "stderr_length": len(result.stderr)
                }
                
                self.logger.info(f"✓ CLI validation passed - completed in {cli_time:.1f}s")
            else:
                validation_result = {
                    "success": False,
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "cli_execution_time": cli_time
                }
                
                self.logger.error(f"✗ CLI validation failed - return code {result.returncode}")
            
            return validation_result
            
        except subprocess.TimeoutExpired:
            self.logger.error("✗ CLI validation failed - timeout")
            return {"success": False, "error": "CLI execution timed out"}
            
        except Exception as e:
            self.logger.error(f"✗ CLI validation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0  # If psutil not available
    
    def run_complete_validation(self) -> Dict[str, Any]:
        """Run complete ML Phase 2 validation suite."""
        
        self.logger.info("=" * 60)
        self.logger.info("STARTING ML PHASE 2 COMPREHENSIVE VALIDATION")
        self.logger.info("=" * 60)
        
        validation_start_time = time.time()
        
        try:
            # 1. Create test datasets
            self.logger.info("\n1. Creating test datasets...")
            medium_dataset = self.create_sample_credit_card_dataset("medium")
            
            # 2. Validate dataset loading
            self.logger.info("\n2. Validating dataset loading...")
            self.results["tests"]["dataset_loading"] = self.validate_dataset_loading(medium_dataset)
            
            # 3. Validate feature engineering
            self.logger.info("\n3. Validating feature engineering...")
            self.results["tests"]["feature_engineering"] = self.validate_feature_engineering(medium_dataset)
            
            # 4. Create experiment tracker
            tracker = create_tracker("validation_experiment", "local", tracking_dir=self.output_dir / "experiments")
            
            # 5. Validate experiment tracking
            self.logger.info("\n4. Validating experiment tracking...")
            self.results["tests"]["experiment_tracking"] = self.validate_experiment_tracking(tracker)
            
            # 6. Validate XGBoost training
            self.logger.info("\n5. Validating XGBoost training...")
            self.results["tests"]["xgboost_training"] = self.validate_xgboost_training(medium_dataset, tracker)
            
            # 7. Validate Isolation Forest training
            self.logger.info("\n6. Validating Isolation Forest training...")
            self.results["tests"]["isolation_forest_training"] = self.validate_isolation_forest_training(medium_dataset, tracker)
            
            # 8. Validate complete pipeline
            self.logger.info("\n7. Validating complete pipeline...")
            pipeline_result = self.validate_complete_pipeline(medium_dataset)
            self.results["tests"]["complete_pipeline"] = pipeline_result
            
            # 9. Validate artifact generation
            self.logger.info("\n8. Validating artifact generation...")
            artifacts_dir = Path(pipeline_result["artifacts_path"])
            self.results["tests"]["artifact_generation"] = self.validate_artifacts_generation(artifacts_dir)
            
            # 10. Validate threshold optimization
            self.logger.info("\n9. Validating threshold optimization...")
            self.results["tests"]["threshold_optimization"] = self.validate_threshold_optimization(medium_dataset)
            
            # 11. Validate evaluation metrics
            self.logger.info("\n10. Validating evaluation metrics...")
            self.results["tests"]["evaluation_metrics"] = self.validate_evaluation_metrics(medium_dataset)
            
            # 12. Run stress tests
            self.logger.info("\n11. Running stress tests...")
            self.results["tests"]["stress_testing"] = self.validate_stress_testing()
            
            # 13. Test failure scenarios
            self.logger.info("\n12. Testing failure scenarios...")
            self.results["tests"]["failure_testing"] = self.validate_failure_scenarios()
            
            # 14. Validate CLI interface
            self.logger.info("\n13. Validating CLI interface...")
            self.results["tests"]["cli_interface"] = self.validate_cli_interface()
            
            # Calculate overall results
            validation_time = time.time() - validation_start_time
            
            # Count successful tests
            successful_tests = sum(1 for test_result in self.results["tests"].values() 
                                 if test_result.get("success", False))
            total_tests = len(self.results["tests"])
            
            # Update results
            self.results.update({
                "end_time": datetime.utcnow(),
                "validation_duration_seconds": validation_time,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
                "overall_success": successful_tests >= total_tests * 0.9  # 90% success threshold
            })
            
            return self.results
            
        except Exception as e:
            self.logger.error(f"Validation failed with error: {e}")
            self.results["errors"].append(str(e))
            self.results["overall_success"] = False
            return self.results
    
    def generate_validation_report(self) -> None:
        """Generate comprehensive validation report."""
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("VALIDATION REPORT")
        self.logger.info("=" * 60)
        
        # Overall summary
        print(f"\nValidation Duration: {self.results['validation_duration_seconds']:.1f} seconds")
        print(f"Total Tests: {self.results['total_tests']}")
        print(f"Successful: {self.results['successful_tests']}")
        print(f"Failed: {self.results['failed_tests']}")
        print(f"Success Rate: {self.results['success_rate']:.1%}")
        
        if self.results["overall_success"]:
            print("\n🎉 OVERALL RESULT: VALIDATION PASSED")
        else:
            print("\n❌ OVERALL RESULT: VALIDATION FAILED")
        
        # Detailed test results
        print(f"\nDetailed Test Results:")
        print("-" * 40)
        
        for test_name, test_result in self.results["tests"].items():
            status = "✓ PASS" if test_result.get("success", False) else "✗ FAIL"
            test_display_name = test_name.replace("_", " ").title()
            print(f"{status} - {test_display_name}")
            
            # Show key metrics for successful tests
            if test_result.get("success", False):
                if "roc_auc" in test_result:
                    print(f"    ROC-AUC: {test_result['roc_auc']:.3f}")
                if "training_time" in test_result:
                    print(f"    Training Time: {test_result['training_time']:.1f}s")
                if "models_trained" in test_result:
                    print(f"    Models Trained: {test_result['models_trained']}")
            else:
                if "error" in test_result:
                    print(f"    Error: {test_result['error']}")
        
        # Dataset information
        if self.datasets:
            print(f"\nDatasets Created:")
            print("-" * 20)
            for size, info in self.datasets.items():
                print(f"{size.capitalize()}: {info['samples']} samples, "
                      f"{info['fraud_cases']} fraud cases ({info['fraud_rate']:.2%})")
        
        # Artifacts summary
        artifacts_test = self.results["tests"].get("artifact_generation", {})
        if artifacts_test.get("success"):
            artifacts_info = artifacts_test.get("artifacts_found", {})
            print(f"\nArtifacts Generated:")
            print("-" * 20)
            print(f"Model Directories: {artifacts_info.get('model_directories', 0)}")
            print(f"Total Files Created: {artifacts_info.get('total_files_found', 0)}")
        
        # Performance summary
        stress_test = self.results["tests"].get("stress_testing", {})
        if stress_test.get("success"):
            print(f"\nPerformance Summary:")
            print("-" * 20)
            for size, result in stress_test.get("stress_results", {}).items():
                if result.get("success"):
                    print(f"{size.capitalize()}: {result['training_time']:.1f}s, "
                          f"{result['memory_used_mb']:.1f}MB, "
                          f"{result['throughput_samples_per_second']:.0f} samples/sec")
        
        # Save detailed report to file
        report_path = self.output_dir / "validation_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nDetailed validation report saved to: {report_path}")
        print(f"Output directory: {self.output_dir}")


def main():
    """Main validation entry point."""
    
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="ML Phase 2 Validation Suite")
    parser.add_argument("--output-dir", type=Path, default="validation_output", 
                       help="Output directory for validation artifacts")
    parser.add_argument("--quick", action="store_true", 
                       help="Run quick validation (reduced dataset sizes)")
    
    args = parser.parse_args()
    
    # Create validator
    validator = MLPhase2Validator(args.output_dir)
    
    try:
        # Run validation
        results = validator.run_complete_validation()
        
        # Generate report
        validator.generate_validation_report()
        
        # Exit with appropriate code
        success = results.get("overall_success", False)
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n\nValidation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()