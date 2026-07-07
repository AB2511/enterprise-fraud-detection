"""
Model Training Package

Production-grade model training pipeline for fraud detection.

This package provides:
- Base training framework with MLflow integration
- Model-specific trainers (XGBoost, Isolation Forest)
- Training pipeline orchestration
- Experiment tracking with MLflow
- Model registry
- Evaluation framework
- Artifact management
"""

from ml.training.base import BaseTrainer, TrainingConfig, TrainingResult
from ml.training.evaluation import EvaluationMetrics, ModelEvaluator
from ml.training.optimization import OptimizationConfig, ThresholdOptimizer
from ml.training.pipeline import ExperimentRunner, TrainingPipeline
from ml.training.registry import ModelArtifacts, ModelRegistry, TrainingMetadata
from ml.training.tracking import ExperimentTracker, LocalTracker, MLflowTracker
from ml.training.trainers.isolation_forest_trainer import (
    IsolationForestConfig,
    IsolationForestTrainer,
)
from ml.training.trainers.xgboost_trainer import XGBoostConfig, XGBoostTrainer

__all__ = [
    # Base framework
    "BaseTrainer",
    "TrainingConfig",
    "TrainingResult",
    # Trainers
    "XGBoostTrainer",
    "XGBoostConfig",
    "IsolationForestTrainer",
    "IsolationForestConfig",
    # Pipeline and experiments
    "TrainingPipeline",
    "ExperimentRunner",
    # Experiment tracking
    "ExperimentTracker",
    "MLflowTracker",
    "LocalTracker",
    # Registry and artifacts
    "ModelRegistry",
    "ModelArtifacts",
    "TrainingMetadata",
    # Evaluation
    "ModelEvaluator",
    "EvaluationMetrics",
    # Optimization
    "ThresholdOptimizer",
    "OptimizationConfig",
]
