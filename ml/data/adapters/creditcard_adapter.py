"""
Credit Card Fraud Detection Dataset Adapter

Adapter for the Kaggle Credit Card Fraud Detection Dataset
(European cardholders transactions).

Dataset source: https://www.kaggle.com/mlg-ulb/creditcardfraud
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ml.data.adapters.base import DatasetAdapter
from ml.utils.logging_config import get_logger
from ml.validation.schemas import DatasetType


class CreditCardAdapter(DatasetAdapter):
    """
    Adapter for Kaggle Credit Card Fraud Detection dataset.
    
    Dataset characteristics:
    - 284,807 transactions over 2 days
    - 492 fraudulent transactions (0.172%)
    - Features V1-V28 are PCA transformed
    - Time: seconds elapsed since first transaction
    - Amount: transaction amount
    - Class: 0=legitimate, 1=fraud
    """

    def __init__(self, raw_data_path: Path):
        """
        Initialize CreditCard adapter.
        
        Args:
            raw_data_path: Path to directory containing creditcard.csv
        """
        super().__init__(raw_data_path)
        self.logger = get_logger(f"ml.adapters.{self.__class__.__name__}")
        self.csv_file = self.raw_data_path / "creditcard.csv"

    def _get_dataset_type(self) -> DatasetType:
        """Return DatasetType.CREDITCARD"""
        return DatasetType.CREDITCARD

    def load_raw_data(self) -> pd.DataFrame:
        """
        Load raw credit card transaction data.
        
        Returns:
            DataFrame with original CreditCard schema
            
        Raises:
            FileNotFoundError: If creditcard.csv not found
            ValueError: If file format is invalid
        """
        if not self.csv_file.exists():
            raise FileNotFoundError(
                f"CreditCard dataset file not found: {self.csv_file}\n"
                f"Please download from: https://www.kaggle.com/mlg-ulb/creditcardfraud"
            )

        try:
            self.logger.info("Loading CreditCard dataset", file_path=str(self.csv_file))

            # Load CSV with optimal dtypes
            df = pd.read_csv(
                self.csv_file,
                dtype={
                    'Time': 'float64',
                    'Amount': 'float64',
                    'Class': 'int8',  # Memory optimization: 0/1 fits in int8
                    # V1-V28 will be float64 by default
                }
            )

            # Validate expected structure
            self._validate_creditcard_schema(df)

            self.logger.info(
                "CreditCard dataset loaded successfully",
                rows=len(df),
                columns=len(df.columns),
                fraud_count=int(df['Class'].sum()),
                fraud_rate=float(df['Class'].mean())
            )

            return df

        except Exception as e:
            self.logger.error("Failed to load CreditCard dataset", error=str(e))
            raise ValueError(f"Invalid CreditCard dataset format: {e}")

    def _validate_creditcard_schema(self, df: pd.DataFrame) -> None:
        """
        Validate that the DataFrame matches expected CreditCard schema.
        
        Args:
            df: DataFrame to validate
            
        Raises:
            ValueError: If schema doesn't match expectations
        """
        # Expected columns
        required_cols = ['Time', 'Amount', 'Class']
        pca_cols = [f'V{i}' for i in range(1, 29)]  # V1 through V28
        expected_cols = required_cols + pca_cols

        # Check all expected columns exist
        missing_cols = set(expected_cols) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing expected columns: {sorted(missing_cols)}")

        # Check for unexpected columns
        extra_cols = set(df.columns) - set(expected_cols)
        if extra_cols:
            self.logger.warning("Unexpected additional columns", extra_columns=list(extra_cols))

        # Validate data types and ranges
        if df['Time'].min() < 0:
            raise ValueError("Time values cannot be negative")

        if df['Amount'].min() < 0:
            raise ValueError("Amount values cannot be negative")

        if not df['Class'].isin([0, 1]).all():
            raise ValueError("Class column must contain only 0 and 1")

        # Check dataset size expectations (should be ~284K transactions)
        if len(df) < 100000:
            self.logger.warning(
                "Dataset seems smaller than expected",
                actual_size=len(df),
                expected_min=280000
            )

    def map_to_standard_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map CreditCard dataset to standardized transaction schema.
        
        The CreditCard dataset uses:
        - Time: seconds elapsed since first transaction
        - V1-V28: PCA-transformed features (anonymized)
        - Amount: transaction amount
        - Class: fraud label (0=legitimate, 1=fraud)
        
        We map this to standard schema with synthetic fields where needed.
        
        Args:
            df: Raw CreditCard DataFrame
            
        Returns:
            DataFrame with standardized schema
        """
        self.logger.info("Mapping CreditCard schema to standard format")

        # Create standardized DataFrame
        standardized = pd.DataFrame()

        # Required standard fields
        standardized['transaction_id'] = self._generate_transaction_ids(len(df))
        standardized['timestamp'] = self._convert_time_to_timestamp(df['Time'])
        standardized['amount'] = df['Amount'].astype('float64')
        standardized['is_fraud'] = df['Class'].astype('bool')

        # Optional standard fields (synthetic/derived)
        standardized['customer_id'] = self._generate_customer_ids(len(df))
        standardized['merchant_id'] = self._generate_merchant_ids(len(df))

        # Dataset-specific features (preserve PCA features)
        for i in range(1, 29):
            col_name = f'V{i}'
            if col_name in df.columns:
                standardized[f'pca_feature_{i:02d}'] = df[col_name].astype('float64')

        # Derived features for enrichment
        standardized['amount_log'] = np.log1p(standardized['amount'])
        standardized['hour'] = standardized['timestamp'].dt.hour
        standardized['day_of_week'] = standardized['timestamp'].dt.dayofweek
        standardized['is_weekend'] = standardized['day_of_week'].isin([5, 6])

        # Transaction categorization based on amount
        standardized['amount_category'] = pd.cut(
            standardized['amount'],
            bins=[0, 10, 50, 200, 1000, float('inf')],
            labels=['micro', 'small', 'medium', 'large', 'xlarge'],
            include_lowest=True
        ).astype(str)

        self.logger.info(
            "Schema mapping completed",
            output_columns=len(standardized.columns),
            standard_fields=4,
            pca_features=28,
            derived_features=len(standardized.columns) - 4 - 28 - 2  # Subtract standard, PCA, and synthetic IDs
        )

        return standardized

    def _generate_transaction_ids(self, n_transactions: int) -> pd.Series:
        """
        Generate synthetic transaction IDs.
        
        Args:
            n_transactions: Number of transactions
            
        Returns:
            Series of transaction IDs
        """
        # Format: CC_YYYYMMDD_XXXXXXXX (CC prefix + date + sequence)
        base_date = "20190101"  # Synthetic date for CreditCard dataset

        transaction_ids = [
            f"CC_{base_date}_{i:08d}" for i in range(1, n_transactions + 1)
        ]

        return pd.Series(transaction_ids, name='transaction_id')

    def _convert_time_to_timestamp(self, time_series: pd.Series) -> pd.Series:
        """
        Convert Time column (seconds elapsed) to proper timestamps.
        
        The original dataset has Time as seconds since first transaction.
        We convert this to proper datetime stamps starting from a base date.
        
        Args:
            time_series: Series with elapsed seconds
            
        Returns:
            Series with datetime timestamps
        """
        # Use a realistic base timestamp (simulated dataset timeframe)
        base_timestamp = datetime(2019, 1, 1, 0, 0, 0)

        # Convert seconds to timedelta and add to base
        timestamps = base_timestamp + pd.to_timedelta(time_series, unit='s')

        return timestamps

    def _generate_customer_ids(self, n_transactions: int) -> pd.Series:
        """
        Generate synthetic but realistic customer IDs.
        
        CreditCard dataset doesn't have customer IDs, so we create synthetic
        ones that follow realistic patterns (customers have multiple transactions).
        
        Args:
            n_transactions: Number of transactions
            
        Returns:
            Series of customer IDs
        """
        # Simulate ~50K unique customers (realistic customer-to-transaction ratio)
        n_customers = min(50000, n_transactions // 3)  # Avg ~3-6 transactions per customer

        # Generate customer ID pool
        customer_pool = [f"CUST_{i:08d}" for i in range(1, n_customers + 1)]

        # Assign customers with realistic distribution
        # Some customers have many transactions, others have few
        np.random.seed(42)  # Deterministic for reproducibility

        # Power-law distribution: few customers with many transactions
        customer_weights = np.random.power(0.5, n_customers)
        customer_weights = customer_weights / customer_weights.sum()

        customer_ids = np.random.choice(
            customer_pool,
            size=n_transactions,
            p=customer_weights
        )

        return pd.Series(customer_ids, name='customer_id')

    def _generate_merchant_ids(self, n_transactions: int) -> pd.Series:
        """
        Generate synthetic merchant IDs.
        
        Args:
            n_transactions: Number of transactions
            
        Returns:
            Series of merchant IDs
        """
        # Simulate ~5K merchants (realistic merchant diversity)
        n_merchants = min(5000, n_transactions // 20)

        merchant_pool = [f"MERCH_{i:06d}" for i in range(1, n_merchants + 1)]

        # Some merchants are more popular than others
        np.random.seed(123)  # Different seed for merchant distribution
        merchant_weights = np.random.exponential(1, n_merchants)
        merchant_weights = merchant_weights / merchant_weights.sum()

        merchant_ids = np.random.choice(
            merchant_pool,
            size=n_transactions,
            p=merchant_weights
        )

        return pd.Series(merchant_ids, name='merchant_id')

    def get_schema_mapping(self) -> dict[str, str]:
        """
        Return mapping from standard schema to CreditCard raw columns.
        
        Returns:
            Dictionary mapping standard names to raw column names
        """
        mapping = {
            # Direct mappings
            'amount': 'Amount',
            'is_fraud': 'Class',
            'time_elapsed': 'Time',

            # PCA features (V1-V28)
            **{f'pca_feature_{i:02d}': f'V{i}' for i in range(1, 29)},

            # Synthetic fields (no source)
            'transaction_id': None,  # Generated
            'timestamp': None,       # Derived from Time
            'customer_id': None,     # Generated
            'merchant_id': None,     # Generated
        }

        return mapping

    def validate(self, df: pd.DataFrame) -> dict[str, any]:
        """
        Validate standardized CreditCard dataset.
        
        Args:
            df: Standardized DataFrame
            
        Returns:
            Validation results dictionary
        """
        validation_results = {
            'schema_valid': True,
            'issues': [],
            'warnings': [],
            'statistics': {}
        }

        try:
            # Schema validation
            required_cols = ['transaction_id', 'timestamp', 'amount', 'is_fraud']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                validation_results['schema_valid'] = False
                validation_results['issues'].append(f"Missing required columns: {missing_cols}")

            # Data quality checks
            if df['amount'].isna().any():
                validation_results['warnings'].append("Missing values in amount column")

            if df['amount'].min() < 0:
                validation_results['issues'].append("Negative amounts detected")

            # Fraud rate validation
            fraud_rate = df['is_fraud'].mean()
            if fraud_rate > 0.1:  # > 10% seems unusually high
                validation_results['warnings'].append(f"High fraud rate: {fraud_rate:.3f}")
            elif fraud_rate < 0.001:  # < 0.1% seems unusually low
                validation_results['warnings'].append(f"Low fraud rate: {fraud_rate:.3f}")

            # Statistics
            validation_results['statistics'] = {
                'total_transactions': len(df),
                'fraud_count': int(df['is_fraud'].sum()),
                'fraud_rate': fraud_rate,
                'amount_stats': {
                    'mean': float(df['amount'].mean()),
                    'median': float(df['amount'].median()),
                    'min': float(df['amount'].min()),
                    'max': float(df['amount'].max()),
                },
                'date_range': {
                    'start': df['timestamp'].min().isoformat(),
                    'end': df['timestamp'].max().isoformat(),
                }
            }

        except Exception as e:
            validation_results['schema_valid'] = False
            validation_results['issues'].append(f"Validation error: {str(e)}")

        return validation_results

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize standardized dataset (data cleaning and preprocessing).
        
        Args:
            df: Standardized DataFrame
            
        Returns:
            Normalized DataFrame
        """
        self.logger.info("Normalizing CreditCard dataset")

        normalized = df.copy()

        # Handle missing values
        if normalized['amount'].isna().any():
            # Fill missing amounts with median
            normalized['amount'].fillna(normalized['amount'].median(), inplace=True)
            self.logger.warning("Filled missing amounts with median")

        # Remove duplicates (if any)
        initial_count = len(normalized)
        normalized = normalized.drop_duplicates(subset=['transaction_id'])
        if len(normalized) < initial_count:
            removed = initial_count - len(normalized)
            self.logger.warning(f"Removed {removed} duplicate transactions")

        # Outlier handling for amounts (cap at 99.9th percentile)
        amount_cap = normalized['amount'].quantile(0.999)
        outliers = (normalized['amount'] > amount_cap).sum()
        if outliers > 0:
            normalized.loc[normalized['amount'] > amount_cap, 'amount'] = amount_cap
            self.logger.info(f"Capped {outliers} amount outliers at {amount_cap:.2f}")

        # Ensure data types
        normalized['is_fraud'] = normalized['is_fraud'].astype('bool')
        normalized['amount'] = normalized['amount'].astype('float64')

        self.logger.info(
            "Normalization completed",
            final_rows=len(normalized),
            removed_duplicates=initial_count - len(normalized),
            capped_outliers=outliers
        )

        return normalized

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply dataset-specific transformations.
        
        Args:
            df: Normalized DataFrame
            
        Returns:
            Transformed DataFrame
        """
        self.logger.info("Applying CreditCard-specific transformations")

        transformed = df.copy()

        # Amount transformations
        transformed['amount_zscore'] = (
            transformed['amount'] - transformed['amount'].mean()
        ) / transformed['amount'].std()

        # Time-based features
        transformed['hour_sin'] = np.sin(2 * np.pi * transformed['hour'] / 24)
        transformed['hour_cos'] = np.cos(2 * np.pi * transformed['hour'] / 24)

        # PCA feature statistics (if available)
        pca_cols = [col for col in transformed.columns if col.startswith('pca_feature_')]
        if pca_cols:
            transformed['pca_feature_sum'] = transformed[pca_cols].sum(axis=1)
            transformed['pca_feature_mean'] = transformed[pca_cols].mean(axis=1)
            transformed['pca_feature_std'] = transformed[pca_cols].std(axis=1)

        self.logger.info(
            "Transformations applied",
            new_features=len(transformed.columns) - len(df.columns)
        )

        return transformed

    def export(self, df: pd.DataFrame, output_dir: Path, format: str = 'parquet') -> Path:
        """
        Export processed dataset.
        
        Args:
            df: DataFrame to export
            output_dir: Output directory
            format: Export format ('parquet', 'csv', 'feather')
            
        Returns:
            Path to exported file
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"creditcard_processed_{timestamp}.{format}"
        output_path = output_dir / filename

        if format == 'parquet':
            df.to_parquet(output_path, index=False, compression='snappy')
        elif format == 'csv':
            df.to_csv(output_path, index=False)
        elif format == 'feather':
            df.to_feather(output_path)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        self.logger.info(f"Dataset exported to {output_path}")
        return output_path
