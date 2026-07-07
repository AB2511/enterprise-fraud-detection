"""
Feature Transformers

Collection of feature transformers for fraud detection ML pipeline.
Each transformer is responsible for creating a specific group of features
and follows the BaseFeatureTransformer interface.
"""

from ml.features.transformers.base import BaseFeatureTransformer, FeatureMetadata, ValidationResult

# Customer and merchant features
from ml.features.transformers.customer import (
    CustomerTransformer,
    MerchantTransformer,
)

# Device and geographic features
from ml.features.transformers.device import (
    DeviceTransformer,
    GeographicTransformer,
)

# Risk features
from ml.features.transformers.risk import (
    RiskTransformer,
)

# Temporal features
from ml.features.transformers.temporal import (
    HolidayTransformer,
    TemporalTransformer,
)

# Transaction features
from ml.features.transformers.transaction import (
    AmountBucketTransformer,
    AmountPercentileTransformer,
    AmountTransformer,
)

# Velocity features
from ml.features.transformers.velocity import (
    RollingStatisticsTransformer,
    VelocityTransformer,
)

__all__ = [
    # Base classes
    "BaseFeatureTransformer",
    "FeatureMetadata",
    "ValidationResult",
    # Transaction transformers
    "AmountTransformer",
    "AmountBucketTransformer",
    "AmountPercentileTransformer",
    # Temporal transformers
    "TemporalTransformer",
    "HolidayTransformer",
    # Velocity transformers
    "VelocityTransformer",
    "RollingStatisticsTransformer",
    # Customer and merchant transformers
    "CustomerTransformer",
    "MerchantTransformer",
    # Device and geographic transformers
    "DeviceTransformer",
    "GeographicTransformer",
    # Risk transformers
    "RiskTransformer",
]
