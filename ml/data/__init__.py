"""
Data Engineering Module

Handles dataset loading, adapters, processors, and versioning.
"""

from ml.data.adapters.base import DatasetAdapter
from ml.data.versioning.dataset_version import DatasetVersion, DatasetVersionRegistry

__all__ = [
    "DatasetAdapter",
    "DatasetVersion",
    "DatasetVersionRegistry",
]
