"""
Isolation Forest Trainer

Secondary unsupervised anomaly detector for fraud detection.
Uses Isolation Forest algorithm to detect outliers without requiring labels.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ml.training.base import BaseTrainer, TrainingConfig
from ml.training.tracking import ExperimentTracker


@dataclass
class IsolationForestConfig(TrainingConfig):
    """Isolation Forest-specific training configuration."""

    # Core Isolation Forest parameters
    n_estimators: int = 100
    max_samples: int | float | str = "auto"
    contamination: float | str = "auto"
    max_features: int | float = 1.0
    bootstrap: bool = False

    # Tree parameters
    random_state: int | None = None

    # Preprocessing
    standardize_features: bool = True
    feature_selection: str | None = None  # "variance", "correlation", None

    # Anomaly score calibration
    calibrate_scores: bool = True
    calibration_method: str = "isotonic"  # "isotonic", "sigmoid"

    # Performance
    n_jobs: int = -1
    verbose: int = 0

    def __post_init__(self):
        # Don't call super().__post_init__() as base class doesn't have it
        # Don't override model_name if it was provided
        if self.random_state is None:
            self.random_state = self.random_seed

    def to_sklearn_params(self) -> dict[str, Any]:
        """Convert to sklearn IsolationForest parameters."""
        return {
            "n_estimators": self.n_estimators,
            "max_samples": self.max_samples,
            "contamination": self.contamination,
            "max_features": self.max_features,
            "bootstrap": self.bootstrap,
            "random_state": self.random_state,
            "n_jobs": self.n_jobs,
            "verbose": self.verbose,
        }

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "IsolationForestConfig":
        """Load Isolation Forest configuration from YAML file."""
        with open(yaml_path) as f:
            config_dict = yaml.safe_load(f)

        return cls(**config_dict)

    def save_yaml(self, yaml_path: str | Path):
        """Save configuration to YAML file."""
        config_dict = self.to_dict()

        with open(yaml_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)


class IsolationForestTrainer(BaseTrainer):
    """
    Isolation Forest trainer for unsupervised fraud detection.

    Features:
    - Unsupervised anomaly detection
    - Feature preprocessing and scaling
    - Score calibration for probability estimates
    - Contamination rate estimation
    - Feature importance via permutation
    """

    def __init__(
        self, config: IsolationForestConfig, experiment_tracker: ExperimentTracker | None = None
    ):
        super().__init__(config, experiment_tracker)
        self.if_config = config

        # Preprocessing components
        self.scaler = None
        self.feature_selector = None

        # Training artifacts
        self.anomaly_scores_ = None
        self.score_threshold_ = None
        self.contamination_rate_ = None

    def _create_model(self) -> IsolationForest:
        """Create Isolation Forest model with configuration."""

        # Get sklearn parameters
        sklearn_params = self.if_config.to_sklearn_params()

        # Auto-estimate contamination if needed
        if self.if_config.contamination == "auto" and self.y_train is not None:
            contamination_rate = np.mean(self.y_train)
            sklearn_params["contamination"] = contamination_rate
            self.contamination_rate_ = contamination_rate

            self.logger.info(f"Auto-estimated contamination rate: {contamination_rate:.4f}")

        # Create model
        model = IsolationForest(**sklearn_params)

        self.logger.info("Created Isolation Forest model")
        self.logger.debug(f"Isolation Forest parameters: {sklearn_params}")

        return model

    def _preprocess_features(self, X: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        """Preprocess features for Isolation Forest."""

        X_processed = X.copy()

        # Handle categorical features first
        if fit:
            # Identify categorical columns
            self.categorical_columns_ = X_processed.select_dtypes(
                include=["object", "category"]
            ).columns.tolist()
            self.numeric_columns_ = X_processed.select_dtypes(include=["number"]).columns.tolist()

            if self.categorical_columns_:
                # Use LabelEncoder for categorical features
                from sklearn.preprocessing import LabelEncoder

                self.label_encoders_ = {}

                for col in self.categorical_columns_:
                    encoder = LabelEncoder()
                    X_processed[col] = encoder.fit_transform(X_processed[col].astype(str))
                    self.label_encoders_[col] = encoder

                self.logger.info(
                    f"Encoded {len(self.categorical_columns_)} categorical features: {self.categorical_columns_}"
                )
        else:
            # Apply existing encoders to categorical columns
            if hasattr(self, "categorical_columns_") and self.categorical_columns_:
                for col in self.categorical_columns_:
                    if col in X_processed.columns and col in self.label_encoders_:
                        # Handle unseen categories by using 0 (first category)
                        try:
                            X_processed[col] = self.label_encoders_[col].transform(
                                X_processed[col].astype(str)
                            )
                        except ValueError:
                            # Handle unseen categories
                            X_processed[col] = (
                                X_processed[col]
                                .astype(str)
                                .map(
                                    lambda x: (
                                        self.label_encoders_[col].transform([x])[0]
                                        if x in self.label_encoders_[col].classes_
                                        else 0
                                    )
                                )
                            )

        # Feature selection (if specified)
        if self.if_config.feature_selection and fit:
            X_processed = self._apply_feature_selection(X_processed, fit=True)
        elif self.feature_selector is not None:
            X_processed = self._apply_feature_selection(X_processed, fit=False)

        # Standardization (recommended for Isolation Forest)
        if self.if_config.standardize_features:
            if fit:
                self.scaler = StandardScaler()
                X_scaled = self.scaler.fit_transform(X_processed)
                self.logger.info("Fitted feature standardization")
            else:
                if self.scaler is None:
                    raise ValueError("Scaler not fitted. Call fit first.")
                X_scaled = self.scaler.transform(X_processed)

            X_processed = pd.DataFrame(
                X_scaled, index=X_processed.index, columns=X_processed.columns
            )

        return X_processed

    def _apply_feature_selection(self, X: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        """Apply feature selection based on configuration."""

        if self.if_config.feature_selection == "variance":
            from sklearn.feature_selection import VarianceThreshold

            if fit:
                self.feature_selector = VarianceThreshold(threshold=0.01)
                X_selected = self.feature_selector.fit_transform(X)
                selected_features = X.columns[self.feature_selector.get_support()]
                self.logger.info(
                    f"Variance-based selection: {len(selected_features)}/{len(X.columns)} features"
                )
            else:
                X_selected = self.feature_selector.transform(X)
                selected_features = X.columns[self.feature_selector.get_support()]

            return pd.DataFrame(X_selected, index=X.index, columns=selected_features)

        elif self.if_config.feature_selection == "correlation":
            # Remove highly correlated features
            if fit:
                correlation_matrix = X.corr().abs()
                upper_triangle = correlation_matrix.where(
                    np.triu(np.ones(correlation_matrix.shape), k=1).astype(bool)
                )

                # Find features to remove (correlation > 0.95)
                to_remove = [
                    column
                    for column in upper_triangle.columns
                    if any(upper_triangle[column] > 0.95)
                ]

                self.feature_selector = {"removed_features": to_remove}
                self.logger.info(f"Correlation-based removal: {len(to_remove)} features removed")

            removed_features = self.feature_selector["removed_features"]
            return X.drop(columns=removed_features, errors="ignore")

        return X

    def _fit_model(self, X: pd.DataFrame, y: pd.Series) -> IsolationForest:
        """Fit Isolation Forest model."""

        # Preprocess features
        X_processed = self._preprocess_features(X, fit=True)

        # Create and fit model
        model = self._create_model()

        self.logger.info("Fitting Isolation Forest model...")
        model.fit(X_processed)

        # Compute anomaly scores on training data
        self.anomaly_scores_ = model.decision_function(X_processed)

        # Determine threshold for binary classification
        # Negative scores indicate anomalies in sklearn's Isolation Forest
        if y is not None:
            # Use supervised information to calibrate threshold
            self.score_threshold_ = self._calibrate_threshold(self.anomaly_scores_, y)
        else:
            # Use contamination rate to set threshold
            contamination = self.contamination_rate_ or self.if_config.contamination
            if isinstance(contamination, (int, float)) and contamination != "auto":
                percentile = (1 - contamination) * 100
                self.score_threshold_ = np.percentile(self.anomaly_scores_, percentile)
            else:
                # Default threshold (0 means anomalies have negative scores)
                self.score_threshold_ = 0.0

        self.logger.info("Isolation Forest model fitted")
        self.logger.info(f"Anomaly score threshold: {self.score_threshold_:.4f}")

        return model

    def _calibrate_threshold(self, scores: np.ndarray, y_true: np.ndarray) -> float:
        """Calibrate anomaly score threshold using ground truth labels."""

        # Try different thresholds and find the one that maximizes F1-score
        from sklearn.metrics import f1_score

        thresholds = np.percentile(scores, np.linspace(1, 99, 99))
        best_f1 = -1
        best_threshold = 0.0

        for threshold in thresholds:
            # Predict anomalies (scores below threshold)
            y_pred = (scores < threshold).astype(int)

            try:
                f1 = f1_score(y_true, y_pred)
                if f1 > best_f1:
                    best_f1 = f1
                    best_threshold = threshold
            except:
                continue

        self.logger.info(f"Calibrated threshold for F1={best_f1:.4f}: {best_threshold:.4f}")
        return best_threshold

    def _predict(self, model: IsolationForest, X: pd.DataFrame) -> np.ndarray:
        """Generate binary predictions (1 for anomaly, 0 for normal)."""

        # Preprocess features
        X_processed = self._preprocess_features(X, fit=False)

        # Get anomaly scores
        scores = model.decision_function(X_processed)

        # Convert to binary predictions (scores below threshold are anomalies)
        predictions = (scores < self.score_threshold_).astype(int)

        return predictions

    def _predict_proba(self, model: IsolationForest, X: pd.DataFrame) -> np.ndarray:
        """Generate prediction probabilities (anomaly scores converted to probabilities)."""

        # Preprocess features
        X_processed = self._preprocess_features(X, fit=False)

        # Get anomaly scores
        scores = model.decision_function(X_processed)

        # Convert scores to probabilities
        # Lower scores (more negative) indicate higher probability of being anomalous
        if self.if_config.calibrate_scores:
            probabilities = self._calibrate_scores_to_probabilities(scores)
        else:
            # Simple transformation: map scores to [0, 1] range
            probabilities = self._simple_score_transformation(scores)

        return probabilities

    def _calibrate_scores_to_probabilities(self, scores: np.ndarray) -> np.ndarray:
        """Calibrate anomaly scores to probabilities using training data."""

        if self.y_train is None:
            return self._simple_score_transformation(scores)

        try:
            from sklearn.base import BaseEstimator, ClassifierMixin
            from sklearn.calibration import CalibratedClassifierCV

            # Create a dummy classifier that uses our scores
            class ScoreClassifier(BaseEstimator, ClassifierMixin):
                def __init__(self, threshold):
                    self.threshold = threshold

                def fit(self, X, y):
                    return self

                def predict(self, X):
                    return (X.ravel() < self.threshold).astype(int)

                def decision_function(self, X):
                    return -X.ravel()  # Negative because lower scores = more anomalous

            # Fit calibrator on training scores
            if hasattr(self, "anomaly_scores_") and self.anomaly_scores_ is not None:
                dummy_classifier = ScoreClassifier(self.score_threshold_)

                # Reshape scores for sklearn
                training_scores = self.anomaly_scores_.reshape(-1, 1)

                calibrator = CalibratedClassifierCV(
                    dummy_classifier, method=self.if_config.calibration_method, cv=3
                )
                calibrator.fit(training_scores, self.y_train)

                # Apply calibration to new scores
                test_scores = scores.reshape(-1, 1)
                probabilities = calibrator.predict_proba(test_scores)[:, 1]

                return probabilities

        except ImportError:
            self.logger.warning("sklearn calibration not available, using simple transformation")
        except Exception as e:
            self.logger.warning(f"Calibration failed: {e}, using simple transformation")

        return self._simple_score_transformation(scores)

    def _simple_score_transformation(self, scores: np.ndarray) -> np.ndarray:
        """Simple transformation of anomaly scores to probabilities."""

        # Normalize scores to [0, 1] using sigmoid-like transformation
        # Lower scores (more anomalous) should have higher probabilities

        # Invert scores (so lower scores become higher values)
        inverted_scores = -scores

        # Apply sigmoid transformation
        probabilities = 1 / (1 + np.exp(-inverted_scores))

        return probabilities

    def _get_feature_importance(self, model: IsolationForest) -> dict[str, float] | None:
        """
        Compute feature importance using permutation importance.

        Since Isolation Forest doesn't provide built-in feature importance,
        we use permutation importance to measure feature contributions.
        """
        if self.X_train is None or self.y_train is None:
            self.logger.warning("Training data not available for feature importance calculation")
            return None

        try:
            from sklearn.inspection import permutation_importance

            # Preprocess training features
            X_processed = self._preprocess_features(self.X_train, fit=False)

            # Create a scorer that uses our anomaly detection
            def anomaly_scorer(estimator, X, y_true):
                # Get anomaly scores
                scores = estimator.decision_function(X)
                # Convert to predictions using our threshold
                y_pred = (scores < self.score_threshold_).astype(int)
                # Return F1-score
                from sklearn.metrics import f1_score

                return f1_score(y_true, y_pred)

            # Compute permutation importance
            perm_importance = permutation_importance(
                model,
                X_processed,
                self.y_train,
                scoring=anomaly_scorer,
                n_repeats=5,
                random_state=self.config.random_seed,
            )

            # Create feature importance dictionary
            feature_importance = {}
            for i, feature in enumerate(self.feature_names):
                if i < len(perm_importance.importances_mean):
                    feature_importance[feature] = float(perm_importance.importances_mean[i])
                else:
                    feature_importance[feature] = 0.0

            self.logger.info("Computed permutation-based feature importance")
            return feature_importance

        except ImportError:
            self.logger.warning("sklearn.inspection not available for permutation importance")
            return None
        except Exception as e:
            self.logger.warning(f"Could not compute feature importance: {e}")
            return None

    def get_anomaly_scores(self, X: pd.DataFrame) -> np.ndarray:
        """Get raw anomaly scores for the input data."""
        if self.model is None:
            raise ValueError("Model must be trained before getting anomaly scores")

        X_processed = self._preprocess_features(X, fit=False)
        return self.model.decision_function(X_processed)

    def analyze_anomalies(self, X: pd.DataFrame, top_n: int = 10) -> dict[str, Any]:
        """
        Analyze the most anomalous samples in the dataset.

        Args:
            X: Input features
            top_n: Number of top anomalies to analyze

        Returns:
            Dictionary with anomaly analysis
        """
        if self.model is None:
            raise ValueError("Model must be trained before analyzing anomalies")

        # Get anomaly scores
        scores = self.get_anomaly_scores(X)

        # Find most anomalous samples (lowest scores)
        anomaly_indices = np.argsort(scores)[:top_n]
        anomaly_scores = scores[anomaly_indices]

        # Get probabilities for these samples
        probabilities = self._predict_proba(self.model, X.iloc[anomaly_indices])

        analysis = {
            "top_anomalies": {
                "indices": anomaly_indices.tolist(),
                "scores": anomaly_scores.tolist(),
                "probabilities": probabilities.tolist(),
                "samples": X.iloc[anomaly_indices].to_dict("records"),
            },
            "score_statistics": {
                "min_score": float(np.min(scores)),
                "max_score": float(np.max(scores)),
                "mean_score": float(np.mean(scores)),
                "std_score": float(np.std(scores)),
                "threshold": float(self.score_threshold_),
                "anomaly_rate": float(np.mean(scores < self.score_threshold_)),
            },
        }

        return analysis

    def plot_anomaly_scores(
        self, X: pd.DataFrame, y: pd.Series | None = None, save_path: Path | None = None
    ):
        """Plot distribution of anomaly scores."""

        if self.model is None:
            raise ValueError("Model must be trained before plotting")

        try:
            import matplotlib.pyplot as plt

            scores = self.get_anomaly_scores(X)

            fig, axes = plt.subplots(1, 2, figsize=(15, 5))

            # Plot 1: Score distribution
            ax1 = axes[0]
            ax1.hist(scores, bins=50, alpha=0.7, edgecolor="black")
            ax1.axvline(
                self.score_threshold_,
                color="red",
                linestyle="--",
                label=f"Threshold: {self.score_threshold_:.3f}",
            )
            ax1.set_xlabel("Anomaly Score")
            ax1.set_ylabel("Frequency")
            ax1.set_title("Distribution of Anomaly Scores")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # Plot 2: Scores by class (if labels available)
            ax2 = axes[1]
            if y is not None:
                normal_scores = scores[y == 0]
                fraud_scores = scores[y == 1]

                ax2.hist(normal_scores, bins=30, alpha=0.6, label="Normal", color="blue")
                ax2.hist(fraud_scores, bins=30, alpha=0.6, label="Fraud", color="red")
                ax2.axvline(
                    self.score_threshold_,
                    color="black",
                    linestyle="--",
                    label=f"Threshold: {self.score_threshold_:.3f}",
                )
                ax2.set_xlabel("Anomaly Score")
                ax2.set_ylabel("Frequency")
                ax2.set_title("Anomaly Scores by Class")
                ax2.legend()
            else:
                # Show percentiles
                percentiles = np.percentile(scores, [10, 25, 50, 75, 90, 95, 99])
                ax2.boxplot(scores, vert=True)
                ax2.set_ylabel("Anomaly Score")
                ax2.set_title("Anomaly Score Distribution")

                # Add percentile annotations
                for i, p in enumerate([10, 25, 50, 75, 90, 95, 99]):
                    ax2.annotate(
                        f"P{p}: {percentiles[i]:.3f}",
                        xy=(1, percentiles[i]),
                        xytext=(1.1, percentiles[i]),
                    )

            ax2.grid(True, alpha=0.3)

            plt.tight_layout()

            if save_path:
                fig.savefig(save_path, dpi=300, bbox_inches="tight")
                self.logger.info(f"Anomaly score plots saved to {save_path}")

            return fig

        except ImportError:
            self.logger.warning("matplotlib not available for plotting")
            return None


def create_default_isolation_forest_config(**overrides) -> IsolationForestConfig:
    """Create a default Isolation Forest configuration with optional overrides."""

    default_config = {
        "model_name": "isolation_forest",
        "n_estimators": 100,
        "contamination": "auto",
        "max_features": 1.0,
        "standardize_features": True,
        "calibrate_scores": True,
        "random_seed": 42,
    }

    default_config.update(overrides)
    return IsolationForestConfig(**default_config)


def create_fast_isolation_forest_config(**overrides) -> IsolationForestConfig:
    """Create a fast Isolation Forest configuration for development/testing."""

    fast_config = {
        "model_name": "isolation_forest_fast",
        "n_estimators": 50,
        "contamination": "auto",
        "max_features": 0.5,
        "standardize_features": True,
        "calibrate_scores": False,  # Skip for speed
        "random_seed": 42,
    }

    fast_config.update(overrides)
    return IsolationForestConfig(**fast_config)


def create_robust_isolation_forest_config(**overrides) -> IsolationForestConfig:
    """Create a robust Isolation Forest configuration for production."""

    robust_config = {
        "model_name": "isolation_forest_robust",
        "n_estimators": 200,
        "contamination": "auto",
        "max_features": 1.0,
        "standardize_features": True,
        "calibrate_scores": True,
        "feature_selection": "variance",
        "random_seed": 42,
    }

    robust_config.update(overrides)
    return IsolationForestConfig(**robust_config)
