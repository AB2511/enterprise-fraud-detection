"""
XGBoost Trainer

Primary supervised fraud classifier using XGBoost with comprehensive
hyperparameter management, early stopping, and feature importance analysis.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
import yaml

try:
    import xgboost as xgb

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from ml.training.base import BaseTrainer, TrainingConfig
from ml.training.tracking import ExperimentTracker


@dataclass
class XGBoostConfig(TrainingConfig):
    """XGBoost-specific training configuration."""

    # XGBoost hyperparameters
    n_estimators: int = 100
    max_depth: int = 6
    learning_rate: float = 0.1
    subsample: float = 1.0
    colsample_bytree: float = 1.0
    colsample_bylevel: float = 1.0
    colsample_bynode: float = 1.0

    # Regularization
    reg_alpha: float = 0.0  # L1 regularization
    reg_lambda: float = 1.0  # L2 regularization
    gamma: float = 0.0  # Minimum split loss

    # Tree construction
    min_child_weight: int = 1
    max_delta_step: int = 0

    # Learning objective
    objective: str = "binary:logistic"
    eval_metric: str = "auc"

    # Performance
    n_jobs: int = -1
    tree_method: str = "auto"  # "auto", "exact", "approx", "hist", "gpu_hist"

    # Early stopping
    early_stopping_rounds: int | None = 10
    validation_fraction: float = 0.1

    # Class imbalance
    scale_pos_weight: float | None = None  # Auto-calculate if None

    # Advanced parameters
    grow_policy: str = "depthwise"  # "depthwise", "lossguide"
    max_leaves: int = 0
    max_bin: int = 256

    # Verbosity
    verbosity: int = 1

    def __post_init__(self):
        # Don't call super().__post_init__() as base class doesn't have it
        # Don't override model_name if it was provided

        # Auto-calculate scale_pos_weight if not provided
        if self.scale_pos_weight is None:
            # Will be calculated during training based on actual data
            pass

    def to_xgb_params(self) -> dict[str, Any]:
        """Convert to XGBoost parameter dictionary."""
        return {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "colsample_bylevel": self.colsample_bylevel,
            "colsample_bynode": self.colsample_bynode,
            "reg_alpha": self.reg_alpha,
            "reg_lambda": self.reg_lambda,
            "gamma": self.gamma,
            "min_child_weight": self.min_child_weight,
            "max_delta_step": self.max_delta_step,
            "objective": self.objective,
            "eval_metric": self.eval_metric,
            "n_jobs": self.n_jobs,
            "tree_method": self.tree_method,
            "scale_pos_weight": self.scale_pos_weight,
            "grow_policy": self.grow_policy,
            "max_leaves": self.max_leaves,
            "max_bin": self.max_bin,
            "verbosity": self.verbosity,
            "random_state": self.random_seed,
        }

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "XGBoostConfig":
        """Load XGBoost configuration from YAML file."""
        with open(yaml_path) as f:
            config_dict = yaml.safe_load(f)

        return cls(**config_dict)

    def save_yaml(self, yaml_path: str | Path):
        """Save configuration to YAML file."""
        config_dict = self.to_dict()

        with open(yaml_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)


class XGBoostTrainer(BaseTrainer):
    """
    XGBoost trainer for fraud detection.

    Features:
    - Comprehensive hyperparameter management
    - Early stopping with validation
    - Feature importance analysis
    - Class imbalance handling
    - GPU support (if available)
    - MLflow integration
    """

    def __init__(self, config: XGBoostConfig, experiment_tracker: ExperimentTracker | None = None):
        if not XGBOOST_AVAILABLE:
            raise ImportError(
                "XGBoost is required for XGBoostTrainer. " "Install with: pip install xgboost"
            )

        super().__init__(config, experiment_tracker)
        self.xgb_config = config

        # Training artifacts
        self.feature_importance_ = None
        self.eval_results_ = {}
        self.best_iteration_ = None

    def _create_model(self) -> xgb.XGBClassifier:
        """Create XGBoost classifier with configuration."""

        # Calculate scale_pos_weight if not provided
        scale_pos_weight = self.xgb_config.scale_pos_weight
        if scale_pos_weight is None and self.y_train is not None:
            n_negative = np.sum(self.y_train == 0)
            n_positive = np.sum(self.y_train == 1)
            scale_pos_weight = n_negative / n_positive if n_positive > 0 else 1.0

            self.logger.info(f"Auto-calculated scale_pos_weight: {scale_pos_weight:.4f}")
            self.xgb_config.scale_pos_weight = scale_pos_weight

        # Get XGBoost parameters
        xgb_params = self.xgb_config.to_xgb_params()

        # Remove parameters that should not be passed to constructor
        constructor_params = xgb_params.copy()

        # Create model
        model = xgb.XGBClassifier(**constructor_params)

        self.logger.info("Created XGBoost classifier")
        self.logger.debug(f"XGBoost parameters: {xgb_params}")

        return model

    def _fit_model(self, X: pd.DataFrame, y: pd.Series) -> xgb.XGBClassifier:
        """Fit XGBoost model with early stopping and evaluation."""

        model = self._create_model()

        # Prepare evaluation set for early stopping
        eval_set = None
        early_stopping_rounds = None

        if self.xgb_config.early_stopping_rounds is not None and self.X_val is not None:
            eval_set = [(X, y), (self.X_val, self.y_val)]
            early_stopping_rounds = self.xgb_config.early_stopping_rounds

            self.logger.info(f"Early stopping enabled with {early_stopping_rounds} rounds")

        # Fit model
        fit_params = {
            "eval_set": eval_set,
            "early_stopping_rounds": early_stopping_rounds,
            "verbose": False,  # Control verbosity through config
        }

        # Remove None values
        fit_params = {k: v for k, v in fit_params.items() if v is not None}

        self.logger.info("Fitting XGBoost model...")
        model.fit(X, y, **fit_params)

        # Store training artifacts
        if hasattr(model, "evals_result_"):
            self.eval_results_ = model.evals_result_

        if hasattr(model, "best_iteration"):
            self.best_iteration_ = model.best_iteration
            self.logger.info(f"Best iteration: {self.best_iteration_}")

        # Compute feature importance
        self.feature_importance_ = self._extract_feature_importance(model)

        self.logger.info(f"XGBoost model fitted with {model.n_estimators} estimators")

        return model

    def _predict(self, model: xgb.XGBClassifier, X: pd.DataFrame) -> np.ndarray:
        """Generate binary predictions."""
        return model.predict(X)

    def _predict_proba(self, model: xgb.XGBClassifier, X: pd.DataFrame) -> np.ndarray:
        """Generate prediction probabilities."""
        probabilities = model.predict_proba(X)
        # Return probabilities for positive class (fraud)
        return probabilities[:, 1] if probabilities.shape[1] > 1 else probabilities.ravel()

    def _get_feature_importance(self, model: xgb.XGBClassifier) -> dict[str, float] | None:
        """Extract feature importance from XGBoost model."""
        if self.feature_importance_ is not None:
            return self.feature_importance_

        return self._extract_feature_importance(model)

    def _extract_feature_importance(self, model: xgb.XGBClassifier) -> dict[str, float]:
        """Extract different types of feature importance from XGBoost."""

        feature_importance = {}

        try:
            # Get feature importance (default is 'weight' - number of times feature is used)
            importance_weight = model.feature_importances_

            # Get gain-based importance (average gain across all splits)
            model.get_booster().feature_names = self.feature_names
            importance_gain = model.get_booster().get_score(importance_type="gain")

            # Get cover-based importance (average coverage across all splits)
            importance_cover = model.get_booster().get_score(importance_type="cover")

            # Store all importance types
            for i, feature in enumerate(self.feature_names):
                feature_importance[feature] = {
                    "weight": float(importance_weight[i]) if i < len(importance_weight) else 0.0,
                    "gain": importance_gain.get(feature, 0.0),
                    "cover": importance_cover.get(feature, 0.0),
                }

            # For compatibility, return gain-based importance as main score
            return {feature: scores["gain"] for feature, scores in feature_importance.items()}

        except Exception as e:
            self.logger.warning(f"Could not extract feature importance: {e}")
            return {}

    def get_training_curves(self) -> dict[str, np.ndarray]:
        """Get training curves from evaluation results."""
        if not self.eval_results_:
            return {}

        curves = {}

        for eval_set_name, metrics in self.eval_results_.items():
            for metric_name, values in metrics.items():
                curve_name = f"{eval_set_name}_{metric_name}"
                curves[curve_name] = np.array(values)

        return curves

    def plot_training_curves(self, save_path: Path | None = None) -> Optional["plt.Figure"]:
        """Plot training curves if evaluation results are available."""

        curves = self.get_training_curves()
        if not curves:
            self.logger.warning("No evaluation results available for plotting")
            return None

        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(10, 6))

            for curve_name, values in curves.items():
                ax.plot(values, label=curve_name)

            ax.set_xlabel("Iteration")
            ax.set_ylabel("Metric Value")
            ax.set_title("XGBoost Training Curves")
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Mark best iteration if available
            if self.best_iteration_ is not None:
                ax.axvline(
                    x=self.best_iteration_,
                    color="red",
                    linestyle="--",
                    label=f"Best Iteration: {self.best_iteration_}",
                )
                ax.legend()

            plt.tight_layout()

            if save_path:
                fig.savefig(save_path, dpi=300, bbox_inches="tight")
                self.logger.info(f"Training curves saved to {save_path}")

            return fig

        except ImportError:
            self.logger.warning("matplotlib not available for plotting")
            return None

    def get_tree_importance_plot(self, max_num_features: int = 20, save_path: Path | None = None):
        """Plot feature importance using XGBoost's built-in plotting."""

        if self.model is None:
            raise ValueError("Model must be trained before plotting importance")

        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(10, max_num_features * 0.4))

            xgb.plot_importance(
                self.model,
                ax=ax,
                max_num_features=max_num_features,
                importance_type="gain",
                show_values=True,
            )

            plt.title("XGBoost Feature Importance (Gain)")
            plt.tight_layout()

            if save_path:
                fig.savefig(save_path, dpi=300, bbox_inches="tight")
                self.logger.info(f"Feature importance plot saved to {save_path}")

            return fig

        except ImportError:
            self.logger.warning("matplotlib not available for plotting")
            return None

    def explain_predictions(
        self, X: pd.DataFrame, sample_indices: list[int] | None = None, max_samples: int = 10
    ) -> dict[str, Any]:
        """
        Explain predictions using SHAP values (if available).

        Note: SHAP integration is not implemented in this phase.
        This method provides a placeholder for future implementation.
        """
        if self.model is None:
            raise ValueError("Model must be trained before explaining predictions")

        # Select samples to explain
        if sample_indices is None:
            sample_indices = list(range(min(max_samples, len(X))))

        samples = X.iloc[sample_indices]
        predictions = self._predict_proba(self.model, samples)

        # Placeholder explanation (would use SHAP in production)
        explanations = {
            "predictions": predictions.tolist(),
            "sample_indices": sample_indices,
            "note": "SHAP explanations not implemented in this phase",
        }

        return explanations

    def hyperparameter_importance_analysis(self) -> dict[str, float]:
        """
        Analyze hyperparameter importance (placeholder).

        In production, this could use hyperparameter optimization
        frameworks like Optuna or Hyperopt.
        """
        # Placeholder implementation
        important_params = {
            "learning_rate": 0.8,
            "max_depth": 0.7,
            "n_estimators": 0.6,
            "subsample": 0.5,
            "colsample_bytree": 0.4,
            "reg_alpha": 0.3,
            "reg_lambda": 0.3,
            "gamma": 0.2,
        }

        return important_params


def create_default_xgboost_config(**overrides) -> XGBoostConfig:
    """Create a default XGBoost configuration with optional overrides."""

    default_config = {
        "model_name": "xgboost",
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "early_stopping": True,
        "early_stopping_rounds": 10,
        "random_seed": 42,
    }

    default_config.update(overrides)
    return XGBoostConfig(**default_config)


def create_fast_xgboost_config(**overrides) -> XGBoostConfig:
    """Create a fast XGBoost configuration for development/testing."""

    fast_config = {
        "model_name": "xgboost_fast",
        "n_estimators": 50,
        "max_depth": 4,
        "learning_rate": 0.2,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "early_stopping": True,
        "early_stopping_rounds": 5,
        "random_seed": 42,
    }

    fast_config.update(overrides)
    return XGBoostConfig(**fast_config)


def create_robust_xgboost_config(**overrides) -> XGBoostConfig:
    """Create a robust XGBoost configuration for production."""

    robust_config = {
        "model_name": "xgboost_robust",
        "n_estimators": 500,
        "max_depth": 8,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "colsample_bylevel": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "gamma": 0.1,
        "min_child_weight": 3,
        "early_stopping": True,
        "early_stopping_rounds": 20,
        "random_seed": 42,
    }

    robust_config.update(overrides)
    return XGBoostConfig(**robust_config)
