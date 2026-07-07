"""
Model Evaluation Framework

Comprehensive evaluation metrics and reporting for fraud detection models.
Includes classification metrics, calibration analysis, and visualization.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

try:
    from sklearn.metrics import calibration_curve

    CALIBRATION_AVAILABLE = True
except ImportError:
    CALIBRATION_AVAILABLE = False

try:
    from sklearn.calibration import CalibrationDisplay

    CALIBRATION_DISPLAY_AVAILABLE = True
except ImportError:
    CALIBRATION_DISPLAY_AVAILABLE = False
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ml.utils.logging_config import get_logger


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics."""

    # Basic classification metrics
    accuracy: float
    precision: float
    recall: float
    f1_score: float

    # Advanced metrics
    roc_auc: float
    pr_auc: float
    matthews_corr: float
    balanced_accuracy: float

    # Confusion matrix
    tn: int
    fp: int
    fn: int
    tp: int

    # Additional metrics
    specificity: float
    npv: float  # Negative Predictive Value
    fpr: float  # False Positive Rate
    fnr: float  # False Negative Rate

    # Calibration metrics
    brier_score: float | None = None
    calibration_error: float | None = None

    def to_dict(self) -> dict[str, float]:
        """Convert metrics to dictionary."""
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "roc_auc": self.roc_auc,
            "pr_auc": self.pr_auc,
            "matthews_corr": self.matthews_corr,
            "balanced_accuracy": self.balanced_accuracy,
            "specificity": self.specificity,
            "npv": self.npv,
            "fpr": self.fpr,
            "fnr": self.fnr,
            "tn": float(self.tn),
            "fp": float(self.fp),
            "fn": float(self.fn),
            "tp": float(self.tp),
            "brier_score": self.brier_score,
            "calibration_error": self.calibration_error,
        }


class ModelEvaluator:
    """
    Comprehensive model evaluation framework.

    Provides methods for:
    - Classification metrics computation
    - Threshold optimization
    - Visualization generation
    - Calibration analysis
    """

    def __init__(self):
        self.logger = get_logger("ml.training.ModelEvaluator")

    def compute_classification_metrics(
        self,
        y_true: np.ndarray | pd.Series,
        y_pred: np.ndarray | pd.Series,
        y_proba: np.ndarray | pd.Series | None = None,
        threshold: float = 0.5,
    ) -> dict[str, float]:
        """
        Compute comprehensive classification metrics.

        Args:
            y_true: True labels
            y_pred: Predicted labels or probabilities
            y_proba: Prediction probabilities (if y_pred is labels)
            threshold: Classification threshold

        Returns:
            Dictionary of metrics
        """
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)

        # If y_pred contains probabilities, convert to binary predictions
        if y_proba is None and ((y_pred >= 0) & (y_pred <= 1)).all() and len(np.unique(y_pred)) > 2:
            y_proba = y_pred
            y_pred = (y_pred >= threshold).astype(int)
        else:
            y_proba = np.asarray(y_proba) if y_proba is not None else None

        # Basic metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, len(y_true))

        # Derived metrics
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0

        # Advanced metrics
        matthews_corr = matthews_corrcoef(y_true, y_pred)
        balanced_acc = balanced_accuracy_score(y_true, y_pred)

        metrics = {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "matthews_corr": matthews_corr,
            "balanced_accuracy": balanced_acc,
            "specificity": specificity,
            "npv": npv,
            "fpr": fpr,
            "fnr": fnr,
            "tn": float(tn),
            "fp": float(fp),
            "fn": float(fn),
            "tp": float(tp),
        }

        # Probability-based metrics
        if y_proba is not None:
            try:
                roc_auc = roc_auc_score(y_true, y_proba)
                pr_auc = average_precision_score(y_true, y_proba)
                brier_score = np.mean((y_proba - y_true) ** 2)

                metrics.update(
                    {
                        "roc_auc": roc_auc,
                        "pr_auc": pr_auc,
                        "brier_score": brier_score,
                    }
                )

                # Calibration error
                try:
                    calibration_error = self._compute_calibration_error(y_true, y_proba)
                    metrics["calibration_error"] = calibration_error
                except Exception as e:
                    self.logger.warning(f"Could not compute calibration error: {e}")

            except Exception as e:
                self.logger.warning(f"Could not compute probability-based metrics: {e}")

        return metrics

    def _compute_calibration_error(
        self, y_true: np.ndarray, y_proba: np.ndarray, n_bins: int = 10
    ) -> float:
        """
        Compute Expected Calibration Error (ECE).

        Args:
            y_true: True labels
            y_proba: Predicted probabilities
            n_bins: Number of calibration bins

        Returns:
            Expected calibration error
        """
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]

        ece = 0
        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            in_bin = (y_proba > bin_lower) & (y_proba <= bin_upper)
            prop_in_bin = in_bin.mean()

            if prop_in_bin > 0:
                accuracy_in_bin = y_true[in_bin].mean()
                avg_confidence_in_bin = y_proba[in_bin].mean()
                ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin

        return ece

    def generate_classification_report(
        self,
        y_true: np.ndarray | pd.Series,
        y_pred: np.ndarray | pd.Series,
        target_names: list[str] | None = None,
    ) -> str:
        """
        Generate detailed classification report.

        Args:
            y_true: True labels
            y_pred: Predicted labels
            target_names: Names for target classes

        Returns:
            Classification report string
        """
        return classification_report(
            y_true, y_pred, target_names=target_names or ["Normal", "Fraud"], digits=4
        )

    def plot_roc_curve(
        self,
        y_true: np.ndarray | pd.Series,
        y_proba: np.ndarray | pd.Series,
        title: str = "ROC Curve",
        save_path: Path | None = None,
    ) -> tuple[plt.Figure, dict[str, Any]]:
        """
        Plot ROC curve.

        Args:
            y_true: True labels
            y_proba: Predicted probabilities
            title: Plot title
            save_path: Path to save plot

        Returns:
            Tuple of (figure, metrics_dict)
        """
        # Compute ROC curve
        fpr, tpr, thresholds = roc_curve(y_true, y_proba)
        roc_auc = roc_auc_score(y_true, y_proba)

        # Create plot
        fig, ax = plt.subplots(figsize=(8, 6))

        # Plot ROC curve
        ax.plot(fpr, tpr, color="blue", lw=2, label=f"ROC Curve (AUC = {roc_auc:.4f})")
        ax.plot([0, 1], [0, 1], color="red", lw=1, linestyle="--", label="Random Classifier")

        # Formatting
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.set_title(title)
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save if requested
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")
            self.logger.info(f"ROC curve saved to {save_path}")

        metrics = {
            "roc_auc": roc_auc,
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
            "thresholds": thresholds.tolist(),
        }

        return fig, metrics

    def plot_precision_recall_curve(
        self,
        y_true: np.ndarray | pd.Series,
        y_proba: np.ndarray | pd.Series,
        title: str = "Precision-Recall Curve",
        save_path: Path | None = None,
    ) -> tuple[plt.Figure, dict[str, Any]]:
        """
        Plot Precision-Recall curve.

        Args:
            y_true: True labels
            y_proba: Predicted probabilities
            title: Plot title
            save_path: Path to save plot

        Returns:
            Tuple of (figure, metrics_dict)
        """
        # Compute PR curve
        precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
        pr_auc = average_precision_score(y_true, y_proba)

        # Baseline (random classifier)
        baseline = np.sum(y_true) / len(y_true)

        # Create plot
        fig, ax = plt.subplots(figsize=(8, 6))

        # Plot PR curve
        ax.plot(recall, precision, color="blue", lw=2, label=f"PR Curve (AUC = {pr_auc:.4f})")
        ax.axhline(
            y=baseline,
            color="red",
            lw=1,
            linestyle="--",
            label=f"Random Classifier ({baseline:.4f})",
        )

        # Formatting
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel("Recall")
        ax.set_ylabel("Precision")
        ax.set_title(title)
        ax.legend(loc="lower left")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save if requested
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")
            self.logger.info(f"PR curve saved to {save_path}")

        metrics = {
            "pr_auc": pr_auc,
            "precision": precision.tolist(),
            "recall": recall.tolist(),
            "thresholds": thresholds.tolist(),
            "baseline": baseline,
        }

        return fig, metrics

    def plot_confusion_matrix(
        self,
        y_true: np.ndarray | pd.Series,
        y_pred: np.ndarray | pd.Series,
        labels: list[str] | None = None,
        title: str = "Confusion Matrix",
        save_path: Path | None = None,
        normalize: str = "true",
    ) -> tuple[plt.Figure, np.ndarray]:
        """
        Plot confusion matrix.

        Args:
            y_true: True labels
            y_pred: Predicted labels
            labels: Class labels
            title: Plot title
            save_path: Path to save plot
            normalize: Normalization method ("true", "pred", "all", None)

        Returns:
            Tuple of (figure, confusion_matrix)
        """
        # Compute confusion matrix
        cm = confusion_matrix(y_true, y_pred, normalize=normalize)

        # Create plot
        fig, ax = plt.subplots(figsize=(8, 6))

        # Plot heatmap
        sns.heatmap(
            cm,
            annot=True,
            fmt=".4f" if normalize else "d",
            cmap="Blues",
            ax=ax,
            xticklabels=labels or ["Normal", "Fraud"],
            yticklabels=labels or ["Normal", "Fraud"],
        )

        ax.set_title(title)
        ax.set_xlabel("Predicted Label")
        ax.set_ylabel("True Label")

        plt.tight_layout()

        # Save if requested
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")
            self.logger.info(f"Confusion matrix saved to {save_path}")

        return fig, cm

    def plot_calibration_curve(
        self,
        y_true: np.ndarray | pd.Series,
        y_proba: np.ndarray | pd.Series,
        n_bins: int = 10,
        title: str = "Calibration Curve",
        save_path: Path | None = None,
    ) -> tuple[plt.Figure, dict[str, Any]]:
        """
        Plot calibration curve.

        Args:
            y_true: True labels
            y_proba: Predicted probabilities
            n_bins: Number of calibration bins
            title: Plot title
            save_path: Path to save plot

        Returns:
            Tuple of (figure, metrics_dict)
        """
        if not CALIBRATION_AVAILABLE:
            self.logger.warning("Calibration curve not available in this sklearn version")
            # Create empty plot
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.text(
                0.5,
                0.5,
                "Calibration curve not available\n(sklearn version too old)",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            ax.set_title(title)

            if save_path:
                fig.savefig(save_path, dpi=300, bbox_inches="tight")
                plt.close(fig)

            return fig, {"calibration_error": None}

        # Compute calibration curve
        fraction_of_positives, mean_predicted_value = calibration_curve(
            y_true, y_proba, n_bins=n_bins
        )

        # Compute calibration error
        calibration_error = self._compute_calibration_error(y_true, y_proba, n_bins)

        # Create plot
        fig, ax = plt.subplots(figsize=(8, 6))

        # Plot calibration curve
        ax.plot(
            mean_predicted_value,
            fraction_of_positives,
            marker="o",
            linewidth=2,
            label=f"Model (ECE = {calibration_error:.4f})",
        )
        ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect Calibration")

        # Formatting
        ax.set_xlabel("Mean Predicted Probability")
        ax.set_ylabel("Fraction of Positives")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save if requested
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")
            self.logger.info(f"Calibration curve saved to {save_path}")

        metrics = {
            "calibration_error": calibration_error,
            "fraction_of_positives": fraction_of_positives.tolist(),
            "mean_predicted_value": mean_predicted_value.tolist(),
        }

        return fig, metrics

    def plot_feature_importance(
        self,
        feature_importance: dict[str, float],
        top_n: int = 20,
        title: str = "Feature Importance",
        save_path: Path | None = None,
    ) -> plt.Figure:
        """
        Plot feature importance.

        Args:
            feature_importance: Dictionary of feature names and importance scores
            top_n: Number of top features to show
            title: Plot title
            save_path: Path to save plot

        Returns:
            Figure object
        """
        # Sort features by importance
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[
            :top_n
        ]

        features, importance = zip(*sorted_features)

        # Create plot
        fig, ax = plt.subplots(figsize=(10, max(6, len(features) * 0.3)))

        # Create horizontal bar plot
        y_pos = np.arange(len(features))
        bars = ax.barh(y_pos, importance, color="skyblue", edgecolor="navy", alpha=0.7)

        # Formatting
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features)
        ax.invert_yaxis()
        ax.set_xlabel("Importance Score")
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.3)

        # Add value labels on bars
        for i, (bar, imp) in enumerate(zip(bars, importance)):
            ax.text(
                bar.get_width() + 0.01 * max(importance),
                bar.get_y() + bar.get_height() / 2,
                f"{imp:.4f}",
                ha="left",
                va="center",
                fontsize=9,
            )

        plt.tight_layout()

        # Save if requested
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches="tight")
            self.logger.info(f"Feature importance plot saved to {save_path}")

        return fig

    def create_interactive_plots(
        self,
        y_true: np.ndarray | pd.Series,
        y_proba: np.ndarray | pd.Series,
        feature_importance: dict[str, float] | None = None,
        save_path: Path | None = None,
    ) -> go.Figure:
        """
        Create interactive evaluation dashboard using Plotly.

        Args:
            y_true: True labels
            y_proba: Predicted probabilities
            feature_importance: Feature importance scores
            save_path: Path to save HTML file

        Returns:
            Plotly figure object
        """
        # Compute curves
        fpr, tpr, _ = roc_curve(y_true, y_proba)
        precision, recall, _ = precision_recall_curve(y_true, y_proba)

        # Create subplots
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "ROC Curve",
                "Precision-Recall Curve",
                "Calibration Curve",
                "Feature Importance",
            ),
            specs=[
                [{"type": "scatter"}, {"type": "scatter"}],
                [{"type": "scatter"}, {"type": "bar"}],
            ],
        )

        # ROC Curve
        fig.add_trace(
            go.Scatter(
                x=fpr,
                y=tpr,
                name=f"ROC (AUC={roc_auc_score(y_true, y_proba):.3f})",
                line=dict(color="blue", width=2),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=[0, 1], y=[0, 1], name="Random", line=dict(color="red", width=1, dash="dash")
            ),
            row=1,
            col=1,
        )

        # PR Curve
        fig.add_trace(
            go.Scatter(
                x=recall,
                y=precision,
                name=f"PR (AUC={average_precision_score(y_true, y_proba):.3f})",
                line=dict(color="green", width=2),
            ),
            row=1,
            col=2,
        )

        # Calibration curve
        if CALIBRATION_AVAILABLE:
            fraction_pos, mean_pred = calibration_curve(y_true, y_proba, n_bins=10)
            fig.add_trace(
                go.Scatter(
                    x=mean_pred,
                    y=fraction_pos,
                    name="Calibration",
                    mode="markers+lines",
                    marker=dict(size=8),
                ),
                row=2,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=[0, 1],
                    y=[0, 1],
                    name="Perfect Calibration",
                    line=dict(color="gray", width=1, dash="dash"),
                ),
                row=2,
                col=1,
            )
        else:
            # Add placeholder text if calibration not available
            fig.add_annotation(
                text="Calibration curve not available<br>(sklearn version too old)",
                x=0.5,
                y=0.5,
                xref="x3",
                yref="y3",
                showarrow=False,
                font=dict(size=12),
            )

        # Feature importance
        if feature_importance:
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[
                :15
            ]
            features, importance = zip(*sorted_features)

            fig.add_trace(
                go.Bar(
                    x=list(importance),
                    y=list(features),
                    orientation="h",
                    name="Importance",
                    marker=dict(color="lightblue"),
                ),
                row=2,
                col=2,
            )

        # Update layout
        fig.update_layout(height=800, title_text="Model Evaluation Dashboard", showlegend=True)

        # Update axes
        fig.update_xaxes(title_text="False Positive Rate", row=1, col=1)
        fig.update_yaxes(title_text="True Positive Rate", row=1, col=1)
        fig.update_xaxes(title_text="Recall", row=1, col=2)
        fig.update_yaxes(title_text="Precision", row=1, col=2)
        fig.update_xaxes(title_text="Mean Predicted Probability", row=2, col=1)
        fig.update_yaxes(title_text="Fraction of Positives", row=2, col=1)
        fig.update_xaxes(title_text="Importance", row=2, col=2)

        # Save if requested
        if save_path:
            fig.write_html(save_path)
            self.logger.info(f"Interactive dashboard saved to {save_path}")

        return fig

    def generate_evaluation_report(
        self,
        y_true: np.ndarray | pd.Series,
        y_pred: np.ndarray | pd.Series,
        y_proba: np.ndarray | pd.Series | None = None,
        feature_importance: dict[str, float] | None = None,
        output_dir: Path = Path("evaluation_report"),
        model_name: str = "model",
    ) -> dict[str, Any]:
        """
        Generate comprehensive evaluation report with plots and metrics.

        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_proba: Predicted probabilities
            feature_importance: Feature importance scores
            output_dir: Directory to save report artifacts
            model_name: Name of the model for file naming

        Returns:
            Dictionary containing all metrics and artifact paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Generating evaluation report in {output_dir}")

        # Compute metrics
        metrics = self.compute_classification_metrics(y_true, y_pred, y_proba)

        # Generate classification report
        class_report = self.generate_classification_report(y_true, y_pred)

        # Create plots
        artifact_paths = {}

        if y_proba is not None:
            # ROC Curve
            roc_path = output_dir / f"{model_name}_roc_curve.png"
            _, roc_data = self.plot_roc_curve(y_true, y_proba, save_path=roc_path)
            artifact_paths["roc_curve"] = roc_path

            # PR Curve
            pr_path = output_dir / f"{model_name}_pr_curve.png"
            _, pr_data = self.plot_precision_recall_curve(y_true, y_proba, save_path=pr_path)
            artifact_paths["pr_curve"] = pr_path

            # Calibration curve
            cal_path = output_dir / f"{model_name}_calibration.png"
            _, cal_data = self.plot_calibration_curve(y_true, y_proba, save_path=cal_path)
            artifact_paths["calibration_curve"] = cal_path

            # Interactive dashboard
            dash_path = output_dir / f"{model_name}_dashboard.html"
            self.create_interactive_plots(y_true, y_proba, feature_importance, save_path=dash_path)
            artifact_paths["dashboard"] = dash_path

        # Confusion Matrix
        cm_path = output_dir / f"{model_name}_confusion_matrix.png"
        _, cm_data = self.plot_confusion_matrix(y_true, y_pred, save_path=cm_path)
        artifact_paths["confusion_matrix"] = cm_path

        # Feature importance
        if feature_importance:
            fi_path = output_dir / f"{model_name}_feature_importance.png"
            self.plot_feature_importance(feature_importance, save_path=fi_path)
            artifact_paths["feature_importance"] = fi_path

        # Save metrics and classification report
        metrics_path = output_dir / f"{model_name}_metrics.json"
        with open(metrics_path, "w") as f:
            import json

            json.dump(metrics, f, indent=2)
        artifact_paths["metrics"] = metrics_path

        report_path = output_dir / f"{model_name}_classification_report.txt"
        with open(report_path, "w") as f:
            f.write(class_report)
        artifact_paths["classification_report"] = report_path

        self.logger.info(f"Evaluation report completed. Artifacts saved in {output_dir}")

        return {
            "metrics": metrics,
            "classification_report": class_report,
            "artifact_paths": artifact_paths,
        }
