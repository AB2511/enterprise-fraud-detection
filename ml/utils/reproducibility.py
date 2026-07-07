"""
Reproducibility Module

Ensures reproducible ML pipeline execution through:
- Global random seed management
- NumPy seed configuration
- Pandas configuration
- Environment snapshot
- Dependency versions
- Pipeline configuration snapshots

Every pipeline run must be fully reproducible.
"""

import hashlib
import json
import os
import platform
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ============================================================================
# Random Seed Management
# ============================================================================


class ReproducibilityManager:
    """
    Manages reproducibility settings for ML pipeline.

    Ensures deterministic behavior across:
    - Python random
    - NumPy random
    - Pandas sampling
    - Hash seeds

    All settings are captured in a snapshot for full reproducibility.
    """

    def __init__(self, seed: int = 42):
        """
        Initialize reproducibility manager.

        Args:
            seed: Global random seed (default: 42)
        """
        self.seed = seed
        self.environment_snapshot: dict[str, Any] | None = None
        self.config_snapshot: dict[str, Any] | None = None

    def set_global_seed(self) -> None:
        """
        Set global random seed for all random number generators.

        This ensures deterministic behavior across:
        - Python's random module
        - NumPy's random module
        - Pandas sampling operations
        - Hash seeds (for dictionary ordering)
        """
        # Python random
        random.seed(self.seed)

        # NumPy random
        np.random.seed(self.seed)

        # Pandas random (for sampling, shuffling)
        # Note: Pandas uses NumPy's random, so this is redundant but explicit

        # Hash seed for deterministic dictionary ordering
        os.environ["PYTHONHASHSEED"] = str(self.seed)

        print(f"✓ Global random seed set to {self.seed}")

    def configure_pandas(self) -> None:
        """
        Configure Pandas for reproducibility.

        Sets Pandas display and computation options for consistency.
        """
        # Display options (for logging consistency)
        pd.set_option("display.max_rows", 100)
        pd.set_option("display.max_columns", 50)
        pd.set_option("display.width", 120)
        pd.set_option("display.precision", 6)

        # Computation options
        pd.set_option("mode.chained_assignment", "raise")  # Raise on chained assignment

        print("✓ Pandas configuration set for reproducibility")

    def capture_environment_snapshot(self) -> dict[str, Any]:
        """
        Capture environment snapshot for reproducibility.

        Returns:
            Dictionary with environment information
        """
        snapshot = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "seed": self.seed,
            # Python environment
            "python_version": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            # Package versions
            "numpy_version": np.__version__,
            "pandas_version": pd.__version__,
            # Environment variables (selected)
            "pythonhashseed": os.environ.get("PYTHONHASHSEED", "not set"),
            "python_path": os.environ.get("PYTHONPATH", "not set"),
            # Working directory
            "cwd": os.getcwd(),
        }

        # Try to get additional package versions
        try:
            import sklearn

            snapshot["sklearn_version"] = sklearn.__version__
        except ImportError:
            snapshot["sklearn_version"] = "not installed"

        self.environment_snapshot = snapshot
        return snapshot

    def capture_config_snapshot(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Capture pipeline configuration snapshot.

        Args:
            config: Pipeline configuration dictionary

        Returns:
            Configuration snapshot with hash
        """
        # Create deterministic config string
        config_str = json.dumps(config, sort_keys=True, default=str)
        config_hash = hashlib.sha256(config_str.encode()).hexdigest()

        snapshot = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "config": config,
            "config_hash": config_hash,
        }

        self.config_snapshot = snapshot
        return snapshot

    def save_snapshot(self, output_path: Path) -> None:
        """
        Save reproducibility snapshot to file.

        Args:
            output_path: Path to save snapshot JSON
        """
        if self.environment_snapshot is None:
            self.capture_environment_snapshot()

        snapshot = {
            "seed": self.seed,
            "environment": self.environment_snapshot,
            "config": self.config_snapshot,
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(snapshot, f, indent=2, default=str)

        print(f"✓ Reproducibility snapshot saved to {output_path}")

    @classmethod
    def load_snapshot(cls, snapshot_path: Path) -> "ReproducibilityManager":
        """
        Load reproducibility snapshot and create manager.

        Args:
            snapshot_path: Path to snapshot JSON

        Returns:
            ReproducibilityManager configured from snapshot
        """
        with open(snapshot_path) as f:
            snapshot = json.load(f)

        manager = cls(seed=snapshot["seed"])
        manager.environment_snapshot = snapshot.get("environment")
        manager.config_snapshot = snapshot.get("config")

        return manager

    def verify_environment(self, expected_snapshot: dict[str, Any]) -> bool:
        """
        Verify current environment matches expected snapshot.

        Args:
            expected_snapshot: Expected environment snapshot

        Returns:
            True if environment matches, False otherwise
        """
        current = self.capture_environment_snapshot()

        # Check critical fields
        critical_fields = ["python_version", "numpy_version", "pandas_version"]

        mismatches = []
        for field in critical_fields:
            if current.get(field) != expected_snapshot.get(field):
                mismatches.append(
                    f"{field}: expected {expected_snapshot.get(field)}, "
                    f"got {current.get(field)}"
                )

        if mismatches:
            print("⚠ Environment mismatch detected:")
            for mismatch in mismatches:
                print(f"  - {mismatch}")
            return False

        print("✓ Environment matches expected snapshot")
        return True

    def initialize_reproducible_environment(self) -> None:
        """
        Initialize full reproducible environment.

        This is the main entry point. Call this at the start of any pipeline.
        """
        print(f"Initializing reproducible environment (seed={self.seed})...")

        # Set seeds
        self.set_global_seed()

        # Configure Pandas
        self.configure_pandas()

        # Capture environment
        self.capture_environment_snapshot()

        print("✓ Reproducible environment initialized")


# ============================================================================
# Dependency Version Tracking
# ============================================================================


def capture_dependency_versions() -> dict[str, str]:
    """
    Capture versions of all installed packages.

    Returns:
        Dictionary of package name to version
    """
    try:
        import pkg_resources

        installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
        return installed_packages
    except Exception as e:
        print(f"Warning: Could not capture dependency versions: {e}")
        return {}


def save_dependency_versions(output_path: Path) -> None:
    """
    Save dependency versions to file.

    Args:
        output_path: Path to save versions JSON
    """
    versions = capture_dependency_versions()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    version_data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_packages": len(versions),
        "packages": versions,
    }

    with open(output_path, "w") as f:
        json.dump(version_data, f, indent=2)

    print(f"✓ Saved {len(versions)} package versions to {output_path}")


# ============================================================================
# Configuration Hash
# ============================================================================


def compute_config_hash(config: dict[str, Any]) -> str:
    """
    Compute deterministic hash of configuration.

    Args:
        config: Configuration dictionary

    Returns:
        SHA256 hash string
    """
    config_str = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(config_str.encode()).hexdigest()


# ============================================================================
# Global Reproducibility Instance
# ============================================================================

# Global instance (can be imported and used across modules)
_global_reproducibility_manager: ReproducibilityManager | None = None


def get_reproducibility_manager(seed: int = 42) -> ReproducibilityManager:
    """
    Get or create global reproducibility manager.

    Args:
        seed: Random seed

    Returns:
        ReproducibilityManager instance
    """
    global _global_reproducibility_manager

    if _global_reproducibility_manager is None:
        _global_reproducibility_manager = ReproducibilityManager(seed=seed)
        _global_reproducibility_manager.initialize_reproducible_environment()

    return _global_reproducibility_manager


def reset_reproducibility_manager() -> None:
    """Reset global reproducibility manager (useful for testing)"""
    global _global_reproducibility_manager
    _global_reproducibility_manager = None
