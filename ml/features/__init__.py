"""
Features Module

Feature engineering and transformation components for the fraud detection ML pipeline.

This module provides:
- Base feature transformer interface
- Concrete feature transformers for different domains
- Feature registry for metadata management
- Local feature store for offline storage
- Pipeline integration for end-to-end workflows
"""

from ml.features.pipeline import FeatureEngineeringStage, FeatureSelectionStage
from ml.features.registry import FeatureRegistry, FeatureRegistryEntry
from ml.features.store import FeatureSetMetadata, LocalFeatureStore

# Import transformers
from ml.features.transformers import (
    AmountBucketTransformer,
    AmountPercentileTransformer,
    # Transaction transformers
    AmountTransformer,
    # Customer and merchant transformers
    CustomerTransformer,
    # Device and geographic transformers
    DeviceTransformer,
    GeographicTransformer,
    HolidayTransformer,
    MerchantTransformer,
    # Risk transformers
    RiskTransformer,
    RollingStatisticsTransformer,
    # Temporal transformers
    TemporalTransformer,
    # Velocity transformers
    VelocityTransformer,
)
from ml.features.transformers.base import BaseFeatureTransformer, FeatureMetadata, ValidationResult

__all__ = [
    # Base classes
    "BaseFeatureTransformer",
    "FeatureMetadata",
    "ValidationResult",
    # Registry and store
    "FeatureRegistry",
    "FeatureRegistryEntry",
    "LocalFeatureStore",
    "FeatureSetMetadata",
    # Pipeline stages
    "FeatureEngineeringStage",
    "FeatureSelectionStage",
    # Transformers
    "AmountTransformer",
    "AmountBucketTransformer",
    "AmountPercentileTransformer",
    "TemporalTransformer",
    "HolidayTransformer",
    "VelocityTransformer",
    "RollingStatisticsTransformer",
    "CustomerTransformer",
    "MerchantTransformer",
    "DeviceTransformer",
    "GeographicTransformer",
    "RiskTransformer",
]
