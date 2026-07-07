"""
Feature Engineering Pipeline

Integration of feature transformers with the ML pipeline framework
for end-to-end feature engineering workflows.
"""

from datetime import datetime
from typing import Any

import pandas as pd

from ml.features.registry import FeatureRegistry
from ml.features.store import LocalFeatureStore
from ml.features.transformers.base import BaseFeatureTransformer
from ml.pipeline.stage import PipelineStage
from ml.utils.logging_config import get_logger


class FeatureEngineeringStage(PipelineStage):
    """
    Pipeline stage for feature engineering.

    Applies a sequence of feature transformers to input data
    and manages the feature engineering workflow.
    """

    def __init__(
        self,
        transformers: list[BaseFeatureTransformer],
        feature_registry: FeatureRegistry | None = None,
        feature_store: LocalFeatureStore | None = None,
        validate_features: bool = True,
        store_features: bool = True,
        **kwargs,
    ):
        """
        Initialize feature engineering stage.

        Args:
            transformers: List of feature transformers to apply
            feature_registry: Optional feature registry for metadata tracking
            feature_store: Optional feature store for persistence
            validate_features: Whether to validate transformers
            store_features: Whether to store features in feature store
            **kwargs: Additional parameters
        """
        super().__init__(
            name="feature_engineering",
            description="Apply feature transformers to create ML features",
            **kwargs,
        )

        self.transformers = transformers
        self.feature_registry = feature_registry
        self.feature_store = feature_store
        self.validate_features = validate_features
        self.store_features = store_features

        self.logger = get_logger("ml.features.FeatureEngineeringStage")

        # Register transformers if registry provided
        if self.feature_registry:
            for transformer in self.transformers:
                self.feature_registry.register_transformer(transformer)

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Execute feature engineering stage.

        Args:
            inputs: Input data containing 'dataset' key

        Returns:
            Dictionary with engineered features and metadata
        """
        dataset = inputs.get("dataset")
        if dataset is None or dataset.empty:
            raise ValueError("Input dataset is required and cannot be empty")

        self.logger.info(f"Starting feature engineering with {len(self.transformers)} transformers")

        # Start with original dataset
        current_data = dataset.copy()
        transformer_results = []
        feature_metadata = {}

        # Apply each transformer
        for i, transformer in enumerate(self.transformers):
            with self.logger.stage_context(f"applying_transformer_{transformer.name}"):
                try:
                    # Validate transformer if enabled
                    if self.validate_features and self.feature_registry:
                        validation_result = self.feature_registry.validate_transformer(
                            transformer, current_data
                        )

                        if not validation_result.is_valid:
                            self.logger.error(
                                f"Transformer validation failed: {validation_result.errors}"
                            )
                            raise ValueError(f"Transformer {transformer.name} validation failed")

                    # Apply transformer
                    if not transformer.is_fitted:
                        self.logger.info(f"Fitting transformer: {transformer.name}")
                        transformer.fit(current_data)

                    self.logger.info(f"Transforming data with: {transformer.name}")
                    transformed_data = transformer.transform(current_data)

                    # Get new features (columns added by this transformer)
                    original_cols = set(current_data.columns)
                    new_cols = set(transformed_data.columns) - original_cols

                    # Update current data
                    current_data = transformed_data

                    # Store transformer results
                    transformer_result = {
                        "transformer_name": transformer.name,
                        "transformer_version": transformer.version(),
                        "transformer_class": transformer.__class__.__name__,
                        "features_added": list(new_cols),
                        "n_features_added": len(new_cols),
                        "fit_statistics": transformer.fit_statistics,
                        "metadata": transformer.metadata().to_dict(),
                    }
                    transformer_results.append(transformer_result)

                    # Update feature metadata
                    for feature_name in new_cols:
                        feature_metadata[feature_name] = {
                            "source_transformer": transformer.name,
                            "transformer_version": transformer.version(),
                            "transformer_class": transformer.__class__.__name__,
                            "created_at": datetime.utcnow().isoformat(),
                        }

                    self.logger.info(
                        f"Transformer {transformer.name} added {len(new_cols)} features: {list(new_cols)[:5]}..."
                    )

                except Exception as e:
                    self.logger.error(f"Error applying transformer {transformer.name}: {e}")
                    raise

        # Store features in feature store if enabled
        feature_set_key = None
        if self.store_features and self.feature_store:
            try:
                feature_set_name = inputs.get("feature_set_name", "engineered_features")
                source_dataset = inputs.get("dataset_name", "unknown")

                transformer_names = [t.name for t in self.transformers]

                feature_set_key = self.feature_store.store_features(
                    features_df=current_data,
                    feature_set_name=feature_set_name,
                    description=f"Features created by {len(self.transformers)} transformers",
                    transformers_used=transformer_names,
                    source_dataset=source_dataset,
                    format="parquet",
                )

                self.logger.info(f"Stored features in feature store: {feature_set_key}")

            except Exception as e:
                self.logger.warning(f"Could not store features: {e}")

        # Create comprehensive output
        total_features_added = sum(len(result["features_added"]) for result in transformer_results)

        output = {
            # Data
            "engineered_features": current_data,
            "original_dataset": dataset,
            # Metadata
            "feature_engineering_metadata": {
                "n_transformers_applied": len(self.transformers),
                "total_features_added": total_features_added,
                "original_feature_count": len(dataset.columns),
                "final_feature_count": len(current_data.columns),
                "transformer_results": transformer_results,
                "feature_metadata": feature_metadata,
                "processing_time": datetime.utcnow().isoformat(),
            },
            # Store information
            "feature_set_key": feature_set_key,
            "feature_store_path": (
                str(self.feature_store.store_path) if self.feature_store else None
            ),
        }

        # Pass through other inputs
        for key, value in inputs.items():
            if key not in output:
                output[key] = value

        self.logger.info(
            f"Feature engineering completed: {len(dataset.columns)} → {len(current_data.columns)} features "
            f"({total_features_added} added)"
        )

        return output


class FeatureSelectionStage(PipelineStage):
    """
    Pipeline stage for feature selection.

    Applies feature selection techniques to reduce dimensionality
    and improve model performance.
    """

    def __init__(
        self,
        selection_method: str = "variance_threshold",
        selection_params: dict[str, Any] = None,
        target_column: str = "is_fraud",
        **kwargs,
    ):
        """
        Initialize feature selection stage.

        Args:
            selection_method: Feature selection method to use
            selection_params: Parameters for selection method
            target_column: Target column name for supervised selection
            **kwargs: Additional parameters
        """
        super().__init__(
            name="feature_selection",
            description="Select most relevant features for modeling",
            **kwargs,
        )

        self.selection_method = selection_method
        self.selection_params = selection_params or {}
        self.target_column = target_column

        self.logger = get_logger("ml.features.FeatureSelectionStage")

        # Feature selection state
        self.selected_features_: list[str] | None = None
        self.selection_scores_: dict[str, float] | None = None

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Execute feature selection stage.

        Args:
            inputs: Input data containing engineered features

        Returns:
            Dictionary with selected features and selection metadata
        """
        engineered_features = inputs.get("engineered_features")
        if engineered_features is None or engineered_features.empty:
            raise ValueError("Engineered features are required")

        self.logger.info(f"Starting feature selection with method: {self.selection_method}")

        # Extract features and target
        if self.target_column in engineered_features.columns:
            X = engineered_features.drop(columns=[self.target_column])
            y = engineered_features[self.target_column]
        else:
            X = engineered_features
            y = None
            self.logger.warning(
                f"Target column '{self.target_column}' not found, using unsupervised selection"
            )

        # Apply feature selection
        selected_X, selection_metadata = self._apply_feature_selection(X, y)

        # Reconstruct full dataset with selected features
        selected_features_df = selected_X.copy()
        if y is not None:
            selected_features_df[self.target_column] = y

        # Create output
        output = {
            # Data
            "selected_features": selected_features_df,
            "feature_selection_X": selected_X,
            # Metadata
            "feature_selection_metadata": {
                "selection_method": self.selection_method,
                "selection_params": self.selection_params,
                "original_feature_count": len(X.columns),
                "selected_feature_count": len(selected_X.columns),
                "features_removed": len(X.columns) - len(selected_X.columns),
                "selected_features": list(selected_X.columns),
                "selection_scores": self.selection_scores_,
                **selection_metadata,
            },
        }

        # Pass through other inputs
        for key, value in inputs.items():
            if key not in output:
                output[key] = value

        self.logger.info(
            f"Feature selection completed: {len(X.columns)} → {len(selected_X.columns)} features"
        )

        return output

    def _apply_feature_selection(self, X: pd.DataFrame, y: pd.Series | None) -> tuple:
        """Apply the specified feature selection method."""

        if self.selection_method == "variance_threshold":
            return self._variance_threshold_selection(X)

        elif self.selection_method == "correlation_threshold":
            return self._correlation_threshold_selection(X)

        elif self.selection_method == "univariate" and y is not None:
            return self._univariate_selection(X, y)

        elif self.selection_method == "mutual_info" and y is not None:
            return self._mutual_info_selection(X, y)

        else:
            self.logger.warning(
                f"Unknown selection method: {self.selection_method}, returning all features"
            )
            return X, {}

    def _variance_threshold_selection(self, X: pd.DataFrame) -> tuple:
        """Select features based on variance threshold."""
        threshold = self.selection_params.get("threshold", 0.01)

        # Compute variances for numeric columns only
        numeric_cols = X.select_dtypes(include=["number"]).columns
        variances = X[numeric_cols].var()

        # Select features above threshold
        high_variance_features = variances[variances > threshold].index.tolist()

        # Include non-numeric columns
        non_numeric_cols = X.select_dtypes(exclude=["number"]).columns.tolist()
        selected_features = high_variance_features + non_numeric_cols

        selected_X = X[selected_features]

        self.selected_features_ = selected_features
        self.selection_scores_ = variances.to_dict()

        metadata = {
            "variance_threshold": threshold,
            "low_variance_features_removed": list(set(numeric_cols) - set(high_variance_features)),
        }

        return selected_X, metadata

    def _correlation_threshold_selection(self, X: pd.DataFrame) -> tuple:
        """Remove highly correlated features."""
        threshold = self.selection_params.get("threshold", 0.95)

        # Compute correlation matrix for numeric columns
        numeric_cols = X.select_dtypes(include=["number"]).columns
        if len(numeric_cols) < 2:
            return X, {"message": "Not enough numeric features for correlation analysis"}

        corr_matrix = X[numeric_cols].corr().abs()

        # Find highly correlated pairs
        upper_triangle = corr_matrix.where(
            pd.np.triu(pd.np.ones(corr_matrix.shape), k=1).astype(bool)
        )

        # Features to remove (keep first occurrence)
        to_remove = [
            column for column in upper_triangle.columns if any(upper_triangle[column] > threshold)
        ]

        # Select remaining features
        remaining_numeric = [col for col in numeric_cols if col not in to_remove]
        non_numeric_cols = X.select_dtypes(exclude=["number"]).columns.tolist()
        selected_features = remaining_numeric + non_numeric_cols

        selected_X = X[selected_features]

        self.selected_features_ = selected_features

        metadata = {
            "correlation_threshold": threshold,
            "highly_correlated_features_removed": to_remove,
        }

        return selected_X, metadata

    def _univariate_selection(self, X: pd.DataFrame, y: pd.Series) -> tuple:
        """Select features using univariate statistical tests."""
        try:
            from sklearn.feature_selection import SelectKBest, chi2, f_classif
            from sklearn.preprocessing import MinMaxScaler

            k = self.selection_params.get("k", min(50, len(X.columns)))
            score_func = self.selection_params.get("score_func", "f_classif")

            # Select only numeric columns
            numeric_cols = X.select_dtypes(include=["number"]).columns
            X_numeric = X[numeric_cols]

            if len(numeric_cols) == 0:
                return X, {"message": "No numeric features for univariate selection"}

            # Handle different score functions
            if score_func == "chi2":
                # Chi2 requires non-negative values
                scaler = MinMaxScaler()
                X_scaled = pd.DataFrame(
                    scaler.fit_transform(X_numeric),
                    columns=X_numeric.columns,
                    index=X_numeric.index,
                )
                selector = SelectKBest(score_func=chi2, k=min(k, len(numeric_cols)))
            else:
                X_scaled = X_numeric
                selector = SelectKBest(score_func=f_classif, k=min(k, len(numeric_cols)))

            # Fit selector
            X_selected = selector.fit_transform(X_scaled, y)

            # Get selected feature names
            selected_mask = selector.get_support()
            selected_numeric_features = X_numeric.columns[selected_mask].tolist()

            # Include non-numeric columns
            non_numeric_cols = X.select_dtypes(exclude=["number"]).columns.tolist()
            selected_features = selected_numeric_features + non_numeric_cols

            selected_X = X[selected_features]

            self.selected_features_ = selected_features
            self.selection_scores_ = dict(zip(X_numeric.columns, selector.scores_))

            metadata = {
                "score_func": score_func,
                "k": k,
                "selected_k": len(selected_numeric_features),
            }

            return selected_X, metadata

        except ImportError:
            self.logger.warning("scikit-learn not available, skipping univariate selection")
            return X, {"message": "scikit-learn not available"}

    def _mutual_info_selection(self, X: pd.DataFrame, y: pd.Series) -> tuple:
        """Select features using mutual information."""
        try:
            from sklearn.feature_selection import SelectKBest, mutual_info_classif

            k = self.selection_params.get("k", min(30, len(X.columns)))

            # Select only numeric columns
            numeric_cols = X.select_dtypes(include=["number"]).columns
            X_numeric = X[numeric_cols]

            if len(numeric_cols) == 0:
                return X, {"message": "No numeric features for mutual info selection"}

            # Apply mutual information selection
            selector = SelectKBest(score_func=mutual_info_classif, k=min(k, len(numeric_cols)))
            X_selected = selector.fit_transform(X_numeric, y)

            # Get selected feature names
            selected_mask = selector.get_support()
            selected_numeric_features = X_numeric.columns[selected_mask].tolist()

            # Include non-numeric columns
            non_numeric_cols = X.select_dtypes(exclude=["number"]).columns.tolist()
            selected_features = selected_numeric_features + non_numeric_cols

            selected_X = X[selected_features]

            self.selected_features_ = selected_features
            self.selection_scores_ = dict(zip(X_numeric.columns, selector.scores_))

            metadata = {
                "k": k,
                "selected_k": len(selected_numeric_features),
            }

            return selected_X, metadata

        except ImportError:
            self.logger.warning("scikit-learn not available, skipping mutual info selection")
            return X, {"message": "scikit-learn not available"}
