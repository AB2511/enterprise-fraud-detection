"""
Feature Store

Local feature store implementation for storing, versioning, and retrieving
feature data with metadata and statistics tracking.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.utils.file_manager import atomic_write_dataframe, atomic_write_json
from ml.utils.logging_config import get_logger
from ml.utils.metadata import MetadataManager


@dataclass
class FeatureSetMetadata:
    """Metadata for a feature set."""

    name: str
    version: str
    description: str
    created_at: str
    updated_at: str
    n_records: int
    n_features: int
    feature_names: list[str]
    data_types: dict[str, str]
    statistics: dict[str, Any]
    transformers_used: list[str]
    source_dataset: str
    schema_version: str
    checksum: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class LocalFeatureStore:
    """
    Local feature store for offline storage and retrieval of features.

    Supports:
    - Feature storage with versioning
    - Metadata management
    - Statistics tracking
    - Feature lookup and retrieval
    - Multiple storage formats
    """

    def __init__(self, store_path: Path, metadata_manager: MetadataManager | None = None):
        """
        Initialize local feature store.

        Args:
            store_path: Base path for feature store
            metadata_manager: Optional metadata manager instance
        """
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.store_path / "features").mkdir(exist_ok=True)
        (self.store_path / "metadata").mkdir(exist_ok=True)
        (self.store_path / "statistics").mkdir(exist_ok=True)
        (self.store_path / "versions").mkdir(exist_ok=True)

        self.metadata_manager = metadata_manager or MetadataManager(self.store_path / "metadata")
        self.logger = get_logger("ml.features.LocalFeatureStore")

        # Internal state
        self.feature_sets: dict[str, FeatureSetMetadata] = {}
        self._load_feature_sets()

    def store_features(
        self,
        features_df: pd.DataFrame,
        feature_set_name: str,
        version: str | None = None,
        description: str = "",
        transformers_used: list[str] = None,
        source_dataset: str = "",
        format: str = "parquet",
        **kwargs,
    ) -> str:
        """
        Store a feature set in the feature store.

        Args:
            features_df: DataFrame containing features
            feature_set_name: Name of the feature set
            version: Version string (auto-generated if None)
            description: Description of the feature set
            transformers_used: List of transformers used to create features
            source_dataset: Source dataset name
            format: Storage format ('parquet', 'csv', 'feather')
            **kwargs: Additional parameters

        Returns:
            Feature set key (name:version)
        """
        # Generate version if not provided
        if version is None:
            version = self._generate_version()

        feature_set_key = f"{feature_set_name}:{version}"

        # Validate inputs
        if features_df.empty:
            raise ValueError("Cannot store empty feature set")

        # Compute checksum
        checksum = self._compute_dataframe_checksum(features_df)

        # Create metadata
        metadata = FeatureSetMetadata(
            name=feature_set_name,
            version=version,
            description=description,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            n_records=len(features_df),
            n_features=len(features_df.columns),
            feature_names=list(features_df.columns),
            data_types={col: str(dtype) for col, dtype in features_df.dtypes.items()},
            statistics=self._compute_feature_statistics(features_df),
            transformers_used=transformers_used or [],
            source_dataset=source_dataset,
            schema_version="1.0.0",
            checksum=checksum,
        )

        # Store feature data
        feature_path = self._get_feature_path(feature_set_name, version, format)

        if format == "parquet":
            atomic_write_dataframe(features_df, feature_path, format="parquet")
        elif format == "csv":
            atomic_write_dataframe(features_df, feature_path, format="csv")
        elif format == "feather":
            atomic_write_dataframe(features_df, feature_path, format="feather")
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Store metadata
        metadata_path = self._get_metadata_path(feature_set_name, version)
        atomic_write_json(metadata.to_dict(), metadata_path)

        # Update internal state
        self.feature_sets[feature_set_key] = metadata

        # Update feature store index
        self._update_feature_store_index()

        self.logger.info(
            f"Stored feature set: {feature_set_key} ({len(features_df)} records, {len(features_df.columns)} features)"
        )

        return feature_set_key

    def load_features(
        self, feature_set_name: str, version: str | None = None, features: list[str] | None = None
    ) -> tuple[pd.DataFrame, FeatureSetMetadata]:
        """
        Load a feature set from the store.

        Args:
            feature_set_name: Name of the feature set
            version: Version to load (latest if None)
            features: Specific features to load (all if None)

        Returns:
            Tuple of (features DataFrame, metadata)
        """
        # Get version
        if version is None:
            version = self._get_latest_version(feature_set_name)

        feature_set_key = f"{feature_set_name}:{version}"

        if feature_set_key not in self.feature_sets:
            raise ValueError(f"Feature set not found: {feature_set_key}")

        metadata = self.feature_sets[feature_set_key]

        # Load feature data
        feature_path = self._find_feature_file(feature_set_name, version)

        if feature_path.suffix == ".parquet":
            features_df = pd.read_parquet(feature_path)
        elif feature_path.suffix == ".csv":
            features_df = pd.read_csv(feature_path)
        elif feature_path.suffix == ".feather":
            features_df = pd.read_feather(feature_path)
        else:
            raise ValueError(f"Unsupported file format: {feature_path.suffix}")

        # Filter features if specified
        if features:
            missing_features = set(features) - set(features_df.columns)
            if missing_features:
                raise ValueError(f"Features not found: {missing_features}")
            features_df = features_df[features]

        # Verify checksum
        current_checksum = self._compute_dataframe_checksum(features_df)
        if current_checksum != metadata.checksum and features is None:
            self.logger.warning(f"Checksum mismatch for {feature_set_key}")

        self.logger.info(f"Loaded feature set: {feature_set_key} ({len(features_df)} records)")

        return features_df, metadata

    def list_feature_sets(self, pattern: str | None = None) -> list[FeatureSetMetadata]:
        """
        List available feature sets.

        Args:
            pattern: Optional pattern to filter by name

        Returns:
            List of feature set metadata
        """
        feature_sets = list(self.feature_sets.values())

        if pattern:
            feature_sets = [fs for fs in feature_sets if pattern in fs.name]

        # Sort by name and version
        feature_sets.sort(key=lambda x: (x.name, x.version))

        return feature_sets

    def get_feature_info(self, feature_name: str) -> list[dict[str, Any]]:
        """
        Get information about where a feature is available.

        Args:
            feature_name: Name of the feature

        Returns:
            List of feature set information containing the feature
        """
        info = []

        for feature_set_key, metadata in self.feature_sets.items():
            if feature_name in metadata.feature_names:
                info.append(
                    {
                        "feature_set_name": metadata.name,
                        "feature_set_version": metadata.version,
                        "feature_set_key": feature_set_key,
                        "created_at": metadata.created_at,
                        "n_records": metadata.n_records,
                        "source_dataset": metadata.source_dataset,
                    }
                )

        return info

    def delete_feature_set(self, feature_set_name: str, version: str | None = None):
        """
        Delete a feature set from the store.

        Args:
            feature_set_name: Name of the feature set
            version: Version to delete (all versions if None)
        """
        if version:
            # Delete specific version
            feature_set_key = f"{feature_set_name}:{version}"

            if feature_set_key in self.feature_sets:
                # Delete files
                self._delete_feature_files(feature_set_name, version)

                # Remove from internal state
                del self.feature_sets[feature_set_key]

                self.logger.info(f"Deleted feature set: {feature_set_key}")
        else:
            # Delete all versions
            keys_to_delete = [
                key for key in self.feature_sets.keys() if key.startswith(f"{feature_set_name}:")
            ]

            for key in keys_to_delete:
                version = key.split(":", 1)[1]
                self._delete_feature_files(feature_set_name, version)
                del self.feature_sets[key]

            self.logger.info(f"Deleted all versions of feature set: {feature_set_name}")

        # Update feature store index
        self._update_feature_store_index()

    def get_statistics(self, feature_set_name: str, version: str | None = None) -> dict[str, Any]:
        """
        Get statistics for a feature set.

        Args:
            feature_set_name: Name of the feature set
            version: Version (latest if None)

        Returns:
            Statistics dictionary
        """
        if version is None:
            version = self._get_latest_version(feature_set_name)

        feature_set_key = f"{feature_set_name}:{version}"

        if feature_set_key not in self.feature_sets:
            raise ValueError(f"Feature set not found: {feature_set_key}")

        return self.feature_sets[feature_set_key].statistics

    def update_statistics(self, feature_set_name: str, version: str, statistics: dict[str, Any]):
        """
        Update statistics for a feature set.

        Args:
            feature_set_name: Name of the feature set
            version: Version
            statistics: Statistics dictionary
        """
        feature_set_key = f"{feature_set_name}:{version}"

        if feature_set_key in self.feature_sets:
            self.feature_sets[feature_set_key].statistics.update(statistics)
            self.feature_sets[feature_set_key].updated_at = datetime.utcnow().isoformat()

            # Save updated metadata
            metadata_path = self._get_metadata_path(feature_set_name, version)
            atomic_write_json(self.feature_sets[feature_set_key].to_dict(), metadata_path)

            self.logger.info(f"Updated statistics for feature set: {feature_set_key}")

    def export_catalog(self) -> dict[str, Any]:
        """
        Export complete feature catalog.

        Returns:
            Feature catalog dictionary
        """
        catalog = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "n_feature_sets": len(self.feature_sets),
                "total_features": sum(fs.n_features for fs in self.feature_sets.values()),
                "store_path": str(self.store_path),
            },
            "feature_sets": {},
            "feature_index": {},
        }

        # Add feature set information
        for key, metadata in self.feature_sets.items():
            catalog["feature_sets"][key] = metadata.to_dict()

        # Create feature index
        for metadata in self.feature_sets.values():
            for feature_name in metadata.feature_names:
                if feature_name not in catalog["feature_index"]:
                    catalog["feature_index"][feature_name] = []

                catalog["feature_index"][feature_name].append(
                    {
                        "feature_set_name": metadata.name,
                        "feature_set_version": metadata.version,
                        "feature_set_key": f"{metadata.name}:{metadata.version}",
                    }
                )

        return catalog

    def _load_feature_sets(self):
        """Load feature sets from metadata files."""
        metadata_dir = self.store_path / "metadata"

        for metadata_file in metadata_dir.glob("*.json"):
            try:
                with open(metadata_file) as f:
                    metadata_dict = json.load(f)

                metadata = FeatureSetMetadata(**metadata_dict)
                feature_set_key = f"{metadata.name}:{metadata.version}"
                self.feature_sets[feature_set_key] = metadata

            except Exception as e:
                self.logger.warning(f"Could not load metadata from {metadata_file}: {e}")

        self.logger.info(f"Loaded {len(self.feature_sets)} feature sets from store")

    def _generate_version(self) -> str:
        """Generate a version string."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"v{timestamp}"

    def _compute_dataframe_checksum(self, df: pd.DataFrame) -> str:
        """Compute checksum for a DataFrame."""
        # Create a reproducible string representation
        content = df.to_json(orient="records")
        # Sort the content to make it deterministic
        content = json.dumps(json.loads(content), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _compute_feature_statistics(self, df: pd.DataFrame) -> dict[str, Any]:
        """Compute comprehensive statistics for features."""
        stats = {
            "n_records": len(df),
            "n_features": len(df.columns),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
            "missing_values": df.isnull().sum().to_dict(),
            "feature_types": df.dtypes.astype(str).to_dict(),
        }

        # Numeric feature statistics
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            numeric_stats = df[numeric_cols].describe().to_dict()
            stats["numeric_features"] = numeric_stats

        # Categorical feature statistics
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns
        if len(categorical_cols) > 0:
            categorical_stats = {}
            for col in categorical_cols:
                categorical_stats[col] = {
                    "nunique": df[col].nunique(),
                    "top_values": df[col].value_counts().head(5).to_dict(),
                }
            stats["categorical_features"] = categorical_stats

        return stats

    def _get_feature_path(self, feature_set_name: str, version: str, format: str) -> Path:
        """Get path for feature data file."""
        filename = f"{feature_set_name}_{version}.{format}"
        return self.store_path / "features" / filename

    def _get_metadata_path(self, feature_set_name: str, version: str) -> Path:
        """Get path for metadata file."""
        filename = f"{feature_set_name}_{version}_metadata.json"
        return self.store_path / "metadata" / filename

    def _find_feature_file(self, feature_set_name: str, version: str) -> Path:
        """Find feature file with any supported extension."""
        base_path = self.store_path / "features" / f"{feature_set_name}_{version}"

        for ext in [".parquet", ".csv", ".feather"]:
            path = Path(str(base_path) + ext)
            if path.exists():
                return path

        raise FileNotFoundError(f"Feature file not found for {feature_set_name}:{version}")

    def _delete_feature_files(self, feature_set_name: str, version: str):
        """Delete all files for a feature set version."""
        # Delete feature data
        for ext in [".parquet", ".csv", ".feather"]:
            feature_path = self.store_path / "features" / f"{feature_set_name}_{version}{ext}"
            if feature_path.exists():
                feature_path.unlink()

        # Delete metadata
        metadata_path = self._get_metadata_path(feature_set_name, version)
        if metadata_path.exists():
            metadata_path.unlink()

    def _get_latest_version(self, feature_set_name: str) -> str:
        """Get the latest version of a feature set."""
        versions = [
            key.split(":", 1)[1]
            for key in self.feature_sets.keys()
            if key.startswith(f"{feature_set_name}:")
        ]

        if not versions:
            raise ValueError(f"No versions found for feature set: {feature_set_name}")

        # Sort versions and return latest
        return max(versions)

    def _update_feature_store_index(self):
        """Update the feature store index file."""
        index = {
            "updated_at": datetime.utcnow().isoformat(),
            "feature_sets": list(self.feature_sets.keys()),
            "feature_count": sum(fs.n_features for fs in self.feature_sets.values()),
        }

        index_path = self.store_path / "index.json"
        atomic_write_json(index, index_path)
