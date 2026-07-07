"""
Dataset Adapters

Contains concrete implementations of dataset adapters for different
fraud detection datasets.
"""

from ml.data.adapters.base import DatasetAdapter
from ml.data.adapters.creditcard_adapter import CreditCardAdapter
from ml.data.adapters.ieee_cis_adapter import IEEECISAdapter

__all__ = [
    "DatasetAdapter",
    "CreditCardAdapter",
    "IEEECISAdapter",
]
