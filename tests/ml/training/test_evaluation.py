"""
Tests for model evaluation functionality.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch

# Set matplotlib backend before any matplotlib imports
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for tests

from ml.training.evaluation import ModelEvaluator, EvaluationMetrics


class TestEvaluationMetrics:
    """Test EvaluationMetrics data class."""
    
    def test_evaluation_metrics_creation(self):
        """Test basic EvaluationMetrics creation."""
        metrics = EvaluationMetrics(
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            roc_auc=0.0,
            pr_auc=0.0,
            matthews_corr=0.0,
            balanced_accuracy=0.0,
            tn=0,
            fp=0,
            fn=0,
            tp=0,
            specificity=0.0,
            npv=0.0,
            fpr=0.0,
            fnr=0.0
        )
        
        # Check default values
        assert metrics.accuracy == 0.0
        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.f1_score == 0.0
        assert metrics.roc_auc == 0.0
        
    def test_evaluation_metrics_with_values(self):
        """Test EvaluationMetrics with values."""
        metrics = EvaluationMetrics(
            accuracy=0.95,
            precision=0.90,
            recall=0.85,
            f1_score=0.87,
            roc_auc=0.92,
            pr_auc=0.88,
            matthews_corr=0.82,
            balanced_accuracy=0.89,
            tn=85,
            fp=5,
            fn=3,
            tp=7,
            specificity=0.94,
            npv=0.97,
            fpr=0.06,
            fnr=0.30
        )
        
        assert metrics.accuracy == 0.95
        assert metrics.precision == 0.90
        assert metrics.recall == 0.85
        assert metrics.f1_score == 0.87
        assert metrics.roc_auc == 0.92
        
    def test_to_dict(self):
        """Test metrics serialization."""
        metrics = EvaluationMetrics(
            accuracy=0.95,
            precision=0.90,
            recall=0.85,
            f1_score=0.87,
            roc_auc=0.92,
            pr_auc=0.88,
            matthews_corr=0.82,
            balanced_accuracy=0.89,
            tn=85,
            fp=5,
            fn=3,
            tp=7,
            specificity=0.94,
            npv=0.97,
            fpr=0.06,
            fnr=0.30
        )
        
        metrics_dict = metrics.to_dict()
        
        assert metrics_dict["accuracy"] == 0.95
        assert metrics_dict["precision"] == 0.90
        assert metrics_dict["roc_auc"] == 0.92
        assert metrics_dict["brier_score"] is None  # None values preserved


class TestModelEvaluator:
    """Test ModelEvaluator functionality."""
    
    def test_evaluator_initialization(self):
        """Test evaluator initialization."""
        evaluator = ModelEvaluator()
        
        assert evaluator.logger is not None
        
    def test_compute_classification_metrics_perfect(self):
        """Test metrics computation with perfect predictions."""
        y_true = np.array([0, 0, 1, 1])
        y_pred = np.array([0, 0, 1, 1])
        
        evaluator = ModelEvaluator()
        metrics = evaluator.compute_classification_metrics(y_true, y_pred)
        
        assert metrics["accuracy"] == 1.0
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1_score"] == 1.0
        
    def test_compute_classification_metrics_realistic(self):
        """Test metrics computation with realistic predictions."""
        # Create realistic scenario: 90% accuracy
        np.random.seed(42)
        y_true = np.random.binomial(1, 0.1, 1000)  # 10% positive class
        
        # Create predictions that are mostly correct
        y_pred = y_true.copy()
        # Flip 10% of predictions
        flip_indices = np.random.choice(len(y_pred), size=int(0.1 * len(y_pred)), replace=False)
        y_pred[flip_indices] = 1 - y_pred[flip_indices]
        
        evaluator = ModelEvaluator()
        metrics = evaluator.compute_classification_metrics(y_true, y_pred)
        
        assert 0.8 <= metrics["accuracy"] <= 1.0
        assert 0.0 <= metrics["precision"] <= 1.0
        assert 0.0 <= metrics["recall"] <= 1.0
        assert 0.0 <= metrics["f1_score"] <= 1.0
        
    def test_compute_classification_metrics_with_probabilities(self):
        """Test metrics computation with prediction probabilities."""
        y_true = np.array([0, 0, 1, 1, 0, 1])
        y_pred = np.array([0, 0, 1, 0, 0, 1])
        y_proba = np.array([0.1, 0.2, 0.8, 0.4, 0.1, 0.9])
        
        evaluator = ModelEvaluator()
        metrics = evaluator.compute_classification_metrics(y_true, y_pred, y_proba)
        
        # Should include ROC-AUC and PR-AUC when probabilities provided
        assert "roc_auc" in metrics
        assert "pr_auc" in metrics
        assert 0.0 <= metrics["roc_auc"] <= 1.0
        assert 0.0 <= metrics["pr_auc"] <= 1.0
        
    def test_compute_binary_metrics(self, sample_predictions):
        """Test binary classification metrics computation."""
        y_true, y_pred, y_proba = sample_predictions
        
        evaluator = ModelEvaluator()
        metrics = evaluator.compute_classification_metrics(y_true, y_pred, y_proba)
        
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "roc_auc" in metrics
        assert "pr_auc" in metrics
        assert "matthews_corr" in metrics
        assert "balanced_accuracy" in metrics
        
        # Check value ranges
        for metric_name, value in metrics.items():
            if metric_name in ["tn", "fp", "fn", "tp"]:
                assert isinstance(value, (int, float)) and value >= 0
            elif metric_name in ["matthews_corr"]:
                assert -1.0 <= value <= 1.0  # MCC can be negative
            else:
                assert 0.0 <= value <= 1.0
            
    def test_compute_confusion_matrix(self, sample_predictions):
        """Test confusion matrix computation."""
        y_true, y_pred, _ = sample_predictions
        
        evaluator = ModelEvaluator()
        metrics = evaluator.compute_classification_metrics(y_true, y_pred)
        
        assert "tn" in metrics
        assert "fp" in metrics
        assert "fn" in metrics  
        assert "tp" in metrics
        
        # Check that confusion matrix values sum correctly
        assert metrics["tn"] + metrics["fp"] + metrics["fn"] + metrics["tp"] == len(y_true)
        
    @patch('matplotlib.figure.Figure.savefig')
    def test_plot_roc_curve(self, mock_savefig, sample_predictions, temp_dir):
        """Test ROC curve plotting."""
        y_true, _, y_proba = sample_predictions
        
        evaluator = ModelEvaluator()
        output_path = temp_dir / "roc_curve.png"
        
        fig, metrics = evaluator.plot_roc_curve(y_true, y_proba, save_path=output_path)
        
        assert fig is not None
        assert "roc_auc" in metrics
        mock_savefig.assert_called_once()
        
    @patch('matplotlib.figure.Figure.savefig')
    def test_plot_precision_recall_curve(self, mock_savefig, sample_predictions, temp_dir):
        """Test Precision-Recall curve plotting."""
        y_true, _, y_proba = sample_predictions
        
        evaluator = ModelEvaluator()
        output_path = temp_dir / "pr_curve.png"
        
        fig, metrics = evaluator.plot_precision_recall_curve(y_true, y_proba, save_path=output_path)
        
        assert fig is not None
        assert "pr_auc" in metrics
        mock_savefig.assert_called_once()
        
    @patch('matplotlib.figure.Figure.savefig')
    def test_plot_confusion_matrix(self, mock_savefig, sample_predictions, temp_dir):
        """Test confusion matrix plotting."""
        y_true, y_pred, _ = sample_predictions
        
        evaluator = ModelEvaluator()
        output_path = temp_dir / "confusion_matrix.png"
        
        fig, cm = evaluator.plot_confusion_matrix(y_true, y_pred, save_path=output_path)
        
        assert fig is not None
        assert cm is not None
        mock_savefig.assert_called_once()
        
    @patch('matplotlib.figure.Figure.savefig')
    def test_plot_calibration_curve(self, mock_savefig, sample_predictions, temp_dir):
        """Test calibration curve plotting."""
        y_true, _, y_proba = sample_predictions
        
        evaluator = ModelEvaluator()
        output_path = temp_dir / "calibration_curve.png"
        
        fig, metrics = evaluator.plot_calibration_curve(y_true, y_proba, save_path=output_path)
        
        # Note: This test might return None fig if calibration_curve is not available in sklearn version
        if fig is not None:
            assert "calibration_error" in metrics
            mock_savefig.assert_called_once()
        
    @patch('matplotlib.figure.Figure.savefig')
    def test_plot_feature_importance(self, mock_savefig, temp_dir):
        """Test feature importance plotting."""
        feature_importance = {
            "feature_1": 0.35,
            "feature_2": 0.25,
            "feature_3": 0.20,
            "feature_4": 0.15,
            "feature_5": 0.05
        }
        
        evaluator = ModelEvaluator()
        output_path = temp_dir / "feature_importance.png"
        
        fig = evaluator.plot_feature_importance(feature_importance, save_path=output_path)
        
        assert fig is not None
        mock_savefig.assert_called_once()
        
    @patch('ml.training.evaluation.ModelEvaluator.plot_roc_curve')
    @patch('ml.training.evaluation.ModelEvaluator.plot_precision_recall_curve')
    @patch('ml.training.evaluation.ModelEvaluator.plot_confusion_matrix')
    @patch('ml.training.evaluation.ModelEvaluator.plot_calibration_curve')
    @patch('ml.training.evaluation.ModelEvaluator.plot_feature_importance')
    def test_generate_evaluation_report(self, mock_plot_fi, mock_plot_cal, mock_plot_cm, 
                                      mock_plot_pr, mock_plot_roc, sample_predictions, temp_dir):
        """Test comprehensive evaluation report generation."""
        y_true, y_pred, y_proba = sample_predictions
        feature_importance = {"f1": 0.5, "f2": 0.3, "f3": 0.2}
        
        # Mock plot methods to return paths
        mock_plot_roc.return_value = (None, {})  # (fig, metrics)
        mock_plot_pr.return_value = (None, {})
        mock_plot_cm.return_value = (None, np.array([[10, 2], [3, 85]]))
        mock_plot_cal.return_value = (None, {})
        mock_plot_fi.return_value = None  # Just fig
        
        evaluator = ModelEvaluator()
        
        report = evaluator.generate_evaluation_report(
            y_true, y_pred, y_proba, feature_importance, temp_dir, "test_model"
        )
        
        # Check report structure
        assert "metrics" in report
        assert "artifact_paths" in report
        assert "classification_report" in report
        
        # Check metrics
        assert "accuracy" in report["metrics"]
        assert "roc_auc" in report["metrics"]
        
        # Check artifact paths
        assert "metrics" in report["artifact_paths"]
        assert "roc_curve" in report["artifact_paths"]
        assert "pr_curve" in report["artifact_paths"]
        assert "confusion_matrix" in report["artifact_paths"]
        
        # Check that plots were called
        mock_plot_roc.assert_called_once()
        mock_plot_pr.assert_called_once()
        mock_plot_cm.assert_called_once()
        mock_plot_cal.assert_called_once()
        mock_plot_fi.assert_called_once()
        
    def test_generate_evaluation_report_minimal(self, sample_predictions, temp_dir):
        """Test evaluation report with minimal inputs (no probabilities, no feature importance)."""
        y_true, y_pred, _ = sample_predictions
        
        evaluator = ModelEvaluator()
        
        with patch.object(evaluator, 'plot_confusion_matrix', return_value=(None, np.array([[10, 2], [3, 85]]))):
            report = evaluator.generate_evaluation_report(
                y_true, y_pred, None, None, temp_dir, "minimal_model"
            )
        
        # Should still generate basic metrics and confusion matrix
        assert "metrics" in report
        assert "accuracy" in report["metrics"]
        assert "confusion_matrix" in report["artifact_paths"]
        
        # Should not have ROC/PR curves since no probabilities provided
        assert "roc_curve" not in report["artifact_paths"]
        assert "pr_curve" not in report["artifact_paths"]
        
    def test_edge_case_all_same_predictions(self):
        """Test edge case where all predictions are the same."""
        y_true = np.array([0, 1, 0, 1, 0])
        y_pred = np.array([0, 0, 0, 0, 0])  # All predict class 0
        
        evaluator = ModelEvaluator()
        metrics = evaluator.compute_classification_metrics(y_true, y_pred)
        
        # Should handle gracefully without errors
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        # Some metrics might be 0 or undefined, but should not raise errors
        
    def test_edge_case_single_class(self):
        """Test edge case with single class in y_true."""
        y_true = np.array([1, 1, 1, 1, 1])  # All positive
        y_pred = np.array([1, 1, 0, 1, 1])
        
        evaluator = ModelEvaluator()
        metrics = evaluator.compute_classification_metrics(y_true, y_pred)
        
        # Should handle gracefully
        assert "accuracy" in metrics
        assert 0.0 <= metrics["accuracy"] <= 1.0