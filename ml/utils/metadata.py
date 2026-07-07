"""
Metadata Management System

Centralized metadata storage and retrieval for datasets, features,
pipelines, and execution history. All metadata is stored as JSON.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ml.validation.schemas import (
    DatasetMetadata,
    FeatureMetadata,
    PipelineRunMetadata,
    SplitMetadata,
    ValidationResult,
)

# ============================================================================
# Metadata Manager
# ============================================================================


class MetadataManager:
    """
    Centralized metadata management for ML pipeline.

    Handles storage and retrieval of:
    - Dataset metadata
    - Feature metadata
    - Pipeline execution metadata
    - Version metadata
    - Statistics metadata
    - Data lineage
    - Execution history

    All metadata is stored as JSON files in structured directories.
    """

    def __init__(self, metadata_root: Path):
        """
        Initialize metadata manager.

        Args:
            metadata_root: Root directory for metadata storage
        """
        self.metadata_root = Path(metadata_root)
        self._ensure_directory_structure()

    def _ensure_directory_structure(self) -> None:
        """Create metadata directory structure"""
        subdirs = [
            "datasets",
            "features",
            "pipelines",
            "validations",
            "splits",
            "lineage",
            "statistics",
            "history",
        ]

        for subdir in subdirs:
            (self.metadata_root / subdir).mkdir(parents=True, exist_ok=True)

    # ========================================================================
    # Dataset Metadata
    # ========================================================================

    def save_dataset_metadata(self, metadata: DatasetMetadata) -> Path:
        """
        Save dataset metadata.

        Args:
            metadata: DatasetMetadata object

        Returns:
            Path to saved metadata file
        """
        filename = f"{metadata.dataset_id}_{metadata.version}.json"
        filepath = self.metadata_root / "datasets" / filename

        with open(filepath, "w") as f:
            f.write(metadata.model_dump_json(indent=2))

        return filepath

    def load_dataset_metadata(self, dataset_id: str, version: str | None = None) -> DatasetMetadata:
        """
        Load dataset metadata.

        Args:
            dataset_id: Dataset ID
            version: Specific version (if None, loads latest)

        Returns:
            DatasetMetadata object
        """
        if version:
            filename = f"{dataset_id}_{version}.json"
            filepath = self.metadata_root / "datasets" / filename
        else:
            # Find latest version
            filepath = self._find_latest_metadata("datasets", dataset_id)

        if not filepath.exists():
            raise FileNotFoundError(f"Dataset metadata not found: {filepath}")

        with open(filepath) as f:
            data = json.load(f)

        return DatasetMetadata(**data)

    def list_dataset_versions(self, dataset_id: str) -> list[str]:
        """
        List all versions of a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            List of version strings
        """
        pattern = f"{dataset_id}_*.json"
        files = list((self.metadata_root / "datasets").glob(pattern))
        versions = [f.stem.split("_", 1)[1] for f in files]
        return sorted(versions)

    # ========================================================================
    # Feature Metadata
    # ========================================================================

    def save_feature_metadata(
        self,
        features: list[FeatureMetadata],
        version: str,
    ) -> Path:
        """
        Save feature metadata.

        Args:
            features: List of FeatureMetadata objects
            version: Feature version

        Returns:
            Path to saved metadata file
        """
        filename = f"features_{version}.json"
        filepath = self.metadata_root / "features" / filename

        feature_data = [f.model_dump() for f in features]

        with open(filepath, "w") as f:
            json.dump(feature_data, f, indent=2, default=str)

        return filepath

    def load_feature_metadata(self, version: str) -> list[FeatureMetadata]:
        """
        Load feature metadata.

        Args:
            version: Feature version

        Returns:
            List of FeatureMetadata objects
        """
        filename = f"features_{version}.json"
        filepath = self.metadata_root / "features" / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Feature metadata not found: {filepath}")

        with open(filepath) as f:
            data = json.load(f)

        return [FeatureMetadata(**item) for item in data]

    def get_feature_dictionary(self, version: str) -> dict[str, FeatureMetadata]:
        """
        Get feature dictionary as name -> metadata mapping.

        Args:
            version: Feature version

        Returns:
            Dictionary of feature name to FeatureMetadata
        """
        features = self.load_feature_metadata(version)
        return {f.feature_name: f for f in features}

    # ========================================================================
    # Pipeline Metadata
    # ========================================================================

    def save_pipeline_run(self, metadata: PipelineRunMetadata) -> Path:
        """
        Save pipeline run metadata.

        Args:
            metadata: PipelineRunMetadata object

        Returns:
            Path to saved metadata file
        """
        filename = f"{metadata.run_id}.json"
        filepath = self.metadata_root / "pipelines" / filename

        with open(filepath, "w") as f:
            f.write(metadata.model_dump_json(indent=2))

        # Also add to history
        self._append_to_history("pipeline_runs", metadata.model_dump())

        return filepath

    def load_pipeline_run(self, run_id: str) -> PipelineRunMetadata:
        """
        Load pipeline run metadata.

        Args:
            run_id: Pipeline run ID

        Returns:
            PipelineRunMetadata object
        """
        filename = f"{run_id}.json"
        filepath = self.metadata_root / "pipelines" / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Pipeline run metadata not found: {filepath}")

        with open(filepath) as f:
            data = json.load(f)

        return PipelineRunMetadata(**data)

    def list_pipeline_runs(
        self,
        pipeline_name: str | None = None,
        limit: int = 100,
    ) -> list[PipelineRunMetadata]:
        """
        List recent pipeline runs.

        Args:
            pipeline_name: Filter by pipeline name (optional)
            limit: Maximum number of runs to return

        Returns:
            List of PipelineRunMetadata objects (most recent first)
        """
        files = sorted(
            (self.metadata_root / "pipelines").glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        runs = []
        for filepath in files[:limit]:
            with open(filepath) as f:
                data = json.load(f)

            run = PipelineRunMetadata(**data)

            if pipeline_name is None or run.pipeline_name == pipeline_name:
                runs.append(run)

        return runs[:limit]

    # ========================================================================
    # Validation Metadata
    # ========================================================================

    def save_validation_result(self, result: ValidationResult) -> Path:
        """
        Save validation result.

        Args:
            result: ValidationResult object

        Returns:
            Path to saved result file
        """
        filename = f"{result.validation_id}.json"
        filepath = self.metadata_root / "validations" / filename

        with open(filepath, "w") as f:
            f.write(result.model_dump_json(indent=2))

        return filepath

    def load_validation_result(self, validation_id: str) -> ValidationResult:
        """
        Load validation result.

        Args:
            validation_id: Validation ID

        Returns:
            ValidationResult object
        """
        filename = f"{validation_id}.json"
        filepath = self.metadata_root / "validations" / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Validation result not found: {filepath}")

        with open(filepath) as f:
            data = json.load(f)

        return ValidationResult(**data)

    # ========================================================================
    # Split Metadata
    # ========================================================================

    def save_split_metadata(self, metadata: SplitMetadata) -> Path:
        """
        Save train/val/test split metadata.

        Args:
            metadata: SplitMetadata object

        Returns:
            Path to saved metadata file
        """
        filename = f"{metadata.split_id}.json"
        filepath = self.metadata_root / "splits" / filename

        with open(filepath, "w") as f:
            f.write(metadata.model_dump_json(indent=2))

        return filepath

    def load_split_metadata(self, split_id: str) -> SplitMetadata:
        """
        Load split metadata.

        Args:
            split_id: Split ID

        Returns:
            SplitMetadata object
        """
        filename = f"{split_id}.json"
        filepath = self.metadata_root / "splits" / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Split metadata not found: {filepath}")

        with open(filepath) as f:
            data = json.load(f)

        return SplitMetadata(**data)

    # ========================================================================
    # Data Lineage
    # ========================================================================

    def add_lineage_edge(
        self,
        source_id: str,
        target_id: str,
        transformation: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """
        Add a lineage edge (source dataset -> transformation -> target dataset).

        Args:
            source_id: Source dataset ID
            target_id: Target dataset ID
            transformation: Transformation name
            metadata: Optional transformation metadata

        Returns:
            Path to lineage file
        """
        lineage_entry = {
            "edge_id": str(uuid.uuid4()),
            "source_id": source_id,
            "target_id": target_id,
            "transformation": transformation,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": metadata or {},
        }

        # Append to lineage file
        lineage_file = self.metadata_root / "lineage" / "lineage_graph.jsonl"

        with open(lineage_file, "a") as f:
            f.write(json.dumps(lineage_entry) + "\n")

        return lineage_file

    def get_dataset_lineage(self, dataset_id: str) -> list[dict[str, Any]]:
        """
        Get lineage for a dataset (all edges involving this dataset).

        Args:
            dataset_id: Dataset ID

        Returns:
            List of lineage edges
        """
        lineage_file = self.metadata_root / "lineage" / "lineage_graph.jsonl"

        if not lineage_file.exists():
            return []

        lineage = []
        with open(lineage_file) as f:
            for line in f:
                edge = json.loads(line.strip())
                if edge["source_id"] == dataset_id or edge["target_id"] == dataset_id:
                    lineage.append(edge)

        return lineage

    # ========================================================================
    # Statistics
    # ========================================================================

    def save_statistics(
        self,
        entity_id: str,
        entity_type: str,
        statistics: dict[str, Any],
    ) -> Path:
        """
        Save statistics for an entity (dataset, features, etc.).

        Args:
            entity_id: Entity ID
            entity_type: Type of entity (e.g., "dataset", "features")
            statistics: Statistics dictionary

        Returns:
            Path to statistics file
        """
        filename = f"{entity_type}_{entity_id}_statistics.json"
        filepath = self.metadata_root / "statistics" / filename

        stats_data = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "statistics": statistics,
        }

        with open(filepath, "w") as f:
            json.dump(stats_data, f, indent=2, default=str)

        return filepath

    def load_statistics(self, entity_id: str, entity_type: str) -> dict[str, Any]:
        """
        Load statistics for an entity.

        Args:
            entity_id: Entity ID
            entity_type: Type of entity

        Returns:
            Statistics dictionary
        """
        filename = f"{entity_type}_{entity_id}_statistics.json"
        filepath = self.metadata_root / "statistics" / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Statistics not found: {filepath}")

        with open(filepath) as f:
            data = json.load(f)

        return data["statistics"]

    # ========================================================================
    # Execution History
    # ========================================================================

    def _append_to_history(
        self,
        history_type: str,
        entry: dict[str, Any],
    ) -> None:
        """
        Append entry to history log.

        Args:
            history_type: Type of history (e.g., "pipeline_runs", "validations")
            entry: History entry data
        """
        history_file = self.metadata_root / "history" / f"{history_type}.jsonl"

        with open(history_file, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def get_history(
        self,
        history_type: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get history entries.

        Args:
            history_type: Type of history
            limit: Maximum number of entries (most recent)

        Returns:
            List of history entries
        """
        history_file = self.metadata_root / "history" / f"{history_type}.jsonl"

        if not history_file.exists():
            return []

        entries = []
        with open(history_file) as f:
            for line in f:
                entries.append(json.loads(line.strip()))

        if limit:
            entries = entries[-limit:]

        return entries

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _find_latest_metadata(self, subdir: str, entity_id: str) -> Path:
        """Find latest metadata file for an entity"""
        pattern = f"{entity_id}_*.json"
        files = sorted(
            (self.metadata_root / subdir).glob(pattern),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        if not files:
            raise FileNotFoundError(f"No metadata found for {entity_id}")

        return files[0]

    def export_metadata_summary(self, output_path: Path) -> None:
        """
        Export summary of all metadata.

        Args:
            output_path: Path to save summary JSON
        """
        summary = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "metadata_root": str(self.metadata_root),
            "datasets": len(list((self.metadata_root / "datasets").glob("*.json"))),
            "pipeline_runs": len(list((self.metadata_root / "pipelines").glob("*.json"))),
            "validations": len(list((self.metadata_root / "validations").glob("*.json"))),
            "splits": len(list((self.metadata_root / "splits").glob("*.json"))),
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
