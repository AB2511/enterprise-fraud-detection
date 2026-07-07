"""
File Management Utilities

Utilities for:
- Dataset discovery
- File hashing (SHA256, MD5)
- Directory creation
- Atomic writes
- Safe reads
- Export utilities
"""

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

# ============================================================================
# File Hashing
# ============================================================================


def compute_file_hash(filepath: Path, algorithm: str = "sha256") -> str:
    """
    Compute hash of file.

    Args:
        filepath: Path to file
        algorithm: Hash algorithm ("sha256", "md5")

    Returns:
        Hash hex string
    """
    filepath = Path(filepath)

    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "md5":
        hasher = hashlib.md5()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def verify_file_hash(filepath: Path, expected_hash: str, algorithm: str = "sha256") -> bool:
    """
    Verify file hash matches expected value.

    Args:
        filepath: Path to file
        expected_hash: Expected hash value
        algorithm: Hash algorithm

    Returns:
        True if hash matches, False otherwise
    """
    actual_hash = compute_file_hash(filepath, algorithm)
    return actual_hash == expected_hash


# ============================================================================
# Dataset Discovery
# ============================================================================


def discover_datasets(
    root_dir: Path,
    file_pattern: str = "*.csv",
    recursive: bool = True,
) -> list[Path]:
    """
    Discover dataset files in directory.

    Args:
        root_dir: Root directory to search
        file_pattern: File pattern (e.g., "*.csv", "*.parquet")
        recursive: Search recursively

    Returns:
        List of dataset file paths
    """
    root_dir = Path(root_dir)

    if not root_dir.exists():
        return []

    if recursive:
        return sorted(root_dir.rglob(file_pattern))
    else:
        return sorted(root_dir.glob(file_pattern))


def discover_dataset_versions(
    dataset_name: str,
    dataset_dir: Path,
) -> list[dict[str, Any]]:
    """
    Discover all versions of a dataset.

    Args:
        dataset_name: Dataset name
        dataset_dir: Directory containing dataset versions

    Returns:
        List of version info dictionaries
    """
    dataset_dir = Path(dataset_dir)
    pattern = f"{dataset_name}_*.parquet"

    versions = []
    for filepath in sorted(dataset_dir.glob(pattern)):
        # Extract version from filename
        # Format: dataset_name_YYYYMMDD_HHMMSS_uuid.parquet
        stem = filepath.stem
        parts = stem.split("_")

        if len(parts) >= 3:
            version_info = {
                "filepath": filepath,
                "filename": filepath.name,
                "version_id": "_".join(parts[1:]),  # Everything after dataset name
                "size_bytes": filepath.stat().st_size,
                "modified_time": filepath.stat().st_mtime,
            }
            versions.append(version_info)

    return versions


# ============================================================================
# Atomic Operations
# ============================================================================


def atomic_write_text(content: str, filepath: Path) -> None:
    """
    Write text file atomically (write to temp, then move).

    Args:
        content: Text content to write
        filepath: Destination file path
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file first
    with tempfile.NamedTemporaryFile(
        mode="w", dir=filepath.parent, delete=False, suffix=".tmp"
    ) as temp_file:
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    # Atomic move
    temp_path.replace(filepath)


def atomic_write_json(data: dict[str, Any], filepath: Path, indent: int = 2) -> None:
    """
    Write JSON file atomically.

    Args:
        data: Data to write
        filepath: Destination file path
        indent: JSON indentation
    """
    content = json.dumps(data, indent=indent, default=str)
    atomic_write_text(content, filepath)


def atomic_write_dataframe(
    df: pd.DataFrame, filepath: Path, format: str = "parquet", **kwargs
) -> None:
    """
    Write DataFrame atomically.

    Args:
        df: DataFrame to write
        filepath: Destination file path
        format: File format ("parquet", "csv")
        **kwargs: Additional arguments for to_parquet/to_csv
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file
    temp_path = filepath.with_suffix(filepath.suffix + ".tmp")

    try:
        if format == "parquet":
            df.to_parquet(temp_path, index=False, **kwargs)
        elif format == "csv":
            df.to_csv(temp_path, index=False, **kwargs)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Atomic move
        temp_path.replace(filepath)
    except Exception:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink()
        raise


# ============================================================================
# Safe Read Operations
# ============================================================================


def safe_read_json(filepath: Path) -> dict[str, Any]:
    """
    Safely read JSON file with error handling.

    Args:
        filepath: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        with open(filepath) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in {filepath}: {e.msg}", e.doc, e.pos)


def safe_read_dataframe(filepath: Path, format: str | None = None, **kwargs) -> pd.DataFrame:
    """
    Safely read DataFrame with error handling.

    Args:
        filepath: Path to data file
        format: File format (auto-detected from extension if None)
        **kwargs: Additional arguments for read_parquet/read_csv

    Returns:
        DataFrame
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    # Auto-detect format
    if format is None:
        format = filepath.suffix.lstrip(".")

    try:
        if format == "parquet":
            return pd.read_parquet(filepath, **kwargs)
        elif format == "csv":
            return pd.read_csv(filepath, **kwargs)
        else:
            raise ValueError(f"Unsupported format: {format}")
    except Exception as e:
        raise OSError(f"Failed to read {filepath}: {e}")


# ============================================================================
# Export Utilities
# ============================================================================


def export_dataframe(
    df: pd.DataFrame,
    output_path: Path,
    formats: list[str] = ["parquet"],
    compression: str | None = "snappy",
) -> dict[str, Path]:
    """
    Export DataFrame to multiple formats.

    Args:
        df: DataFrame to export
        output_path: Base output path (without extension)
        formats: List of formats to export ("parquet", "csv", "json")
        compression: Compression type

    Returns:
        Dictionary mapping format to output path
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    exported_files = {}

    for fmt in formats:
        if fmt == "parquet":
            filepath = output_path.with_suffix(".parquet")
            atomic_write_dataframe(df, filepath, format="parquet", compression=compression)
            exported_files["parquet"] = filepath

        elif fmt == "csv":
            filepath = output_path.with_suffix(".csv")
            atomic_write_dataframe(df, filepath, format="csv")
            exported_files["csv"] = filepath

        elif fmt == "json":
            filepath = output_path.with_suffix(".json")
            atomic_write_json(df.to_dict(orient="records"), filepath)
            exported_files["json"] = filepath

        else:
            raise ValueError(f"Unsupported format: {fmt}")

    return exported_files


def export_metadata(
    metadata: dict[str, Any],
    output_path: Path,
    formats: list[str] = ["json"],
) -> dict[str, Path]:
    """
    Export metadata to multiple formats.

    Args:
        metadata: Metadata dictionary
        output_path: Base output path (without extension)
        formats: List of formats ("json", "yaml")

    Returns:
        Dictionary mapping format to output path
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    exported_files = {}

    for fmt in formats:
        if fmt == "json":
            filepath = output_path.with_suffix(".json")
            atomic_write_json(metadata, filepath)
            exported_files["json"] = filepath

        elif fmt == "yaml":
            try:
                import yaml

                filepath = output_path.with_suffix(".yaml")
                content = yaml.dump(metadata, default_flow_style=False)
                atomic_write_text(content, filepath)
                exported_files["yaml"] = filepath
            except ImportError:
                print("Warning: PyYAML not installed, skipping YAML export")

        else:
            raise ValueError(f"Unsupported format: {fmt}")

    return exported_files


# ============================================================================
# Directory Management
# ============================================================================


def ensure_directory(dirpath: Path) -> Path:
    """
    Ensure directory exists (create if necessary).

    Args:
        dirpath: Directory path

    Returns:
        Directory path
    """
    dirpath = Path(dirpath)
    dirpath.mkdir(parents=True, exist_ok=True)
    return dirpath


def clean_directory(dirpath: Path, pattern: str = "*") -> int:
    """
    Clean files matching pattern from directory.

    Args:
        dirpath: Directory path
        pattern: File pattern to remove

    Returns:
        Number of files removed
    """
    dirpath = Path(dirpath)

    if not dirpath.exists():
        return 0

    count = 0
    for filepath in dirpath.glob(pattern):
        if filepath.is_file():
            filepath.unlink()
            count += 1

    return count


def copy_directory(src: Path, dst: Path) -> None:
    """
    Copy directory recursively.

    Args:
        src: Source directory
        dst: Destination directory
    """
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        raise FileNotFoundError(f"Source directory not found: {src}")

    shutil.copytree(src, dst, dirs_exist_ok=True)


# ============================================================================
# File Information
# ============================================================================


def get_file_info(filepath: Path) -> dict[str, Any]:
    """
    Get file information.

    Args:
        filepath: Path to file

    Returns:
        Dictionary with file information
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    stat = filepath.stat()

    return {
        "filepath": str(filepath),
        "filename": filepath.name,
        "extension": filepath.suffix,
        "size_bytes": stat.st_size,
        "size_mb": stat.st_size / (1024 * 1024),
        "created_time": stat.st_ctime,
        "modified_time": stat.st_mtime,
        "is_file": filepath.is_file(),
        "is_dir": filepath.is_dir(),
    }


def get_directory_size(dirpath: Path) -> int:
    """
    Get total size of directory in bytes.

    Args:
        dirpath: Directory path

    Returns:
        Total size in bytes
    """
    dirpath = Path(dirpath)

    if not dirpath.exists():
        return 0

    total_size = 0
    for filepath in dirpath.rglob("*"):
        if filepath.is_file():
            total_size += filepath.stat().st_size

    return total_size
