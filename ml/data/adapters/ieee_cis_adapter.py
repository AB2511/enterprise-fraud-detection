"""
IEEE-CIS Fraud Detection Dataset Adapter

Adapter for the IEEE-CIS Fraud Detection Dataset from Kaggle competition.
This dataset contains real-world e-commerce transactions with rich feature set.

Dataset source: https://www.kaggle.com/c/ieee-fraud-detection
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ml.data.adapters.base import DatasetAdapter
from ml.utils.logging_config import get_logger
from ml.validation.schemas import DatasetType


class IEEECISAdapter(DatasetAdapter):
    """
    Adapter for IEEE-CIS Fraud Detection dataset.
    
    Dataset characteristics:
    - 590,540 transactions in train set
    - 506,691 transactions in test set
    - Rich feature set: Identity, Transaction, and derived features
    - Transaction amount, product codes, email domains, device info
    - isFraud: binary target (train set only)
    - Features: C1-C14 (counting), D1-D15 (timedelta), M1-M9 (match), V1-V339 (Vesta features)
    """

    def __init__(self, raw_data_path: Path):
        """
        Initialize IEEE-CIS adapter.
        
        Args:
            raw_data_path: Path to directory containing train/test CSV files
        """
        super().__init__(raw_data_path)
        self.logger = get_logger(f"ml.adapters.{self.__class__.__name__}")

        # IEEE-CIS dataset files
        self.train_transaction_file = self.raw_data_path / "train_transaction.csv"
        self.train_identity_file = self.raw_data_path / "train_identity.csv"
        self.test_transaction_file = self.raw_data_path / "test_transaction.csv"
        self.test_identity_file = self.raw_data_path / "test_identity.csv"

    def _get_dataset_type(self) -> DatasetType:
        """Return DatasetType.IEEE_CIS"""
        return DatasetType.IEEE_CIS

    def load_raw_data(self) -> pd.DataFrame:
        """
        Load raw IEEE-CIS transaction data.
        
        Returns:
            DataFrame with original IEEE-CIS schema (train set with labels)
            
        Raises:
            FileNotFoundError: If required CSV files not found
            ValueError: If file format is invalid
        """
        # Check for required files
        if not self.train_transaction_file.exists():
            raise FileNotFoundError(
                f"IEEE-CIS train_transaction.csv not found: {self.train_transaction_file}\n"
                f"Please download from: https://www.kaggle.com/c/ieee-fraud-detection/data"
            )

        try:
            self.logger.info("Loading IEEE-CIS transaction data", file_path=str(self.train_transaction_file))

            # Load main transaction data
            transaction_df = pd.read_csv(self.train_transaction_file)

            # Load identity data if available
            identity_df = None
            if self.train_identity_file.exists():
                self.logger.info("Loading IEEE-CIS identity data", file_path=str(self.train_identity_file))
                identity_df = pd.read_csv(self.train_identity_file)

                # Merge identity data with transactions
                transaction_df = transaction_df.merge(
                    identity_df,
                    on='TransactionID',
                    how='left'
                )
                self.logger.info(
                    "Merged identity data",
                    transaction_rows=len(transaction_df),
                    identity_rows=len(identity_df)
                )
            else:
                self.logger.warning("Identity data file not found, proceeding with transactions only")

            # Validate schema
            self._validate_ieee_cis_schema(transaction_df)

            self.logger.info(
                "IEEE-CIS dataset loaded successfully",
                rows=len(transaction_df),
                columns=len(transaction_df.columns),
                fraud_count=int(transaction_df['isFraud'].sum()),
                fraud_rate=float(transaction_df['isFraud'].mean())
            )

            return transaction_df

        except Exception as e:
            self.logger.error("Failed to load IEEE-CIS dataset", error=str(e))
            raise ValueError(f"Invalid IEEE-CIS dataset format: {e}")

    def _validate_ieee_cis_schema(self, df: pd.DataFrame) -> None:
        """
        Validate that DataFrame matches expected IEEE-CIS schema.
        
        Args:
            df: DataFrame to validate
            
        Raises:
            ValueError: If schema doesn't match expectations
        """
        # Core required columns
        required_cols = [
            'TransactionID', 'isFraud', 'TransactionDT', 'TransactionAmt',
            'ProductCD', 'card1', 'card2', 'card3', 'card4', 'card5', 'card6',
            'addr1', 'addr2', 'dist1', 'dist2'
        ]

        # Check required columns
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            # Some columns might be optional, only fail on critical ones
            critical_cols = ['TransactionID', 'isFraud', 'TransactionDT', 'TransactionAmt']
            missing_critical = [col for col in critical_cols if col in missing_cols]
            if missing_critical:
                raise ValueError(f"Missing critical columns: {missing_critical}")
            else:
                self.logger.warning("Missing optional columns", missing_columns=missing_cols)

        # Validate data types and ranges
        if df['TransactionDT'].min() <= 0:
            raise ValueError("TransactionDT must be positive")

        if df['TransactionAmt'].min() < 0:
            raise ValueError("TransactionAmt cannot be negative")

        if not df['isFraud'].isin([0, 1]).all():
            raise ValueError("isFraud column must contain only 0 and 1")

        # Check for reasonable dataset size
        if len(df) < 100000:
            self.logger.warning(
                "Dataset seems smaller than expected",
                actual_size=len(df),
                expected_min=500000
            )

    def map_to_standard_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map IEEE-CIS dataset to standardized transaction schema.
        
        IEEE-CIS features:
        - TransactionID: unique identifier
        - TransactionDT: timedelta from reference point
        - TransactionAmt: transaction amount
        - isFraud: fraud label
        - ProductCD: product code
        - card1-card6: card information
        - addr1-addr2: address information
        - C1-C14: counting features
        - D1-D15: timedelta features
        - M1-M9: match features
        - V1-V339: Vesta engineered features
        
        Args:
            df: Raw IEEE-CIS DataFrame
            
        Returns:
            DataFrame with standardized schema
        """
        self.logger.info("Mapping IEEE-CIS schema to standard format")

        # Create standardized DataFrame
        standardized = pd.DataFrame()

        # Required standard fields
        standardized['transaction_id'] = df['TransactionID'].astype(str)
        standardized['timestamp'] = self._convert_transaction_dt_to_timestamp(df['TransactionDT'])
        standardized['amount'] = df['TransactionAmt'].astype('float64')
        standardized['is_fraud'] = df['isFraud'].astype('bool')

        # Optional standard fields (derived from IEEE-CIS features)
        standardized['customer_id'] = self._derive_customer_ids(df)
        standardized['merchant_id'] = self._derive_merchant_ids(df)

        # Product information
        if 'ProductCD' in df.columns:
            standardized['product_code'] = df['ProductCD'].astype(str)

        # Card information
        card_cols = [f'card{i}' for i in range(1, 7)]
        existing_card_cols = [col for col in card_cols if col in df.columns]
        for col in existing_card_cols:
            standardized[f'card_{col[-1]}'] = df[col]

        # Address information
        if 'addr1' in df.columns:
            standardized['billing_address_1'] = df['addr1']
        if 'addr2' in df.columns:
            standardized['billing_address_2'] = df['addr2']

        # Distance features
        if 'dist1' in df.columns:
            standardized['distance_1'] = df['dist1']
        if 'dist2' in df.columns:
            standardized['distance_2'] = df['dist2']

        # Categorical features (C1-C14)
        c_cols = [f'C{i}' for i in range(1, 15)]
        existing_c_cols = [col for col in c_cols if col in df.columns]
        for col in existing_c_cols:
            standardized[f'count_feature_{col[1:]}'] = df[col]

        # Time delta features (D1-D15)
        d_cols = [f'D{i}' for i in range(1, 16)]
        existing_d_cols = [col for col in d_cols if col in df.columns]
        for col in existing_d_cols:
            standardized[f'timedelta_feature_{col[1:]}'] = df[col]

        # Match features (M1-M9)
        m_cols = [f'M{i}' for i in range(1, 10)]
        existing_m_cols = [col for col in m_cols if col in df.columns]
        for col in existing_m_cols:
            standardized[f'match_feature_{col[1:]}'] = df[col]

        # Vesta engineered features (V1-V339) - sample important ones
        v_cols = [f'V{i}' for i in range(1, 340)]
        existing_v_cols = [col for col in v_cols if col in df.columns]

        # Take first 50 V features to avoid too many columns
        important_v_cols = existing_v_cols[:50]
        for col in important_v_cols:
            standardized[f'vesta_feature_{col[1:].zfill(3)}'] = df[col]

        # Identity features (if available)
        identity_features = [
            'id_01', 'id_02', 'id_03', 'id_04', 'id_05', 'id_06', 'id_07', 'id_08',
            'id_09', 'id_10', 'id_11', 'id_12', 'id_13', 'id_14', 'id_15', 'id_16',
            'id_17', 'id_18', 'id_19', 'id_20', 'id_21', 'id_22', 'id_23', 'id_24',
            'id_25', 'id_26', 'id_27', 'id_28', 'id_29', 'id_30', 'id_31', 'id_32',
            'id_33', 'id_34', 'id_35', 'id_36', 'id_37', 'id_38',
            'DeviceType', 'DeviceInfo'
        ]

        for col in identity_features:
            if col in df.columns:
                standardized[f'identity_{col}'] = df[col]

        # Derived features for enrichment
        standardized['amount_log'] = np.log1p(standardized['amount'])
        standardized['hour'] = standardized['timestamp'].dt.hour
        standardized['day_of_week'] = standardized['timestamp'].dt.dayofweek
        standardized['is_weekend'] = standardized['day_of_week'].isin([5, 6])

        # Transaction categorization
        standardized['amount_category'] = pd.cut(
            standardized['amount'],
            bins=[0, 20, 100, 500, 2000, float('inf')],
            labels=['micro', 'small', 'medium', 'large', 'xlarge'],
            include_lowest=True
        ).astype(str)

        self.logger.info(
            "Schema mapping completed",
            output_columns=len(standardized.columns),
            standard_fields=6,
            ieee_features=len([col for col in standardized.columns if any(
                prefix in col for prefix in ['count_', 'timedelta_', 'match_', 'vesta_', 'identity_']
            )]),
            derived_features=5
        )

        return standardized

    def _convert_transaction_dt_to_timestamp(self, transaction_dt: pd.Series) -> pd.Series:
        """
        Convert TransactionDT (seconds from reference) to proper timestamps.
        
        Args:
            transaction_dt: Series with transaction time deltas
            
        Returns:
            Series with datetime timestamps
        """
        # IEEE-CIS dataset uses seconds from an unknown reference point
        # We'll use a realistic reference date
        reference_date = datetime(2017, 12, 1, 0, 0, 0)

        # Convert to timestamps
        timestamps = reference_date + pd.to_timedelta(transaction_dt, unit='s')

        return timestamps

    def _derive_customer_ids(self, df: pd.DataFrame) -> pd.Series:
        """
        Derive customer IDs from IEEE-CIS features.
        
        Uses card information and other identifying features to create
        synthetic but consistent customer groupings.
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Series of customer IDs
        """
        # Combine card features to create customer signatures
        customer_features = []

        # Primary card identifier
        if 'card1' in df.columns:
            customer_features.append(df['card1'].fillna('unknown').astype(str))

        # Secondary identifiers
        for col in ['card2', 'card3', 'addr1']:
            if col in df.columns:
                customer_features.append(df[col].fillna('').astype(str))

        # Combine features to create customer signature
        if customer_features:
            customer_signature = pd.Series(['_'.join(row) for row in zip(*customer_features)])

            # Convert to customer IDs
            unique_signatures = customer_signature.unique()
            signature_to_id = {
                sig: f"IEEE_CUST_{i:08d}"
                for i, sig in enumerate(unique_signatures, 1)
            }

            customer_ids = customer_signature.map(signature_to_id)
        else:
            # Fallback: generate sequential IDs
            customer_ids = pd.Series([f"IEEE_CUST_{i:08d}" for i in range(1, len(df) + 1)])

        return customer_ids

    def _derive_merchant_ids(self, df: pd.DataFrame) -> pd.Series:
        """
        Derive merchant IDs from IEEE-CIS features.
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Series of merchant IDs
        """
        # Use product code and address information for merchant grouping
        merchant_features = []

        if 'ProductCD' in df.columns:
            merchant_features.append(df['ProductCD'].fillna('unknown').astype(str))

        if 'addr2' in df.columns:
            merchant_features.append(df['addr2'].fillna('').astype(str))

        # Combine features
        if merchant_features:
            merchant_signature = pd.Series(['_'.join(row) for row in zip(*merchant_features)])

            # Convert to merchant IDs
            unique_signatures = merchant_signature.unique()
            signature_to_id = {
                sig: f"IEEE_MERCH_{i:06d}"
                for i, sig in enumerate(unique_signatures, 1)
            }

            merchant_ids = merchant_signature.map(signature_to_id)
        else:
            # Fallback: generate based on transaction patterns
            n_merchants = len(df) // 50  # Assume ~50 transactions per merchant on average
            merchant_pool = [f"IEEE_MERCH_{i:06d}" for i in range(1, n_merchants + 1)]

            np.random.seed(456)
            merchant_ids = pd.Series(np.random.choice(merchant_pool, len(df)))

        return merchant_ids

    def get_schema_mapping(self) -> dict[str, str]:
        """
        Return mapping from standard schema to IEEE-CIS raw columns.
        
        Returns:
            Dictionary mapping standard names to raw column names
        """
        mapping = {
            # Direct mappings
            'transaction_id': 'TransactionID',
            'amount': 'TransactionAmt',
            'is_fraud': 'isFraud',
            'transaction_time': 'TransactionDT',
            'product_code': 'ProductCD',

            # Card features
            **{f'card_{i}': f'card{i}' for i in range(1, 7)},

            # Address features
            'billing_address_1': 'addr1',
            'billing_address_2': 'addr2',
            'distance_1': 'dist1',
            'distance_2': 'dist2',

            # Counting features (C1-C14)
            **{f'count_feature_{i}': f'C{i}' for i in range(1, 15)},

            # Timedelta features (D1-D15)
            **{f'timedelta_feature_{i}': f'D{i}' for i in range(1, 16)},

            # Match features (M1-M9)
            **{f'match_feature_{i}': f'M{i}' for i in range(1, 10)},

            # Vesta features (V1-V50 subset)
            **{f'vesta_feature_{i:03d}': f'V{i}' for i in range(1, 51)},

            # Synthetic fields
            'timestamp': None,      # Derived from TransactionDT
            'customer_id': None,    # Derived from card/addr features
            'merchant_id': None,    # Derived from product/addr features
        }

        return mapping

    def validate(self, df: pd.DataFrame) -> dict[str, any]:
        """
        Validate standardized IEEE-CIS dataset.
        
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

            # Check for duplicate transaction IDs
            duplicate_count = df['transaction_id'].duplicated().sum()
            if duplicate_count > 0:
                validation_results['issues'].append(f"Duplicate transaction IDs: {duplicate_count}")

            # Fraud rate validation
            fraud_rate = df['is_fraud'].mean()
            if fraud_rate > 0.2:  # > 20% seems unusually high
                validation_results['warnings'].append(f"High fraud rate: {fraud_rate:.3f}")
            elif fraud_rate < 0.005:  # < 0.5% seems unusually low for IEEE-CIS
                validation_results['warnings'].append(f"Low fraud rate: {fraud_rate:.3f}")

            # Statistics
            validation_results['statistics'] = {
                'total_transactions': len(df),
                'fraud_count': int(df['is_fraud'].sum()),
                'fraud_rate': fraud_rate,
                'unique_customers': df['customer_id'].nunique(),
                'unique_merchants': df['merchant_id'].nunique(),
                'amount_stats': {
                    'mean': float(df['amount'].mean()),
                    'median': float(df['amount'].median()),
                    'min': float(df['amount'].min()),
                    'max': float(df['amount'].max()),
                },
                'date_range': {
                    'start': df['timestamp'].min().isoformat(),
                    'end': df['timestamp'].max().isoformat(),
                    'duration_days': (df['timestamp'].max() - df['timestamp'].min()).days,
                }
            }

        except Exception as e:
            validation_results['schema_valid'] = False
            validation_results['issues'].append(f"Validation error: {str(e)}")

        return validation_results

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize standardized IEEE-CIS dataset.
        
        Args:
            df: Standardized DataFrame
            
        Returns:
            Normalized DataFrame
        """
        self.logger.info("Normalizing IEEE-CIS dataset")

        normalized = df.copy()

        # Handle missing values in amount
        if normalized['amount'].isna().any():
            normalized['amount'].fillna(normalized['amount'].median(), inplace=True)
            self.logger.warning("Filled missing amounts with median")

        # Remove duplicates by transaction_id
        initial_count = len(normalized)
        normalized = normalized.drop_duplicates(subset=['transaction_id'])
        if len(normalized) < initial_count:
            removed = initial_count - len(normalized)
            self.logger.warning(f"Removed {removed} duplicate transactions")

        # Outlier handling for amounts
        amount_cap = normalized['amount'].quantile(0.995)  # More conservative for IEEE-CIS
        outliers = (normalized['amount'] > amount_cap).sum()
        if outliers > 0:
            normalized.loc[normalized['amount'] > amount_cap, 'amount'] = amount_cap
            self.logger.info(f"Capped {outliers} amount outliers at {amount_cap:.2f}")

        # Handle missing values in key features
        key_numeric_cols = [col for col in normalized.columns
                           if col.startswith(('count_feature_', 'timedelta_feature_', 'vesta_feature_'))]

        for col in key_numeric_cols:
            if normalized[col].isna().any():
                # Fill with median for numeric features
                normalized[col].fillna(normalized[col].median(), inplace=True)

        # Handle categorical features
        categorical_cols = [col for col in normalized.columns
                          if col.startswith(('match_feature_', 'identity_', 'card_'))]

        for col in categorical_cols:
            if normalized[col].isna().any():
                # Fill with mode or 'unknown'
                mode_val = normalized[col].mode()
                fill_val = mode_val.iloc[0] if len(mode_val) > 0 else 'unknown'
                normalized[col].fillna(fill_val, inplace=True)

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
        Apply IEEE-CIS specific transformations.
        
        Args:
            df: Normalized DataFrame
            
        Returns:
            Transformed DataFrame
        """
        self.logger.info("Applying IEEE-CIS specific transformations")

        transformed = df.copy()

        # Amount transformations
        transformed['amount_zscore'] = (
            transformed['amount'] - transformed['amount'].mean()
        ) / transformed['amount'].std()

        # Time-based features
        transformed['hour_sin'] = np.sin(2 * np.pi * transformed['hour'] / 24)
        transformed['hour_cos'] = np.cos(2 * np.pi * transformed['hour'] / 24)

        # Customer transaction frequency (approximate)
        customer_counts = transformed['customer_id'].value_counts()
        transformed['customer_transaction_count'] = transformed['customer_id'].map(customer_counts)

        # Merchant transaction frequency
        merchant_counts = transformed['merchant_id'].value_counts()
        transformed['merchant_transaction_count'] = transformed['merchant_id'].map(merchant_counts)

        # Feature aggregations
        vesta_cols = [col for col in transformed.columns if col.startswith('vesta_feature_')]
        if len(vesta_cols) > 0:
            transformed['vesta_feature_sum'] = transformed[vesta_cols].sum(axis=1)
            transformed['vesta_feature_mean'] = transformed[vesta_cols].mean(axis=1)
            transformed['vesta_feature_std'] = transformed[vesta_cols].std(axis=1)

        count_cols = [col for col in transformed.columns if col.startswith('count_feature_')]
        if len(count_cols) > 0:
            transformed['count_feature_sum'] = transformed[count_cols].sum(axis=1)

        self.logger.info(
            "Transformations applied",
            new_features=len(transformed.columns) - len(df.columns)
        )

        return transformed

    def export(self, df: pd.DataFrame, output_dir: Path, format: str = 'parquet') -> Path:
        """
        Export processed IEEE-CIS dataset.
        
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
        filename = f"ieee_cis_processed_{timestamp}.{format}"
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
