"""
Feature Registry

Central registry for tracking and managing feature transformers,
including metadata, versions, dependencies, and validation results.
"""

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ml.features.transformers.base import BaseFeatureTransformer, ValidationResult
from ml.utils.file_manager import atomic_write_json
from ml.utils.logging_config import get_logger


@dataclass
class FeatureRegistryEntry:
    """Registry entry for a feature transformer."""

    name: str
    version: str
    owner: str
    description: str
    transformer_class: str
    dependencies: list[str]
    output_features: list[str]
    parameters: dict[str, Any]
    created_at: str
    updated_at: str
    validation_results: dict[str, Any]
    statistics: dict[str, Any]
    lineage: dict[str, Any]
    tags: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert registry entry to dictionary."""
        return asdict(self)


class FeatureRegistry:
    """
    Central registry for feature transformers.

    Tracks feature metadata, versions, dependencies, validation results,
    and provides discovery and management capabilities.
    """

    def __init__(self, registry_path: Path | None = None):
        """
        Initialize feature registry.

        Args:
            registry_path: Path to store registry data
        """
        self.registry_path = registry_path or Path("data/features/registry")
        self.registry_path.mkdir(parents=True, exist_ok=True)

        self.logger = get_logger("ml.features.FeatureRegistry")

        # Registry data
        self.entries: dict[str, FeatureRegistryEntry] = {}
        self.version_history: dict[str, list[str]] = defaultdict(list)
        self.dependency_graph: dict[str, list[str]] = defaultdict(list)

        # Load existing registry
        self._load_registry()

    def register_transformer(
        self,
        transformer: BaseFeatureTransformer,
        tags: list[str] = None,
        force_update: bool = False,
    ) -> str:
        """
        Register a feature transformer in the registry.

        Args:
            transformer: Feature transformer to register
            tags: Optional tags for categorization
            force_update: Whether to update if transformer already exists

        Returns:
            Registry key for the transformer
        """
        registry_key = f"{transformer.name}:{transformer.version()}"

        # Check if already registered
        if registry_key in self.entries and not force_update:
            self.logger.warning(f"Transformer {registry_key} already registered")
            return registry_key

        # Create registry entry
        metadata = transformer.metadata()

        entry = FeatureRegistryEntry(
            name=transformer.name,
            version=transformer.version(),
            owner=transformer.owner,
            description=transformer.description,
            transformer_class=transformer.__class__.__name__,
            dependencies=transformer.dependencies,
            output_features=transformer.get_feature_names_out(),
            parameters=transformer.get_params(),
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            validation_results={},
            statistics=metadata.statistics,
            lineage=self._compute_lineage(transformer),
            tags=tags or [],
        )

        # Register entry
        self.entries[registry_key] = entry

        # Update version history
        self.version_history[transformer.name].append(transformer.version())

        # Update dependency graph
        self._update_dependency_graph(transformer.name, transformer.dependencies)

        # Save registry
        self._save_registry()

        self.logger.info(f"Registered transformer: {registry_key}")

        return registry_key

    def get_transformer_info(
        self, name: str, version: str | None = None
    ) -> FeatureRegistryEntry | None:
        """
        Get information about a registered transformer.

        Args:
            name: Transformer name
            version: Specific version (latest if None)

        Returns:
            Registry entry or None if not found
        """
        if version:
            registry_key = f"{name}:{version}"
            return self.entries.get(registry_key)
        else:
            # Get latest version
            versions = self.version_history.get(name, [])
            if not versions:
                return None

            latest_version = max(versions)
            registry_key = f"{name}:{latest_version}"
            return self.entries.get(registry_key)

    def list_transformers(self, tags: list[str] | None = None) -> list[FeatureRegistryEntry]:
        """
        List registered transformers.

        Args:
            tags: Filter by tags

        Returns:
            List of registry entries
        """
        entries = list(self.entries.values())

        if tags:
            entries = [entry for entry in entries if any(tag in entry.tags for tag in tags)]

        # Sort by name and version
        entries.sort(key=lambda x: (x.name, x.version))

        return entries

    def get_dependencies(self, name: str) -> list[str]:
        """
        Get dependencies for a transformer.

        Args:
            name: Transformer name

        Returns:
            List of dependency names
        """
        return self.dependency_graph.get(name, [])

    def get_dependents(self, name: str) -> list[str]:
        """
        Get transformers that depend on the given transformer.

        Args:
            name: Transformer name

        Returns:
            List of dependent transformer names
        """
        dependents = []

        for transformer_name, deps in self.dependency_graph.items():
            if name in deps:
                dependents.append(transformer_name)

        return dependents

    def validate_transformer(self, transformer: BaseFeatureTransformer, X) -> ValidationResult:
        """
        Validate a transformer and update registry.

        Args:
            transformer: Transformer to validate
            X: Input data for validation

        Returns:
            Validation result
        """
        registry_key = f"{transformer.name}:{transformer.version()}"

        # Run validation
        validation_result = transformer.validation(X)

        # Update registry entry
        if registry_key in self.entries:
            self.entries[registry_key].validation_results = validation_result.to_dict()
            self.entries[registry_key].updated_at = datetime.utcnow().isoformat()

            # Save registry
            self._save_registry()

        self.logger.info(
            f"Validated transformer: {registry_key} - Valid: {validation_result.is_valid}"
        )

        return validation_result

    def update_statistics(self, transformer: BaseFeatureTransformer, statistics: dict[str, Any]):
        """
        Update statistics for a registered transformer.

        Args:
            transformer: Transformer to update
            statistics: Statistics dictionary
        """
        registry_key = f"{transformer.name}:{transformer.version()}"

        if registry_key in self.entries:
            self.entries[registry_key].statistics.update(statistics)
            self.entries[registry_key].updated_at = datetime.utcnow().isoformat()

            # Save registry
            self._save_registry()

            self.logger.info(f"Updated statistics for transformer: {registry_key}")

    def get_feature_lineage(self, feature_name: str) -> list[dict[str, Any]]:
        """
        Get lineage information for a specific feature.

        Args:
            feature_name: Name of the feature

        Returns:
            List of lineage entries
        """
        lineage = []

        for entry in self.entries.values():
            if feature_name in entry.output_features:
                lineage_info = {
                    "transformer_name": entry.name,
                    "transformer_version": entry.version,
                    "transformer_class": entry.transformer_class,
                    "dependencies": entry.dependencies,
                    "created_at": entry.created_at,
                }
                lineage.append(lineage_info)

        return lineage

    def export_feature_dictionary(self) -> dict[str, Any]:
        """
        Export complete feature dictionary.

        Returns:
            Feature dictionary with all metadata
        """
        feature_dict = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "n_transformers": len(self.entries),
                "n_features": sum(len(entry.output_features) for entry in self.entries.values()),
            },
            "transformers": {},
            "features": {},
            "dependency_graph": dict(self.dependency_graph),
        }

        # Add transformer information
        for registry_key, entry in self.entries.items():
            feature_dict["transformers"][registry_key] = entry.to_dict()

        # Add feature information
        for entry in self.entries.values():
            for feature_name in entry.output_features:
                feature_dict["features"][feature_name] = {
                    "transformer_name": entry.name,
                    "transformer_version": entry.version,
                    "transformer_class": entry.transformer_class,
                    "description": entry.description,
                    "dependencies": entry.dependencies,
                    "created_at": entry.created_at,
                }

        return feature_dict

    def export_statistics(self) -> dict[str, Any]:
        """
        Export feature statistics.

        Returns:
            Statistics dictionary
        """
        stats = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "n_transformers": len(self.entries),
                "n_features": sum(len(entry.output_features) for entry in self.entries.values()),
            },
            "transformer_statistics": {},
            "feature_counts": defaultdict(int),
            "version_counts": defaultdict(int),
            "owner_counts": defaultdict(int),
        }

        for entry in self.entries.values():
            # Transformer statistics
            stats["transformer_statistics"][f"{entry.name}:{entry.version}"] = entry.statistics

            # Aggregate counts
            stats["feature_counts"][entry.transformer_class] += len(entry.output_features)
            stats["version_counts"][entry.name] += 1
            stats["owner_counts"][entry.owner] += 1

        return stats

    def export_lineage(self) -> dict[str, Any]:
        """
        Export feature lineage information.

        Returns:
            Lineage dictionary
        """
        lineage = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
            },
            "dependency_graph": dict(self.dependency_graph),
            "feature_lineage": {},
            "transformer_lineage": {},
        }

        # Feature-level lineage
        for entry in self.entries.values():
            for feature_name in entry.output_features:
                lineage["feature_lineage"][feature_name] = {
                    "source_transformer": entry.name,
                    "source_version": entry.version,
                    "source_dependencies": entry.dependencies,
                    "created_at": entry.created_at,
                }

        # Transformer-level lineage
        for entry in self.entries.values():
            lineage["transformer_lineage"][entry.name] = {
                "versions": self.version_history[entry.name],
                "dependencies": self.dependency_graph[entry.name],
                "dependents": self.get_dependents(entry.name),
            }

        return lineage

    def save_exports(self, output_dir: Path):
        """
        Save all registry exports to files.

        Args:
            output_dir: Directory to save exports
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Export feature dictionary
        feature_dict = self.export_feature_dictionary()
        atomic_write_json(feature_dict, output_dir / "feature_dictionary.json")

        # Export statistics
        statistics = self.export_statistics()
        atomic_write_json(statistics, output_dir / "feature_statistics.json")

        # Export lineage
        lineage = self.export_lineage()
        atomic_write_json(lineage, output_dir / "feature_lineage.json")

        self.logger.info(f"Exported registry data to {output_dir}")

    def _load_registry(self):
        """Load registry from disk."""
        registry_file = self.registry_path / "registry.json"

        if registry_file.exists():
            try:
                with open(registry_file) as f:
                    data = json.load(f)

                # Load entries
                for key, entry_dict in data.get("entries", {}).items():
                    entry = FeatureRegistryEntry(**entry_dict)
                    self.entries[key] = entry

                # Load version history
                self.version_history = defaultdict(list, data.get("version_history", {}))

                # Load dependency graph
                self.dependency_graph = defaultdict(list, data.get("dependency_graph", {}))

                self.logger.info(f"Loaded registry with {len(self.entries)} entries")

            except Exception as e:
                self.logger.error(f"Error loading registry: {e}")

    def _save_registry(self):
        """Save registry to disk."""
        registry_file = self.registry_path / "registry.json"

        data = {
            "entries": {key: entry.to_dict() for key, entry in self.entries.items()},
            "version_history": dict(self.version_history),
            "dependency_graph": dict(self.dependency_graph),
            "saved_at": datetime.utcnow().isoformat(),
        }

        try:
            atomic_write_json(data, registry_file)
            self.logger.debug(f"Saved registry to {registry_file}")
        except Exception as e:
            self.logger.error(f"Error saving registry: {e}")

    def _update_dependency_graph(self, transformer_name: str, dependencies: list[str]):
        """Update dependency graph with transformer dependencies."""
        # For now, track column dependencies
        # In a more sophisticated system, this could track transformer dependencies
        self.dependency_graph[transformer_name] = dependencies.copy()

    def _compute_lineage(self, transformer: BaseFeatureTransformer) -> dict[str, Any]:
        """Compute lineage information for a transformer."""
        return {
            "input_columns": transformer.dependencies,
            "output_features": transformer.get_feature_names_out(),
            "transformer_class": transformer.__class__.__name__,
            "parameters": transformer.get_params(),
            "created_at": datetime.utcnow().isoformat(),
        }
