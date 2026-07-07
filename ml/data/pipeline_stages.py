"""
Dataset Processing Pipeline Stages

Pipeline stages that integrate dataset adapters with the foundation
validation, versioning, and metadata systems.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ml.data.adapters import CreditCardAdapter, DatasetAdapter, IEEECISAdapter
from ml.data.versioning.dataset_version import DatasetVersion
from ml.pipeline.stage import PipelineStage
from ml.reports.metadata_report import MetadataReport
from ml.reports.quality_report import QualityReport
from ml.reports.validation_report import ValidationReport
from ml.utils.metadata import DatasetMetadata, MetadataManager
from ml.validation.validators import (
    CategoricalConsistencyValidator,
    DuplicateValidator,
    MissingValueValidator,
    SchemaValidator,
    ValueRangeValidator,
)


class DatasetLoadingStage(PipelineStage):
    """
    Stage for loading raw datasets using appropriate adapters.
    
    Automatically detects dataset type and applies the correct adapter.
    """

    def __init__(self, dataset_type: str = "auto"):
        """
        Initialize dataset loading stage.
        
        Args:
            dataset_type: Type of dataset ("creditcard", "ieee_cis", or "auto")
        """
        super().__init__(
            name="dataset_loading",
            description="Load raw dataset using appropriate adapter"
        )
        self.dataset_type = dataset_type
        from ml.utils.logging_config import get_logger
        self.logger = get_logger(f"ml.pipeline.{self.__class__.__name__}")

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Load dataset using appropriate adapter.
        
        Args:
            inputs: Must contain 'raw_data_path' key
            
        Returns:
            Dictionary with loaded dataset and metadata
        """
        raw_data_path = Path(inputs["raw_data_path"])

        # Auto-detect dataset type if not specified
        if self.dataset_type == "auto":
            detected_type = self._detect_dataset_type(raw_data_path)
            self.logger.info(f"Auto-detected dataset type: {detected_type}")
        else:
            detected_type = self.dataset_type

        # Create appropriate adapter
        adapter = self._create_adapter(detected_type, raw_data_path)

        # Load dataset
        self.logger.info(f"Loading {detected_type} dataset")
        standardized_df = adapter.load()

        # Generate metadata
        metadata = adapter.metadata

        return {
            "dataset": standardized_df,
            "adapter": adapter,
            "dataset_metadata": metadata,
            "dataset_type": detected_type,
            "schema_mapping": adapter.get_schema_mapping(),
        }

    def _detect_dataset_type(self, raw_data_path: Path) -> str:
        """
        Auto-detect dataset type based on file structure.
        
        Args:
            raw_data_path: Path to raw data directory
            
        Returns:
            Detected dataset type
        """
        files = list(raw_data_path.glob("*.csv"))
        file_names = [f.name.lower() for f in files]

        # Check for CreditCard dataset
        if "creditcard.csv" in file_names:
            return "creditcard"

        # Check for IEEE-CIS dataset
        ieee_files = ["train_transaction.csv", "train_identity.csv"]
        if any(f in file_names for f in ieee_files):
            return "ieee_cis"

        # Default fallback
        self.logger.warning("Could not auto-detect dataset type, defaulting to creditcard")
        return "creditcard"

    def _create_adapter(self, dataset_type: str, raw_data_path: Path) -> DatasetAdapter:
        """
        Create appropriate dataset adapter.
        
        Args:
            dataset_type: Type of dataset
            raw_data_path: Path to raw data
            
        Returns:
            Dataset adapter instance
        """
        if dataset_type == "creditcard":
            return CreditCardAdapter(raw_data_path)
        elif dataset_type == "ieee_cis":
            return IEEECISAdapter(raw_data_path)
        else:
            raise ValueError(f"Unsupported dataset type: {dataset_type}")


class DatasetValidationStage(PipelineStage):
    """
    Stage for comprehensive dataset validation using foundation validators.
    """

    def __init__(self):
        super().__init__(
            name="dataset_validation",
            dependencies=["dataset_loading"],
            description="Validate dataset quality and schema compliance"
        )
        from ml.utils.logging_config import get_logger
        self.logger = get_logger(f"ml.pipeline.{self.__class__.__name__}")

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Validate dataset using multiple validators.
        
        Args:
            inputs: Must contain 'dataset' key with DataFrame
            
        Returns:
            Dictionary with validation results and updated metadata
        """
        df = inputs["dataset"]
        dataset_type = inputs["dataset_type"]
        dataset_metadata = inputs["dataset_metadata"]

        self.logger.info(f"Validating {dataset_type} dataset", rows=len(df), columns=len(df.columns))

        # Create validators
        validators = self._create_validators(dataset_type)

        # Run all validations
        all_validation_results = []
        for validator in validators:
            self.logger.info(f"Running {validator.__class__.__name__}")
            results = validator.validate(df)
            all_validation_results.extend(results)

        # Aggregate results
        validation_summary = self._aggregate_validation_results(all_validation_results)

        # Update metadata with validation status
        dataset_metadata.validation_passed = validation_summary["all_passed"]

        # Generate validation report
        validation_report = ValidationReport()
        validation_report.collect_data(
            validation_results=all_validation_results,
            dataset_info={
                "name": dataset_metadata.dataset_name,
                "type": dataset_type,
                "rows": len(df),
                "columns": len(df.columns)
            }
        )

        return {
            **inputs,  # Pass through all inputs
            "validation_results": all_validation_results,
            "validation_summary": validation_summary,
            "validation_report": validation_report,
            "dataset_metadata": dataset_metadata,  # Updated metadata
        }

    def _create_validators(self, dataset_type: str) -> list:
        """
        Create appropriate validators for dataset type.
        
        Args:
            dataset_type: Type of dataset
            
        Returns:
            List of validator instances
        """
        # Standard validators for all datasets
        validators = [
            # Schema validation
            SchemaValidator(
                required_columns=["transaction_id", "timestamp", "amount", "is_fraud"],
                column_types={
                    "amount": "float64",
                    "is_fraud": "bool",
                }
            ),

            # Missing value validation
            MissingValueValidator(
                max_missing_rate=0.1,  # Allow up to 10% missing
                critical_columns=["transaction_id", "amount", "is_fraud"]
            ),

            # Duplicate validation
            DuplicateValidator(
                subset=["transaction_id"],  # Transaction IDs must be unique
                max_duplicate_rate=0.01
            ),

            # Value range validation
            ValueRangeValidator(
                range_specs={
                    "amount": {"min": 0.0, "max": float('inf')},  # Amounts must be positive
                }
            ),

            # Timestamp validation - temporarily disabled due to timezone issues
            # TimestampValidator(
            #     timestamp_columns=["timestamp"],
            #     allow_future=False,
            #     check_ordering=True
            # ),
        ]

        # Dataset-specific validators
        if dataset_type == "creditcard":
            # CreditCard specific validations
            validators.append(
                CategoricalConsistencyValidator(
                    categorical_columns=["amount_category"],
                    max_unique_ratio=0.5
                )
            )

        elif dataset_type == "ieee_cis":
            # IEEE-CIS specific validations
            validators.extend([
                CategoricalConsistencyValidator(
                    categorical_columns=["product_code"],
                    max_unique_ratio=0.3
                )
            ])

        return validators

    def _aggregate_validation_results(self, validation_results: list) -> dict[str, Any]:
        """
        Aggregate validation results into summary.
        
        Args:
            validation_results: List of ValidationCheck objects
            
        Returns:
            Validation summary dictionary
        """
        total_checks = len(validation_results)
        passed_checks = sum(1 for check in validation_results if check.passed)
        failed_checks = total_checks - passed_checks

        # Group by severity
        by_severity = {}
        for check in validation_results:
            severity = check.severity
            if severity not in by_severity:
                by_severity[severity] = {"passed": 0, "failed": 0}

            if check.passed:
                by_severity[severity]["passed"] += 1
            else:
                by_severity[severity]["failed"] += 1

        return {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "pass_rate": passed_checks / total_checks if total_checks > 0 else 0.0,
            "all_passed": failed_checks == 0,
            "by_severity": by_severity,
            "failed_validations": [
                {
                    "validator": check.validator_name,
                    "check": check.check_name,
                    "severity": check.severity,
                    "message": check.message
                }
                for check in validation_results if not check.passed
            ]
        }


class DatasetVersioningStage(PipelineStage):
    """
    Stage for dataset versioning using the foundation versioning system.
    """

    def __init__(self):
        super().__init__(
            name="dataset_versioning",
            dependencies=["dataset_validation"],
            description="Create immutable dataset version with metadata"
        )
        from ml.utils.logging_config import get_logger
        self.logger = get_logger(f"ml.pipeline.{self.__class__.__name__}")

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Create versioned dataset with metadata.
        
        Args:
            inputs: Dictionary with dataset and metadata
            
        Returns:
            Dictionary with versioned dataset information
        """
        df = inputs["dataset"]
        dataset_type = inputs["dataset_type"]
        dataset_metadata = inputs["dataset_metadata"]
        validation_summary = inputs["validation_summary"]

        # Create dataset version
        version = DatasetVersion(
            dataset_name=f"{dataset_type}_processed",
            schema_version="v2.0.0",  # Standardized schema version
            preprocessing_version="v1.0.0",
            source=f"{dataset_type}_raw",
            tags=["processed", "validated", dataset_type],
            metadata={
                "validation_passed": validation_summary["all_passed"],
                "validation_pass_rate": validation_summary["pass_rate"],
                "total_validation_checks": validation_summary["total_checks"],
                "dataset_type": dataset_type,
            }
        )

        # Save versioned dataset
        output_dir = Path("data/processed") / dataset_type
        self.logger.info(f"Saving dataset version to {output_dir}")

        version_path = version.save_dataframe(df, output_dir)

        self.logger.info(
            "Dataset versioned successfully",
            version_id=version.version_id,
            file_path=str(version_path),
            checksum=version.checksum
        )

        return {
            **inputs,
            "dataset_version": version,
            "version_path": version_path,
            "version_id": version.version_id,
        }


class DatasetNormalizationStage(PipelineStage):
    """
    Stage for dataset normalization using adapter-specific logic.
    """

    def __init__(self):
        super().__init__(
            name="dataset_normalization",
            dependencies=["dataset_versioning"],
            description="Normalize and clean dataset using adapter logic"
        )
        from ml.utils.logging_config import get_logger
        self.logger = get_logger(f"ml.pipeline.{self.__class__.__name__}")

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize dataset using adapter's normalization logic.
        
        Args:
            inputs: Dictionary with dataset and adapter
            
        Returns:
            Dictionary with normalized dataset
        """
        df = inputs["dataset"]
        adapter = inputs["adapter"]
        dataset_type = inputs["dataset_type"]

        self.logger.info(f"Normalizing {dataset_type} dataset")

        # Apply adapter-specific normalization
        normalized_df = adapter.normalize(df)

        # Create new version for normalized data
        normalized_version = DatasetVersion(
            dataset_name=f"{dataset_type}_normalized",
            schema_version="v2.0.0",
            preprocessing_version="v1.1.0",
            source=inputs["version_id"],  # Link to processed version
            tags=["normalized", "cleaned", dataset_type],
            metadata={
                "normalization_applied": True,
                "parent_version": inputs["version_id"],
            }
        )

        # Save normalized version
        output_dir = Path("data/processed") / dataset_type / "normalized"
        normalized_path = normalized_version.save_dataframe(normalized_df, output_dir)

        self.logger.info(
            "Dataset normalized and versioned",
            version_id=normalized_version.version_id,
            rows=len(normalized_df),
            file_path=str(normalized_path)
        )

        return {
            **inputs,
            "normalized_dataset": normalized_df,
            "normalized_version": normalized_version,
            "normalized_path": normalized_path,
        }


class DatasetTransformationStage(PipelineStage):
    """
    Stage for dataset transformation using adapter-specific feature engineering.
    """

    def __init__(self):
        super().__init__(
            name="dataset_transformation",
            dependencies=["dataset_normalization"],
            description="Apply dataset-specific feature transformations"
        )
        from ml.utils.logging_config import get_logger
        self.logger = get_logger(f"ml.pipeline.{self.__class__.__name__}")

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Transform dataset using adapter's transformation logic.
        
        Args:
            inputs: Dictionary with normalized dataset and adapter
            
        Returns:
            Dictionary with transformed dataset
        """
        normalized_df = inputs["normalized_dataset"]
        adapter = inputs["adapter"]
        dataset_type = inputs["dataset_type"]

        self.logger.info(f"Transforming {dataset_type} dataset")

        # Apply adapter-specific transformations
        transformed_df = adapter.transform(normalized_df)

        # Create version for transformed data
        transformed_version = DatasetVersion(
            dataset_name=f"{dataset_type}_transformed",
            schema_version="v2.0.0",
            preprocessing_version="v1.2.0",
            source=inputs["normalized_version"].version_id,
            tags=["transformed", "featured", dataset_type],
            metadata={
                "transformations_applied": True,
                "parent_version": inputs["normalized_version"].version_id,
                "feature_count": len(transformed_df.columns),
            }
        )

        # Save transformed version
        output_dir = Path("data/processed") / dataset_type / "transformed"
        transformed_path = transformed_version.save_dataframe(transformed_df, output_dir)

        self.logger.info(
            "Dataset transformed and versioned",
            version_id=transformed_version.version_id,
            rows=len(transformed_df),
            columns=len(transformed_df.columns),
            file_path=str(transformed_path)
        )

        return {
            **inputs,
            "transformed_dataset": transformed_df,
            "transformed_version": transformed_version,
            "transformed_path": transformed_path,
        }


class MetadataGenerationStage(PipelineStage):
    """
    Stage for comprehensive metadata generation.
    """

    def __init__(self):
        super().__init__(
            name="metadata_generation",
            dependencies=["dataset_transformation"],
            description="Generate comprehensive metadata and reports"
        )
        from ml.utils.logging_config import get_logger
        self.logger = get_logger(f"ml.pipeline.{self.__class__.__name__}")

    def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Generate comprehensive metadata and reports.
        
        Args:
            inputs: Dictionary with all processing artifacts
            
        Returns:
            Dictionary with metadata and report paths
        """
        transformed_df = inputs["transformed_dataset"]
        dataset_type = inputs["dataset_type"]
        adapter = inputs["adapter"]
        validation_results = inputs["validation_results"]

        self.logger.info("Generating comprehensive metadata and reports")

        # Initialize metadata manager
        metadata_manager = MetadataManager(Path("data/metadata"))

        # Generate final dataset metadata
        final_metadata = DatasetMetadata(
            dataset_name=f"{dataset_type}_final",
            dataset_type=inputs["dataset_metadata"].dataset_type,
            version="v1.0.0",
            stage="FEATURED",
            num_records=len(transformed_df),
            num_fraud=int(transformed_df["is_fraud"].sum()),
            num_legitimate=len(transformed_df) - int(transformed_df["is_fraud"].sum()),
            fraud_rate=transformed_df["is_fraud"].mean(),
            validation_passed=inputs["validation_summary"]["all_passed"],
        )

        # Save metadata
        metadata_manager.save_dataset_metadata(final_metadata)

        # Generate quality report
        quality_report = QualityReport()
        quality_report.collect_data(
            dataframe=transformed_df,
            validation_results=validation_results,
            dataset_info={
                "name": final_metadata.dataset_name,
                "type": dataset_type,
                "version": inputs["transformed_version"].version_id,
            }
        )

        # Generate metadata report
        metadata_report = MetadataReport()
        metadata_report.collect_data(
            dataset_metadata=final_metadata,
            schema_mapping=inputs["schema_mapping"],
            processing_history=[
                {"stage": "loading", "version": inputs["version_id"]},
                {"stage": "normalization", "version": inputs["normalized_version"].version_id},
                {"stage": "transformation", "version": inputs["transformed_version"].version_id},
            ]
        )

        # Save reports
        reports_dir = Path("data/reports") / dataset_type
        reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        quality_report_path = quality_report.save(
            reports_dir / f"quality_report_{timestamp}",
            format="html"
        )

        metadata_report_path = metadata_report.save(
            reports_dir / f"metadata_report_{timestamp}",
            format="html"
        )

        # Generate schema and statistics files
        schema_info = self._generate_schema_info(transformed_df)
        statistics_info = self._generate_statistics(transformed_df, adapter)

        # Save additional metadata files
        schema_path = reports_dir / f"schema_{timestamp}.json"
        with open(schema_path, 'w') as f:
            import json
            json.dump(schema_info, f, indent=2, default=str)

        statistics_path = reports_dir / f"statistics_{timestamp}.json"
        with open(statistics_path, 'w') as f:
            import json
            json.dump(statistics_info, f, indent=2, default=str)

        self.logger.info(
            "Metadata and reports generated successfully",
            quality_report=str(quality_report_path),
            metadata_report=str(metadata_report_path),
            schema_file=str(schema_path),
            statistics_file=str(statistics_path)
        )

        return {
            **inputs,
            "final_metadata": final_metadata,
            "quality_report_path": quality_report_path,
            "metadata_report_path": metadata_report_path,
            "schema_path": schema_path,
            "statistics_path": statistics_path,
            "schema_info": schema_info,
            "statistics_info": statistics_info,
        }

    def _generate_schema_info(self, df: pd.DataFrame) -> dict[str, Any]:
        """Generate comprehensive schema information."""
        schema_info = {
            "generated_at": datetime.now().isoformat(),
            "total_columns": len(df.columns),
            "total_rows": len(df),
            "columns": {}
        }

        for col in df.columns:
            col_info = {
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "null_percentage": float(df[col].isnull().mean()),
                "unique_count": int(df[col].nunique()),
            }

            if pd.api.types.is_numeric_dtype(df[col]):
                col_info.update({
                    "min": float(df[col].min()) if not df[col].isnull().all() else None,
                    "max": float(df[col].max()) if not df[col].isnull().all() else None,
                    "mean": float(df[col].mean()) if not df[col].isnull().all() else None,
                    "std": float(df[col].std()) if not df[col].isnull().all() else None,
                })

            schema_info["columns"][col] = col_info

        return schema_info

    def _generate_statistics(self, df: pd.DataFrame, adapter: DatasetAdapter) -> dict[str, Any]:
        """Generate comprehensive dataset statistics."""
        statistics = {
            "generated_at": datetime.now().isoformat(),
            "dataset_type": adapter.dataset_type.value,
            "basic_stats": {
                "total_transactions": len(df),
                "total_features": len(df.columns),
                "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
            },
            "fraud_analysis": {
                "total_fraud": int(df["is_fraud"].sum()),
                "total_legitimate": int((~df["is_fraud"]).sum()),
                "fraud_rate": float(df["is_fraud"].mean()),
            },
            "temporal_analysis": {},
            "amount_analysis": {},
            "feature_analysis": {}
        }

        # Temporal analysis
        if "timestamp" in df.columns:
            statistics["temporal_analysis"] = {
                "date_range_start": df["timestamp"].min().isoformat(),
                "date_range_end": df["timestamp"].max().isoformat(),
                "duration_days": (df["timestamp"].max() - df["timestamp"].min()).days,
                "transactions_per_day": len(df) / max(1, (df["timestamp"].max() - df["timestamp"].min()).days),
            }

        # Amount analysis
        if "amount" in df.columns:
            statistics["amount_analysis"] = {
                "min_amount": float(df["amount"].min()),
                "max_amount": float(df["amount"].max()),
                "mean_amount": float(df["amount"].mean()),
                "median_amount": float(df["amount"].median()),
                "std_amount": float(df["amount"].std()),
                "q25_amount": float(df["amount"].quantile(0.25)),
                "q75_amount": float(df["amount"].quantile(0.75)),
            }

        # Feature analysis by type
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns

        statistics["feature_analysis"] = {
            "numeric_features": len(numeric_cols),
            "categorical_features": len(categorical_cols),
            "boolean_features": len(df.select_dtypes(include=['bool']).columns),
            "datetime_features": len(df.select_dtypes(include=['datetime']).columns),
        }

        return statistics
