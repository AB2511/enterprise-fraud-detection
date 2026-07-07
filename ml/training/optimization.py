"""
Threshold Optimization

Framework for optimizing classification thresholds based on different business objectives.
Supports cost-based optimization, recall optimization, precision optimization, and F1 optimization.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, f1_score, precision_score, recall_score

from ml.utils.logging_config import get_logger


class OptimizationObjective(Enum):
    """Available optimization objectives."""

    BUSINESS_COST = "business_cost"
    RECALL = "recall"
    PRECISION = "precision"
    F1_SCORE = "f1_score"
    BALANCED_ACCURACY = "balanced_accuracy"
    CUSTOM = "custom"


@dataclass
class BusinessCosts:
    """Business costs for fraud detection."""

    # Cost of false positives (legitimate transactions flagged as fraud)
    false_positive_cost: float = 5.0

    # Cost of false negatives (fraudulent transactions missed)
    false_negative_cost: float = 100.0

    # Cost of true positives (fraud correctly detected - investigation cost)
    true_positive_cost: float = 2.0

    # Cost of true negatives (legitimate transactions correctly passed)
    true_negative_cost: float = 0.0

    def compute_total_cost(self, tp: int, tn: int, fp: int, fn: int) -> float:
        """Compute total business cost given confusion matrix values."""
        return (
            tp * self.true_positive_cost
            + tn * self.true_negative_cost
            + fp * self.false_positive_cost
            + fn * self.false_negative_cost
        )


@dataclass
class OptimizationConfig:
    """Configuration for threshold optimization."""

    objective: OptimizationObjective
    business_costs: BusinessCosts | None = None
    custom_objective: Callable | None = None

    # Search parameters
    threshold_range: tuple[float, float] = (0.01, 0.99)
    n_thresholds: int = 1000

    # Constraints
    min_recall: float | None = None
    min_precision: float | None = None
    max_fpr: float | None = None  # Maximum false positive rate

    # Output
    plot_optimization: bool = True
    save_plots: bool = False

    def __post_init__(self):
        if self.objective == OptimizationObjective.BUSINESS_COST and self.business_costs is None:
            self.business_costs = BusinessCosts()

        if self.objective == OptimizationObjective.CUSTOM and self.custom_objective is None:
            raise ValueError("Custom objective function must be provided for CUSTOM objective")


@dataclass
class OptimizationResult:
    """Results from threshold optimization."""

    optimal_threshold: float
    objective_value: float
    metrics_at_optimal: dict[str, float]

    # Threshold analysis
    thresholds: np.ndarray
    objective_values: np.ndarray
    precision_values: np.ndarray
    recall_values: np.ndarray
    f1_values: np.ndarray

    # Business metrics (if applicable)
    costs: np.ndarray | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "optimal_threshold": self.optimal_threshold,
            "objective_value": self.objective_value,
            "metrics_at_optimal": self.metrics_at_optimal,
            "thresholds": self.thresholds.tolist(),
            "objective_values": self.objective_values.tolist(),
            "precision_values": self.precision_values.tolist(),
            "recall_values": self.recall_values.tolist(),
            "f1_values": self.f1_values.tolist(),
            "costs": self.costs.tolist() if self.costs is not None else None,
        }


class ThresholdOptimizer:
    """
    Threshold optimization framework for fraud detection.

    Supports multiple optimization objectives:
    - Business cost minimization
    - Recall maximization (with precision constraints)
    - Precision maximization (with recall constraints)
    - F1-score maximization
    - Balanced accuracy maximization
    - Custom objective functions
    """

    def __init__(self):
        self.logger = get_logger("ml.training.ThresholdOptimizer")

    def optimize_threshold(
        self,
        y_true: np.ndarray | pd.Series,
        y_proba: np.ndarray | pd.Series,
        config: OptimizationConfig,
    ) -> OptimizationResult:
        """
        Optimize classification threshold based on configuration.

        Args:
            y_true: True binary labels
            y_proba: Predicted probabilities for positive class
            config: Optimization configuration

        Returns:
            OptimizationResult with optimal threshold and metrics
        """
        y_true = np.asarray(y_true)
        y_proba = np.asarray(y_proba)

        self.logger.info(f"Optimizing threshold with objective: {config.objective.value}")

        # Generate threshold range
        thresholds = np.linspace(
            config.threshold_range[0], config.threshold_range[1], config.n_thresholds
        )

        # Compute metrics for all thresholds
        results = self._compute_threshold_metrics(y_true, y_proba, thresholds, config)

        # Find optimal threshold
        optimal_idx, optimal_value = self._find_optimal_threshold(results, config)
        optimal_threshold = thresholds[optimal_idx]

        # Get metrics at optimal threshold
        metrics_at_optimal = self._compute_metrics_at_threshold(y_true, y_proba, optimal_threshold)

        self.logger.info(f"Optimal threshold: {optimal_threshold:.4f}")
        self.logger.info(f"Objective value: {optimal_value:.4f}")
        self.logger.info(f"Precision: {metrics_at_optimal['precision']:.4f}")
        self.logger.info(f"Recall: {metrics_at_optimal['recall']:.4f}")
        self.logger.info(f"F1-score: {metrics_at_optimal['f1_score']:.4f}")

        # Create result object
        result = OptimizationResult(
            optimal_threshold=optimal_threshold,
            objective_value=optimal_value,
            metrics_at_optimal=metrics_at_optimal,
            thresholds=thresholds,
            objective_values=results["objective_values"],
            precision_values=results["precision_values"],
            recall_values=results["recall_values"],
            f1_values=results["f1_values"],
            costs=results.get("costs"),
        )

        # Generate plots if requested
        if config.plot_optimization:
            self._plot_optimization_results(result, config)

        return result

    def _compute_threshold_metrics(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        thresholds: np.ndarray,
        config: OptimizationConfig,
    ) -> dict[str, np.ndarray]:
        """Compute metrics for all thresholds."""

        n_thresholds = len(thresholds)
        precision_values = np.zeros(n_thresholds)
        recall_values = np.zeros(n_thresholds)
        f1_values = np.zeros(n_thresholds)
        objective_values = np.zeros(n_thresholds)

        # For business cost optimization
        costs = (
            np.zeros(n_thresholds)
            if config.objective == OptimizationObjective.BUSINESS_COST
            else None
        )

        for i, threshold in enumerate(thresholds):
            y_pred = (y_proba >= threshold).astype(int)

            # Basic metrics
            precision_values[i] = precision_score(y_true, y_pred, zero_division=0)
            recall_values[i] = recall_score(y_true, y_pred, zero_division=0)
            f1_values[i] = f1_score(y_true, y_pred, zero_division=0)

            # Objective-specific computations
            if config.objective == OptimizationObjective.BUSINESS_COST:
                # Compute confusion matrix
                tp = np.sum((y_true == 1) & (y_pred == 1))
                tn = np.sum((y_true == 0) & (y_pred == 0))
                fp = np.sum((y_true == 0) & (y_pred == 1))
                fn = np.sum((y_true == 1) & (y_pred == 0))

                cost = config.business_costs.compute_total_cost(tp, tn, fp, fn)
                costs[i] = cost
                objective_values[i] = -cost  # Negative because we minimize cost

            elif config.objective == OptimizationObjective.RECALL:
                objective_values[i] = recall_values[i]

            elif config.objective == OptimizationObjective.PRECISION:
                objective_values[i] = precision_values[i]

            elif config.objective == OptimizationObjective.F1_SCORE:
                objective_values[i] = f1_values[i]

            elif config.objective == OptimizationObjective.BALANCED_ACCURACY:
                objective_values[i] = balanced_accuracy_score(y_true, y_pred)

            elif config.objective == OptimizationObjective.CUSTOM:
                objective_values[i] = config.custom_objective(y_true, y_pred, y_proba, threshold)

        results = {
            "precision_values": precision_values,
            "recall_values": recall_values,
            "f1_values": f1_values,
            "objective_values": objective_values,
        }

        if costs is not None:
            results["costs"] = costs

        return results

    def _find_optimal_threshold(
        self, results: dict[str, np.ndarray], config: OptimizationConfig
    ) -> tuple[int, float]:
        """Find the optimal threshold index and value."""

        objective_values = results["objective_values"]
        precision_values = results["precision_values"]
        recall_values = results["recall_values"]

        # Apply constraints
        valid_mask = np.ones(len(objective_values), dtype=bool)

        if config.min_recall is not None:
            valid_mask &= recall_values >= config.min_recall

        if config.min_precision is not None:
            valid_mask &= precision_values >= config.min_precision

        if config.max_fpr is not None:
            # FPR constraint (would need FPR values computed)
            self.logger.warning("FPR constraint not implemented yet")

        # Check if any thresholds satisfy constraints
        if not np.any(valid_mask):
            self.logger.warning(
                "No thresholds satisfy all constraints. Using unconstrained optimum."
            )
            valid_mask = np.ones(len(objective_values), dtype=bool)

        # Find optimum among valid thresholds
        valid_objectives = objective_values[valid_mask]
        valid_indices = np.where(valid_mask)[0]

        # For business cost, we want minimum cost (maximum negative cost)
        if config.objective == OptimizationObjective.BUSINESS_COST:
            optimal_idx_in_valid = np.argmax(valid_objectives)  # Max negative cost = min cost
        else:
            optimal_idx_in_valid = np.argmax(valid_objectives)  # Maximize metric

        optimal_idx = valid_indices[optimal_idx_in_valid]
        optimal_value = objective_values[optimal_idx]

        return optimal_idx, optimal_value

    def _compute_metrics_at_threshold(
        self, y_true: np.ndarray, y_proba: np.ndarray, threshold: float
    ) -> dict[str, float]:
        """Compute comprehensive metrics at a specific threshold."""

        y_pred = (y_proba >= threshold).astype(int)

        # Confusion matrix
        tp = np.sum((y_true == 1) & (y_pred == 1))
        tn = np.sum((y_true == 0) & (y_pred == 0))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        fn = np.sum((y_true == 1) & (y_pred == 0))

        # Metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

        return {
            "threshold": threshold,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "specificity": specificity,
            "fpr": fpr,
            "tp": int(tp),
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
        }

    def _plot_optimization_results(self, result: OptimizationResult, config: OptimizationConfig):
        """Plot threshold optimization results."""

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        # Plot 1: Objective function vs threshold
        ax1 = axes[0, 0]
        if config.objective == OptimizationObjective.BUSINESS_COST:
            # For cost, plot actual costs (not negative values)
            costs = -result.objective_values if result.costs is None else result.costs
            ax1.plot(result.thresholds, costs, "b-", linewidth=2)
            ax1.axvline(
                result.optimal_threshold,
                color="r",
                linestyle="--",
                label=f"Optimal: {result.optimal_threshold:.3f}",
            )
            ax1.set_ylabel("Total Business Cost")
            ax1.set_title("Business Cost vs Threshold")
        else:
            ax1.plot(result.thresholds, result.objective_values, "b-", linewidth=2)
            ax1.axvline(
                result.optimal_threshold,
                color="r",
                linestyle="--",
                label=f"Optimal: {result.optimal_threshold:.3f}",
            )
            ax1.set_ylabel(f"{config.objective.value.title()} Score")
            ax1.set_title(f"{config.objective.value.title()} vs Threshold")

        ax1.set_xlabel("Threshold")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot 2: Precision and Recall vs threshold
        ax2 = axes[0, 1]
        ax2.plot(result.thresholds, result.precision_values, "g-", label="Precision", linewidth=2)
        ax2.plot(result.thresholds, result.recall_values, "b-", label="Recall", linewidth=2)
        ax2.plot(result.thresholds, result.f1_values, "orange", label="F1-Score", linewidth=2)
        ax2.axvline(
            result.optimal_threshold,
            color="r",
            linestyle="--",
            label=f"Optimal: {result.optimal_threshold:.3f}",
        )
        ax2.set_xlabel("Threshold")
        ax2.set_ylabel("Score")
        ax2.set_title("Precision, Recall, F1 vs Threshold")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Plot 3: Precision-Recall curve with optimal point
        ax3 = axes[1, 0]
        ax3.plot(result.recall_values, result.precision_values, "b-", linewidth=2, label="PR Curve")

        # Mark optimal point
        optimal_precision = result.metrics_at_optimal["precision"]
        optimal_recall = result.metrics_at_optimal["recall"]
        ax3.plot(
            optimal_recall,
            optimal_precision,
            "ro",
            markersize=10,
            label=f"Optimal ({optimal_recall:.3f}, {optimal_precision:.3f})",
        )

        ax3.set_xlabel("Recall")
        ax3.set_ylabel("Precision")
        ax3.set_title("Precision-Recall Curve")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # Plot 4: Confusion matrix components at optimal threshold
        ax4 = axes[1, 1]
        metrics = result.metrics_at_optimal
        components = ["TP", "TN", "FP", "FN"]
        values = [metrics["tp"], metrics["tn"], metrics["fp"], metrics["fn"]]
        colors = ["green", "lightgreen", "orange", "red"]

        bars = ax4.bar(components, values, color=colors, alpha=0.7)
        ax4.set_ylabel("Count")
        ax4.set_title(f"Confusion Matrix at Optimal Threshold ({result.optimal_threshold:.3f})")

        # Add value labels on bars
        for bar, value in zip(bars, values):
            ax4.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.01,
                f"{int(value)}",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        plt.tight_layout()

        if config.save_plots:
            plot_path = Path("threshold_optimization.png")
            fig.savefig(plot_path, dpi=300, bbox_inches="tight")
            self.logger.info(f"Optimization plots saved to {plot_path}")

        return fig

    def grid_search_threshold(
        self,
        y_true: np.ndarray | pd.Series,
        y_proba: np.ndarray | pd.Series,
        param_grid: dict[str, list[Any]],
        scoring: str = "f1_score",
    ) -> dict[str, Any]:
        """
        Perform grid search over threshold optimization parameters.

        Args:
            y_true: True binary labels
            y_proba: Predicted probabilities
            param_grid: Grid of parameters to search
            scoring: Scoring metric for comparison

        Returns:
            Dictionary with best parameters and results
        """
        from itertools import product

        self.logger.info("Starting grid search for threshold optimization")

        # Generate parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(product(*param_values))

        results = []

        for params in param_combinations:
            param_dict = dict(zip(param_names, params))

            try:
                # Create config with current parameters
                config = OptimizationConfig(**param_dict, plot_optimization=False)

                # Optimize threshold
                result = self.optimize_threshold(y_true, y_proba, config)

                # Store result
                result_dict = {
                    "parameters": param_dict,
                    "optimal_threshold": result.optimal_threshold,
                    "score": result.metrics_at_optimal.get(scoring, result.objective_value),
                    "precision": result.metrics_at_optimal["precision"],
                    "recall": result.metrics_at_optimal["recall"],
                    "f1_score": result.metrics_at_optimal["f1_score"],
                }
                results.append(result_dict)

            except Exception as e:
                self.logger.warning(f"Error with parameters {param_dict}: {e}")
                continue

        if not results:
            raise ValueError("No valid parameter combinations found")

        # Find best result
        best_result = max(results, key=lambda x: x["score"])

        self.logger.info(f"Grid search completed. Best score: {best_result['score']:.4f}")
        self.logger.info(f"Best parameters: {best_result['parameters']}")

        return {
            "best_result": best_result,
            "all_results": results,
            "best_config": OptimizationConfig(**best_result["parameters"]),
        }


def create_business_cost_optimizer(
    fp_cost: float = 5.0, fn_cost: float = 100.0, tp_cost: float = 2.0, tn_cost: float = 0.0
) -> OptimizationConfig:
    """
    Create a business cost optimization configuration.

    Args:
        fp_cost: Cost of false positives
        fn_cost: Cost of false negatives
        tp_cost: Cost of true positives
        tn_cost: Cost of true negatives

    Returns:
        OptimizationConfig for business cost optimization
    """
    business_costs = BusinessCosts(
        false_positive_cost=fp_cost,
        false_negative_cost=fn_cost,
        true_positive_cost=tp_cost,
        true_negative_cost=tn_cost,
    )

    return OptimizationConfig(
        objective=OptimizationObjective.BUSINESS_COST, business_costs=business_costs
    )


def create_recall_optimizer(min_precision: float = 0.1) -> OptimizationConfig:
    """Create a recall optimization configuration with precision constraint."""
    return OptimizationConfig(objective=OptimizationObjective.RECALL, min_precision=min_precision)


def create_precision_optimizer(min_recall: float = 0.8) -> OptimizationConfig:
    """Create a precision optimization configuration with recall constraint."""
    return OptimizationConfig(objective=OptimizationObjective.PRECISION, min_recall=min_recall)


def create_f1_optimizer() -> OptimizationConfig:
    """Create an F1-score optimization configuration."""
    return OptimizationConfig(objective=OptimizationObjective.F1_SCORE)
