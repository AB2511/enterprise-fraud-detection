"""
Unit tests for schema validator.

Tests:
- Schema validation logic
- Missing column detection
- Target validation
- Duplicate detection
"""

import pandas as pd
import pytest

from ml.training.data.config import IEEECISSchema
from ml.training.data.schema_validator import SchemaValidationResult, validate_schema


@pytest.fixture
def valid_transaction_df():
    """Create valid transaction DataFrame."""
    return pd.DataFrame(
        {
            "TransactionID": [1, 2, 3, 4, 5],
            "isFraud": [0, 1, 0, 0, 1],
            "TransactionDT": [100, 200, 300, 400, 500],
            "TransactionAmt": [10.0, 20.0, 30.0, 40.0, 50.0],
        }
    )


@pytest.fixture
def valid_identity_df():
    """Create valid identity DataFrame."""
    return pd.DataFrame(
        {
            "TransactionID": [1, 2, 3],
            "id_01": [0.1, 0.2, 0.3],
        }
    )


class TestSchemaValidationResult:
    """Test SchemaValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = SchemaValidationResult(is_valid=True, errors=[], warnings=[])
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_invalid_result(self):
        """Test creating an invalid result."""
        result = SchemaValidationResult(
            is_valid=False, errors=["Error 1", "Error 2"], warnings=["Warning 1"]
        )
        assert not result.is_valid
        assert len(result.errors) == 2
        assert len(result.warnings) == 1

    def test_str_representation_valid(self):
        """Test string representation for valid result."""
        result = SchemaValidationResult(is_valid=True)
        str_result = str(result)
        assert "PASSED" in str_result

    def test_str_representation_invalid(self):
        """Test string representation for invalid result."""
        result = SchemaValidationResult(
            is_valid=False,
            errors=["Missing column"],
            warnings=["Low fraud rate"],
            missing_columns=["TransactionID"],
        )
        str_result = str(result)
        assert "FAILED" in str_result
        assert "Missing column" in str_result
        assert "Low fraud rate" in str_result


class TestValidateSchema:
    """Test schema validation function."""

    def test_validate_valid_transaction(self, valid_transaction_df):
        """Test validation passes for valid transaction table."""
        result = validate_schema(valid_transaction_df, table_name="transaction")
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_valid_identity(self, valid_identity_df):
        """Test validation passes for valid identity table."""
        result = validate_schema(valid_identity_df, table_name="identity")
        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_missing_transaction_id(self, valid_transaction_df):
        """Test validation fails for missing TransactionID."""
        df = valid_transaction_df.drop(columns=["TransactionID"])
        result = validate_schema(df, table_name="transaction")

        assert not result.is_valid
        assert any("TransactionID" in error for error in result.errors)
        assert "TransactionID" in result.missing_columns

    def test_validate_missing_target(self, valid_transaction_df):
        """Test validation fails for missing isFraud."""
        df = valid_transaction_df.drop(columns=["isFraud"])
        result = validate_schema(df, table_name="transaction")

        assert not result.is_valid
        assert any("isFraud" in error for error in result.errors)

    def test_validate_null_transaction_id(self, valid_transaction_df):
        """Test validation fails for null TransactionIDs."""
        df = valid_transaction_df.copy()
        df.loc[0, "TransactionID"] = None

        result = validate_schema(df, table_name="transaction")

        assert not result.is_valid
        assert any("null" in error.lower() for error in result.errors)

    def test_validate_duplicate_transaction_id(self, valid_transaction_df):
        """Test validation fails for duplicate TransactionIDs."""
        df = valid_transaction_df.copy()
        df.loc[1, "TransactionID"] = 1  # Duplicate

        result = validate_schema(df, table_name="transaction")

        assert not result.is_valid
        assert any("duplicate" in error.lower() for error in result.errors)

    def test_validate_null_target(self, valid_transaction_df):
        """Test validation fails for null target values."""
        df = valid_transaction_df.copy()
        df.loc[0, "isFraud"] = None

        result = validate_schema(df, table_name="transaction")

        assert not result.is_valid
        assert any("isFraud" in error and "null" in error.lower() for error in result.errors)

    def test_validate_non_binary_target(self, valid_transaction_df):
        """Test validation fails for non-binary target values."""
        df = valid_transaction_df.copy()
        df.loc[0, "isFraud"] = 2  # Invalid value

        result = validate_schema(df, table_name="transaction")

        assert not result.is_valid
        assert any("non-binary" in error.lower() for error in result.errors)

    def test_validate_empty_dataframe(self):
        """Test validation fails for empty DataFrame."""
        df = pd.DataFrame()
        result = validate_schema(df, table_name="transaction")

        assert not result.is_valid
        assert any("empty" in error.lower() for error in result.errors)

    def test_validate_low_fraud_rate_warning(self, valid_transaction_df):
        """Test warning for very low fraud rate."""
        df = valid_transaction_df.copy()
        # Add many legitimate transactions
        legitimate = pd.DataFrame(
            {
                "TransactionID": range(6, 10006),
                "isFraud": [0] * 10000,
                "TransactionDT": range(600, 10600),
                "TransactionAmt": [10.0] * 10000,
            }
        )
        df = pd.concat([df, legitimate], ignore_index=True)

        result = validate_schema(df, table_name="transaction")

        assert result.is_valid  # Still valid
        assert any("low fraud rate" in warning.lower() for warning in result.warnings)

    def test_validate_high_fraud_rate_warning(self, valid_transaction_df):
        """Test warning for unusually high fraud rate."""
        df = valid_transaction_df.copy()
        df["isFraud"] = 1  # All fraud

        result = validate_schema(df, table_name="transaction")

        assert result.is_valid  # Still valid
        assert any("high fraud rate" in warning.lower() for warning in result.warnings)

    def test_validate_extra_columns(self, valid_transaction_df):
        """Test extra columns are identified."""
        df = valid_transaction_df.copy()
        df["extra_col"] = 1

        result = validate_schema(df, table_name="transaction")

        assert result.is_valid
        assert "extra_col" in result.extra_columns

    def test_validate_merged_table(self, valid_transaction_df, valid_identity_df):
        """Test validation for merged table."""
        merged_df = valid_transaction_df.merge(valid_identity_df, on="TransactionID", how="left")

        result = validate_schema(merged_df, table_name="merged")

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_with_custom_schema(self, valid_transaction_df):
        """Test validation with custom schema."""
        custom_schema = IEEECISSchema()
        result = validate_schema(
            valid_transaction_df, table_name="transaction", schema=custom_schema
        )

        assert result.is_valid
