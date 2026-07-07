"""
Base Dataset Adapter

Abstract base class for dataset adapters. All dataset-specific adapters
must inherit from this class and implement the required methods.

This design allows pluggable datasets without changing downstream code.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from ml.validation.schemas import (
    DatasetMetadata,
    DatasetType,
    ProcessingStage,
)


class DatasetAdapter(ABC):
    """
    Abstract base class for dataset adapters.
    
    Each dataset (CreditCard, IEEE-CIS, etc.) implements this interface.
    This abstraction allows the pipeline to work with any dataset without
    modification to downstream feature engineering and validation code.
    """

    def __init__(self, raw_data_path: Path):
        """
        Initialize adapter with path to raw data.
        
        Args:
            raw_data_path: Path to raw dataset directory
        """
        self.raw_data_path = Path(raw_data_path)
        self.dataset_type: DatasetType = self._get_dataset_type()
        self.version: str = "v1.0.0"

        # Will be populated after load()
        self.raw_df: pd.DataFrame | None = None
        self.metadata: DatasetMetadata | None = None

    @abstractmethod
    def _get_dataset_type(self) -> DatasetType:
        """Return the dataset type enum"""
        pass

    @abstractmethod
    def load_raw_data(self) -> pd.DataFrame:
        """
        Load raw data from source files.
        
        Returns:
            DataFrame with raw transaction data
        """
        pass

    @abstractmethod
    def map_to_standard_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map dataset-specific columns to standard schema.
        
        This is the key method that normalizes different datasets to a
        common schema expected by downstream pipeline components.
        
        Args:
            df: Raw DataFrame with dataset-specific columns
            
        Returns:
            DataFrame with standardized column names:
                - transaction_id
                - timestamp
                - amount
                - is_fraud (target)
                - customer_id (if available)
                - merchant_id (if available)
                - ... other optional fields
        """
        pass

    @abstractmethod
    def get_schema_mapping(self) -> dict[str, str]:
        """
        Return mapping from raw column names to standard schema.
        
        Returns:
            Dictionary: {standard_name: raw_column_name}
            
        Example:
            {
                "transaction_id": "TransactionID",
                "amount": "TransactionAmt",
                "is_fraud": "isFraud",
            }
        """
        pass

    def load(self) -> pd.DataFrame:
        """
        Load and standardize the dataset.
        
        This is the main entry point. It:
        1. Loads raw data
        2. Maps to standard schema
        3. Generates metadata
        4. Validates basic structure
        
        Returns:
            Standardized DataFrame
        """
        print(f"Loading {self.dataset_type.value} dataset from {self.raw_data_path}")

        # Load raw data
        self.raw_df = self.load_raw_data()
        print(f"✓ Loaded {len(self.raw_df):,} raw records")

        # Map to standard schema
        standardized_df = self.map_to_standard_schema(self.raw_df)
        print(f"✓ Mapped to standard schema ({len(standardized_df.columns)} columns)")

        # Generate metadata
        self.metadata = self._generate_metadata(standardized_df)
        print(f"✓ Generated metadata (fraud rate: {self.metadata.fraud_rate:.4f})")

        # Basic validation
        self._validate_standard_schema(standardized_df)
        print("✓ Validated standard schema")

        return standardized_df

    def _generate_metadata(self, df: pd.DataFrame) -> DatasetMetadata:
        """
        Generate dataset metadata.
        
        Args:
            df: Standardized DataFrame
            
        Returns:
            DatasetMetadata object
        """
        # Calculate statistics
        num_records = len(df)
        num_fraud = int(df['is_fraud'].sum()) if 'is_fraud' in df.columns else 0
        num_legitimate = num_records - num_fraud
        fraud_rate = num_fraud / num_records if num_records > 0 else 0.0

        # Temporal coverage
        date_range_start = None
        date_range_end = None
        if 'timestamp' in df.columns:
            date_range_start = df['timestamp'].min()
            date_range_end = df['timestamp'].max()

        # Calculate data hash for integrity
        data_hash = self._calculate_data_hash(df)

        return DatasetMetadata(
            dataset_name=f"{self.dataset_type.value}_raw",
            dataset_type=self.dataset_type,
            version=self.version,
            stage=ProcessingStage.RAW,
            num_records=num_records,
            num_fraud=num_fraud,
            num_legitimate=num_legitimate,
            fraud_rate=fraud_rate,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            data_hash=data_hash,
            validation_passed=False,  # Will be updated after validation
        )

    def _calculate_data_hash(self, df: pd.DataFrame) -> str:
        """
        Calculate SHA256 hash of DataFrame for integrity verification.
        
        Args:
            df: DataFrame to hash
            
        Returns:
            SHA256 hash string
        """
        # Use a subset of columns and first/last rows for efficiency
        hash_data = {
            'num_rows': len(df),
            'num_cols': len(df.columns),
            'columns': list(df.columns),
            'first_row': df.iloc[0].to_dict() if len(df) > 0 else {},
            'last_row': df.iloc[-1].to_dict() if len(df) > 0 else {},
        }
        hash_str = json.dumps(hash_data, sort_keys=True, default=str)
        return hashlib.sha256(hash_str.encode()).hexdigest()

    def _validate_standard_schema(self, df: pd.DataFrame) -> None:
        """
        Validate that DataFrame has required standard schema columns.
        
        Args:
            df: DataFrame to validate
            
        Raises:
            ValueError: If required columns are missing
        """
        required_columns = ['transaction_id', 'timestamp', 'amount', 'is_fraud']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(
                f"Missing required columns in standard schema: {missing_columns}"
            )

        # Check data types
        if not pd.api.types.is_numeric_dtype(df['amount']):
            raise ValueError("Column 'amount' must be numeric")

        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            raise ValueError("Column 'timestamp' must be datetime")

        if not pd.api.types.is_bool_dtype(df['is_fraud']) and \
           not pd.api.types.is_integer_dtype(df['is_fraud']):
            raise ValueError("Column 'is_fraud' must be boolean or integer")

    def save_metadata(self, output_path: Path) -> None:
        """
        Save dataset metadata to JSON file.
        
        Args:
            output_path: Path to save metadata.json
        """
        if self.metadata is None:
            raise ValueError("Metadata not generated. Call load() first.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write(self.metadata.model_dump_json(indent=2))

        print(f"✓ Saved metadata to {output_path}")

    def get_schema_info(self) -> dict[str, str]:
        """
        Get schema information for documentation.
        
        Returns:
            Dictionary with schema field descriptions
        """
        if self.raw_df is None:
            raise ValueError("Dataset not loaded. Call load() first.")

        schema_info = {}
        for col in self.raw_df.columns:
            schema_info[col] = {
                'dtype': str(self.raw_df[col].dtype),
                'missing_count': int(self.raw_df[col].isna().sum()),
                'missing_rate': float(self.raw_df[col].isna().mean()),
            }

        return schema_info

    def get_statistics(self) -> dict[str, any]:
        """
        Get basic dataset statistics.
        
        Returns:
            Dictionary with dataset statistics
        """
        if self.raw_df is None:
            raise ValueError("Dataset not loaded. Call load() first.")

        stats = {
            'num_records': len(self.raw_df),
            'num_columns': len(self.raw_df.columns),
            'memory_usage_mb': self.raw_df.memory_usage(deep=True).sum() / 1024 / 1024,
            'columns': list(self.raw_df.columns),
        }

        if 'is_fraud' in self.raw_df.columns:
            stats['fraud_distribution'] = self.raw_df['is_fraud'].value_counts().to_dict()

        return stats

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"type={self.dataset_type.value}, "
            f"version={self.version}, "
            f"records={len(self.raw_df) if self.raw_df is not None else 0}"
            f")"
        )
