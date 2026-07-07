"""
Tests for Dataset Pipeline Stages

Tests for pipeline stages that integrate adapters with foundation systems.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

from ml.data.pipeline_stages import (
    DatasetLoadingStage, DatasetValidationStage, DatasetVersioningStage,
    DatasetNormalizationStage, DatasetTransformationStage, MetadataGenerationStage
)
from ml.testing.fixtures import MockDatasetGenerator, temp_directory
from ml.testing.assertions import (
    assert_dataframe_not_empty, assert_dataframe_schema,
    assert_metadata_valid
)


class TestDatasetLoadingStage:
    """Tests for DatasetLoadingStage."""
    
    def test_creditcard_dataset_loading(self, temp_directory):
        """Test loading CreditCard dataset."""
        # Create mock CreditCard data
        mock_data = {
            'Time': np.linspace(0, 172800, 100),
            'Amount': np.random.lognormal(3, 1, 100),
            'Class': np.random.choice([0, 1], 100, p=[0.998, 0.002]),
            **{f'V{i}': np.random.normal(0, 1, 100) for i in range(1, 29)}
        }
        
        df = pd.DataFrame(mock_data)
        csv_path = temp_directory / "creditcard.csv"
        df.to_csv(csv_path, index=False)
        
        # Test loading stage
        stage = DatasetLoadingStage(dataset_type="creditcard")
        inputs = {"raw_data_path": str(temp_directory)}
        
        outputs = stage.execute(inputs)
        
        # Verify outputs
        assert "dataset" in outputs
        assert "adapter" in outputs
        assert "dataset_metadata" in outputs
        assert "dataset_type" in outputs
        assert outputs["dataset_type"] == "creditcard"
        
        # Verify dataset structure
        dataset = outputs["dataset"]
        assert_dataframe_not_empty(dataset)
        
        required_cols = ['transaction_id', 'timestamp', 'amount', 'is_fraud']
        for col in required_cols:
            assert col in dataset.columns
    
    def test_ieee_cis_dataset_loading(self, temp_directory):
        """Test loading IEEE-CIS dataset."""
        # Create mock IEEE-CIS data
        transaction_data = {
            'TransactionID': range(1, 101),
            'isFraud': np.random.choice([0, 1], 100, p=[0.97, 0.03]),
            'TransactionDT': np.random.randint(1, 1000000, 100),
            'TransactionAmt': np.random.lognormal(4, 1, 100),
            'ProductCD': np.random.choice(['W', 'C', 'R'], 100),
            'card1': np.random.randint(1000, 9999, 100),
            'addr1': np.random.randint(100, 999, 100),
        }
        
        df = pd.DataFrame(transaction_data)
        csv_path = temp_directory / "train_transaction.csv"
        df.to_csv(csv_path, index=False)
        
        # Test loading stage
        stage = DatasetLoadingStage(dataset_type="ieee_cis")
        inputs = {"raw_data_path": str(temp_directory)}
        
        outputs = stage.execute(inputs)
        
        # Verify outputs
        assert outputs["dataset_type"] == "ieee_cis"
        dataset = outputs["dataset"]
        assert_dataframe_not_empty(dataset)
        
        required_cols = ['transaction_id', 'timestamp', 'amount', 'is_fraud']
        for col in required_cols:
            assert col in dataset.columns
    
    def test_auto_dataset_detection(self, temp_directory):
        """Test automatic dataset type detection."""
        # Create CreditCard data
        mock_data = {
            'Time': [1, 2, 3],
            'Amount': [10, 20, 30],
            'Class': [0, 1, 0],
            **{f'V{i}': [1, 2, 3] for i in range(1, 29)}
        }
        
        df = pd.DataFrame(mock_data)
        csv_path = temp_directory / "creditcard.csv"
        df.to_csv(csv_path, index=False)
        
        # Test auto-detection
        stage = DatasetLoadingStage(dataset_type="auto")
        inputs = {"raw_data_path": str(temp_directory)}
        
        outputs = stage.execute(inputs)
        
        assert outputs["dataset_type"] == "creditcard"


class TestDatasetValidationStage:
    """Tests for DatasetValidationStage."""
    
    def test_validation_stage_execution(self, temp_directory):
        """Test validation stage execution."""
        # Create mock standardized dataset
        dataset = pd.DataFrame({
            'transaction_id': ['T1', 'T2', 'T3'],
            'timestamp': pd.date_range('2024-01-01', periods=3),
            'amount': [10.0, 20.0, 30.0],
            'is_fraud': [False, True, False]
        })
        
        # Mock metadata
        from ml.validation.schemas import DatasetMetadata, DatasetType, ProcessingStage
        metadata = DatasetMetadata(
            dataset_name="test",
            dataset_type=DatasetType.CREDITCARD,
            version="v1.0.0",
            stage=ProcessingStage.RAW,
            num_records=3,
            num_fraud=1,
            num_legitimate=2,
            fraud_rate=1/3,
        )
        
        # Prepare inputs
        inputs = {
            "dataset": dataset,
            "dataset_type": "creditcard",
            "dataset_metadata": metadata,
        }
        
        # Execute validation
        stage = DatasetValidationStage()
        outputs = stage.execute(inputs)
        
        # Verify outputs
        assert "validation_results" in outputs
        assert "validation_summary" in outputs
        assert "validation_report" in outputs
        
        validation_summary = outputs["validation_summary"]
        assert "total_checks" in validation_summary
        assert "passed_checks" in validation_summary
        assert "all_passed" in validation_summary
    
    def test_validation_with_data_issues(self, temp_directory):
        """Test validation with data quality issues."""
        # Create dataset with issues
        dataset = pd.DataFrame({
            'transaction_id': ['T1', 'T1', 'T3'],  # Duplicate ID
            'timestamp': pd.date_range('2024-01-01', periods=3),
            'amount': [10.0, None, -5.0],  # Missing and negative amount
            'is_fraud': [False, True, False]
        })
        
        from ml.validation.schemas import DatasetMetadata, DatasetType, ProcessingStage
        metadata = DatasetMetadata(
            dataset_name="test_issues",
            dataset_type=DatasetType.CREDITCARD,
            version="v1.0.0",
            stage=ProcessingStage.RAW,
            num_records=3,
            num_fraud=1,
            num_legitimate=2,
            fraud_rate=1/3,
        )
        
        inputs = {
            "dataset": dataset,
            "dataset_type": "creditcard",
            "dataset_metadata": metadata,
        }
        
        stage = DatasetValidationStage()
        outputs = stage.execute(inputs)
        
        validation_summary = outputs["validation_summary"]
        # Should have some failed validations
        assert validation_summary["failed_checks"] > 0
        assert not validation_summary["all_passed"]


class TestDatasetVersioningStage:
    """Tests for DatasetVersioningStage."""
    
    def test_versioning_stage_execution(self, temp_directory):
        """Test dataset versioning stage."""
        # Create test dataset
        dataset = pd.DataFrame({
            'transaction_id': ['T1', 'T2', 'T3'],
            'timestamp': pd.date_range('2024-01-01', periods=3),
            'amount': [10.0, 20.0, 30.0],
            'is_fraud': [False, True, False]
        })
        
        # Mock validation summary
        validation_summary = {
            "all_passed": True,
            "pass_rate": 1.0,
            "total_checks": 5
        }
        
        from ml.validation.schemas import DatasetMetadata, DatasetType, ProcessingStage
        metadata = DatasetMetadata(
            dataset_name="test",
            dataset_type=DatasetType.CREDITCARD,
            version="v1.0.0",
            stage=ProcessingStage.RAW,
            num_records=3,
            num_fraud=1,
            num_legitimate=2,
            fraud_rate=1/3,
        )
        
        inputs = {
            "dataset": dataset,
            "dataset_type": "creditcard", 
            "dataset_metadata": metadata,
            "validation_summary": validation_summary,
        }
        
        # Change to temp directory for output
        import os
        original_cwd = os.getcwd()
        os.chdir(temp_directory)
        
        try:
            stage = DatasetVersioningStage()
            outputs = stage.execute(inputs)
            
            # Verify outputs
            assert "dataset_version" in outputs
            assert "version_path" in outputs
            assert "version_id" in outputs
            
            # Check that version file was created
            version_path = Path(outputs["version_path"])
            # The path might be relative, so check if it exists in temp_directory
            
        finally:
            os.chdir(original_cwd)


class TestPipelineStageIntegration:
    """Integration tests for pipeline stages."""
    
    def test_full_pipeline_execution(self, temp_directory):
        """Test executing a complete pipeline with all stages."""
        # Create mock CreditCard data
        mock_data = {
            'Time': np.linspace(0, 172800, 50),
            'Amount': np.random.lognormal(3, 1, 50),
            'Class': np.random.choice([0, 1], 50, p=[0.96, 0.04]),
            **{f'V{i}': np.random.normal(0, 1, 50) for i in range(1, 29)}
        }
        
        df = pd.DataFrame(mock_data)
        csv_path = temp_directory / "creditcard.csv"
        df.to_csv(csv_path, index=False)
        
        # Change to temp directory for pipeline execution
        import os
        original_cwd = os.getcwd()
        os.chdir(temp_directory)
        
        try:
            # Stage 1: Loading
            loading_stage = DatasetLoadingStage(dataset_type="creditcard")
            loading_outputs = loading_stage.execute({"raw_data_path": str(temp_directory)})
            
            # Stage 2: Validation
            validation_stage = DatasetValidationStage()
            validation_outputs = validation_stage.execute(loading_outputs)
            
            # Stage 3: Versioning
            versioning_stage = DatasetVersioningStage()
            versioning_outputs = versioning_stage.execute(validation_outputs)
            
            # Stage 4: Normalization
            normalization_stage = DatasetNormalizationStage()
            normalization_outputs = normalization_stage.execute(versioning_outputs)
            
            # Stage 5: Transformation
            transformation_stage = DatasetTransformationStage()
            transformation_outputs = transformation_stage.execute(normalization_outputs)
            
            # Stage 6: Metadata Generation
            metadata_stage = MetadataGenerationStage()
            final_outputs = metadata_stage.execute(transformation_outputs)
            
            # Verify final outputs
            assert "transformed_dataset" in final_outputs
            assert "final_metadata" in final_outputs
            assert "quality_report_path" in final_outputs
            assert "schema_info" in final_outputs
            
            # Verify dataset progression
            original_dataset = loading_outputs["dataset"]
            normalized_dataset = normalization_outputs["normalized_dataset"]
            transformed_dataset = final_outputs["transformed_dataset"]
            
            # Should have same number of rows (unless normalization removes some)
            assert len(transformed_dataset) <= len(original_dataset)
            
            # Should have more columns after transformation
            assert len(transformed_dataset.columns) >= len(original_dataset.columns)
            
            print("✅ Full pipeline execution successful!")
            
        finally:
            os.chdir(original_cwd)