"""
Dataset Versioning System

Implements DVC-ready dataset versioning with:
- Version IDs
- Checksums (SHA256)
- Creation timestamps
- Source tracking
- Schema versioning
- Preprocessing versioning

Never overwrites existing versions - all versions are immutable.
"""

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# ============================================================================
# Dataset Version
# ============================================================================

class DatasetVersion:
    """
    Represents a versioned dataset with immutability guarantees.
    
    Each version has:
    - Unique version_id
    - SHA256 checksum
    - Creation timestamp
    - Source information
    - Schema version
    - Preprocessing version
    - Parent version (lineage)
    
    Versions are immutable - once created, they cannot be modified.
    """

    def __init__(
        self,
        dataset_name: str,
        version_id: str | None = None,
        schema_version: str = "v1.0.0",
        preprocessing_version: str = "v1.0.0",
        source: str | None = None,
        parent_version_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize dataset version.
        
        Args:
            dataset_name: Name of the dataset
            version_id: Version ID (auto-generated if None)
            schema_version: Schema version string
            preprocessing_version: Preprocessing version string
            source: Source of dataset (e.g., "creditcard", "ieee-cis")
            parent_version_id: Parent version ID for lineage
            metadata: Additional metadata
        """
        self.dataset_name = dataset_name
        self.version_id = version_id or self._generate_version_id()
        self.schema_version = schema_version
        self.preprocessing_version = preprocessing_version
        self.source = source
        self.parent_version_id = parent_version_id
        self.created_at = datetime.utcnow()
        self.metadata = metadata or {}

        # Will be set after data is saved
        self.checksum: str | None = None
        self.file_path: Path | None = None
        self.num_records: int | None = None
        self.file_size_bytes: int | None = None

    @staticmethod
    def _generate_version_id() -> str:
        """Generate unique version ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_id}"

    def calculate_checksum(self, data_path: Path) -> str:
        """
        Calculate SHA256 checksum of dataset file.
        
        Args:
            data_path: Path to dataset file
            
        Returns:
            SHA256 checksum hex string
        """
        sha256 = hashlib.sha256()

        with open(data_path, 'rb') as f:
            # Read in chunks for memory efficiency
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)

        return sha256.hexdigest()

    def save_dataframe(
        self,
        df: pd.DataFrame,
        output_dir: Path,
        format: str = "parquet",
    ) -> Path:
        """
        Save DataFrame as versioned dataset.
        
        Args:
            df: DataFrame to save
            output_dir: Output directory
            format: File format ("parquet", "csv")
            
        Returns:
            Path to saved file
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with version
        filename = f"{self.dataset_name}_{self.version_id}.{format}"
        filepath = output_dir / filename

        # Never overwrite existing versions
        if filepath.exists():
            raise FileExistsError(
                f"Version already exists: {filepath}. "
                "Versions are immutable and cannot be overwritten."
            )

        # Save data
        if format == "parquet":
            df.to_parquet(filepath, index=False)
        elif format == "csv":
            df.to_csv(filepath, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Update version metadata
        self.file_path = filepath
        self.num_records = len(df)
        self.file_size_bytes = filepath.stat().st_size
        self.checksum = self.calculate_checksum(filepath)

        # Save version metadata
        self._save_version_metadata(output_dir)

        return filepath

    def load_dataframe(self, data_path: Path | None = None) -> pd.DataFrame:
        """
        Load DataFrame from versioned dataset.
        
        Args:
            data_path: Path to data file (uses self.file_path if None)
            
        Returns:
            DataFrame
        """
        filepath = Path(data_path) if data_path else self.file_path

        if filepath is None:
            raise ValueError("No file path specified")

        if not filepath.exists():
            raise FileNotFoundError(f"Dataset file not found: {filepath}")

        # Verify checksum if available
        if self.checksum:
            current_checksum = self.calculate_checksum(filepath)
            if current_checksum != self.checksum:
                raise ValueError(
                    f"Checksum mismatch! Dataset may be corrupted.\n"
                    f"Expected: {self.checksum}\n"
                    f"Got: {current_checksum}"
                )

        # Load based on file extension
        if filepath.suffix == '.parquet':
            return pd.read_parquet(filepath)
        elif filepath.suffix == '.csv':
            return pd.read_csv(filepath)
        else:
            raise ValueError(f"Unsupported file format: {filepath.suffix}")

    def _save_version_metadata(self, output_dir: Path) -> None:
        """Save version metadata as JSON"""
        metadata_file = output_dir / f"{self.dataset_name}_{self.version_id}_version.json"

        version_data = {
            "dataset_name": self.dataset_name,
            "version_id": self.version_id,
            "schema_version": self.schema_version,
            "preprocessing_version": self.preprocessing_version,
            "source": self.source,
            "parent_version_id": self.parent_version_id,
            "created_at": self.created_at.isoformat() + "Z",
            "checksum": self.checksum,
            "file_path": str(self.file_path) if self.file_path else None,
            "num_records": self.num_records,
            "file_size_bytes": self.file_size_bytes,
            "metadata": self.metadata,
        }

        with open(metadata_file, 'w') as f:
            json.dump(version_data, f, indent=2)

    @classmethod
    def load_version_metadata(cls, metadata_path: Path) -> 'DatasetVersion':
        """
        Load version from metadata file.
        
        Args:
            metadata_path: Path to version metadata JSON
            
        Returns:
            DatasetVersion instance
        """
        with open(metadata_path) as f:
            data = json.load(f)

        version = cls(
            dataset_name=data['dataset_name'],
            version_id=data['version_id'],
            schema_version=data['schema_version'],
            preprocessing_version=data['preprocessing_version'],
            source=data['source'],
            parent_version_id=data['parent_version_id'],
            metadata=data['metadata'],
        )

        version.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        version.checksum = data['checksum']
        version.file_path = Path(data['file_path']) if data['file_path'] else None
        version.num_records = data['num_records']
        version.file_size_bytes = data['file_size_bytes']

        return version

    def to_dict(self) -> dict[str, Any]:
        """Convert version to dictionary"""
        return {
            "dataset_name": self.dataset_name,
            "version_id": self.version_id,
            "schema_version": self.schema_version,
            "preprocessing_version": self.preprocessing_version,
            "source": self.source,
            "parent_version_id": self.parent_version_id,
            "created_at": self.created_at.isoformat() + "Z",
            "checksum": self.checksum,
            "file_path": str(self.file_path) if self.file_path else None,
            "num_records": self.num_records,
            "file_size_bytes": self.file_size_bytes,
        }

    def __repr__(self) -> str:
        return (
            f"DatasetVersion("
            f"name={self.dataset_name}, "
            f"version={self.version_id}, "
            f"records={self.num_records}, "
            f"checksum={self.checksum[:8] if self.checksum else 'None'}...)"
        )


# ============================================================================
# Dataset Version Registry
# ============================================================================

class DatasetVersionRegistry:
    """
    Registry for managing dataset versions.
    
    Tracks all versions of all datasets and provides:
    - Version lookup
    - Lineage tracking
    - Version comparison
    - Latest version retrieval
    """

    def __init__(self, registry_dir: Path):
        """
        Initialize version registry.
        
        Args:
            registry_dir: Directory for version registry
        """
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_dir / "dataset_registry.jsonl"

    def register_version(self, version: DatasetVersion) -> None:
        """
        Register a dataset version.
        
        Args:
            version: DatasetVersion to register
        """
        # Check for duplicate version_id
        if self.version_exists(version.version_id):
            raise ValueError(f"Version already registered: {version.version_id}")

        # Append to registry
        with open(self.registry_file, 'a') as f:
            f.write(json.dumps(version.to_dict(), default=str) + '\n')

    def version_exists(self, version_id: str) -> bool:
        """Check if version exists in registry"""
        if not self.registry_file.exists():
            return False

        with open(self.registry_file) as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry['version_id'] == version_id:
                    return True

        return False

    def get_version(self, version_id: str) -> dict[str, Any]:
        """
        Get version metadata by version_id.
        
        Args:
            version_id: Version ID
            
        Returns:
            Version metadata dictionary
        """
        if not self.registry_file.exists():
            raise ValueError(f"Version not found: {version_id}")

        with open(self.registry_file) as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry['version_id'] == version_id:
                    return entry

        raise ValueError(f"Version not found: {version_id}")

    def list_versions(
        self,
        dataset_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List all versions (optionally filtered by dataset name).
        
        Args:
            dataset_name: Filter by dataset name (optional)
            
        Returns:
            List of version metadata dictionaries
        """
        if not self.registry_file.exists():
            return []

        versions = []
        with open(self.registry_file) as f:
            for line in f:
                entry = json.loads(line.strip())
                if dataset_name is None or entry['dataset_name'] == dataset_name:
                    versions.append(entry)

        return sorted(versions, key=lambda v: v['created_at'], reverse=True)

    def get_latest_version(self, dataset_name: str) -> dict[str, Any]:
        """
        Get latest version of a dataset.
        
        Args:
            dataset_name: Dataset name
            
        Returns:
            Latest version metadata dictionary
        """
        versions = self.list_versions(dataset_name)

        if not versions:
            raise ValueError(f"No versions found for dataset: {dataset_name}")

        return versions[0]  # Already sorted by created_at desc

    def get_lineage(self, version_id: str) -> list[dict[str, Any]]:
        """
        Get version lineage (parent versions).
        
        Args:
            version_id: Version ID
            
        Returns:
            List of parent versions (oldest to newest)
        """
        lineage = []
        current_version_id = version_id

        while current_version_id:
            version = self.get_version(current_version_id)
            lineage.append(version)
            current_version_id = version.get('parent_version_id')

        return list(reversed(lineage))  # Oldest first

    def export_registry(self, output_path: Path) -> None:
        """
        Export registry to JSON.
        
        Args:
            output_path: Path to save registry JSON
        """
        versions = self.list_versions()

        registry_data = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_versions": len(versions),
            "versions": versions,
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(registry_data, f, indent=2, default=str)
