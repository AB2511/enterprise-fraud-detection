#!/usr/bin/env python3
"""
Test Runner for ML Training Pipeline

Comprehensive test suite for the ML Phase 2 training pipeline.
Runs unit tests, integration tests, and validates the complete training workflow.
"""

import sys
import pytest
import subprocess
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any
import tempfile
import shutil
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.training.pipeline import TrainingPipeline, PipelineConfig
from ml.training.trainers import XGBoostConfig, IsolationForestConfig
from ml.training.tracking import LocalTracker
from ml.training.registry import ModelRegistry
from ml.utils.logging_config import setup_logging


def create_sample_dataset(n_samples: int = 1000, output_path: Path = None) -> pd.DataFrame:
    """Create sample fraud detection dataset for testing."""
    
    np.random.seed(42)
    
    # Generate realistic features
    data = {
        'transaction_id': [f'txn_{i:06d}' for i in range(n_samples)],
        'amount': np.random.exponential(100, n_samples),
        'hour': np.random.randint(0, 24, n_samples),
        'day_of_week': np.random.randint(0, 7, n_samples),
        'merchant_category': np.random.choice(['grocery', 'gas', 'restaurant', 'online'], n_samples),
        'customer_age': np.random.randint(18, 80, n_samples),
        'account_age_days': np.random.exponential(365, n_samples),
        'transaction_count_24h': np.random.poisson(3, n_samples),
        'amount_mean_7d': np.random.exponential(75, n_samples),
        'amount_std_7d': np.random.exponential(25, n_samples),
        'is_weekend': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
        'velocity_1h': np.random.exponential(1.5, n_samples),
        'distance_from_home': np.random.exponential(5, n_samples),
        'device_risk_score': np.random.beta(2, 5, n_samples),
        'ip_risk_score': np.random.beta(2, 5, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Create realistic fraud labels (about 5% fraud rate)
    fraud_probability = (
        0.01 +  # Base rate
        0.15 * (df['amount'] > df['amount'].quantile(0.95)) +  # High amounts
        0.08 * (df['hour'].isin([2, 3, 4, 23])) +  # Unusual hours
        0.05 * (df['velocity_1h'] > 3) +  # High velocity
        0.04 * (df['distance_from_home'] > 20) +  # Far from home
        0.06 * (df['device_risk_score'] > 0.8) +  # High device risk
        0.06 * (df['ip_risk_score'] > 0.8)  # High IP risk
    )
    
    df['is_fraud'] = np.random.binomial(1, fraud_probability.clip(0, 0.3), n_samples)
    
    # Add some categorical encoding
    category_map = {'grocery': 0, 'gas': 1, 'restaurant': 2, 'online': 3}
    df['merchant_category_encoded'] = df['merchant_category'].map(category_map)
    
    if output_path:
        df.to_csv(output_path, index=False)
        print(f"Sample dataset saved to: {output_path}")
    
    print(f"Dataset created: {len(df)} samples, {df['is_fraud'].sum()} fraud cases ({df['is_fraud'].mean():.1%} fraud rate)")
    
    return df


def run_unit_tests() -> Dict[str, Any]:
    """Run unit tests for training components."""
    
    print("\n" + "="*60)
    print("RUNNING UNIT TESTS")
    print("="*60)
    
    # Run pytest with coverage
    test_args = [
        "tests/ml/training/",
        "-v",
        "--tb=short",
        "--cov=ml.training",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-fail-under=85"
    ]
    
    try:
        result = pytest.main(test_args)
        success = result == 0
    except Exception as e:
        print(f"Error running unit tests: {e}")
        success = False
    
    return {
        "success": success,
        "test_type": "unit_tests",
        "coverage_report": "htmlcov/index.html" if success else None
    }


def run_integration_test() -> Dict[str, Any]:
    """Run integration test with real training pipeline."""
    
    print("\n" + "="*60)
    print("RUNNING INTEGRATION TEST")
    print("="*60)
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create test dataset
        print("Creating test dataset...")
        dataset_path = temp_dir / "test_fraud_data.csv"
        test_data = create_sample_dataset(n_samples=500, output_path=dataset_path)
        
        # Create pipeline configuration
        print("Configuring training pipeline...")
        config = PipelineConfig(
            pipeline_name="integration_test",
            dataset_path=dataset_path,
            experiment_tracker_type="local",
            registry_path=temp_dir / "registry",
            artifacts_base_dir=temp_dir / "artifacts",
            generate_evaluation_reports=True,
            optimize_thresholds=True,
            random_seed=42,
            trainer_configs=[
                XGBoostConfig(
                    model_name="xgboost_integration_test",
                    n_estimators=20,  # Small for fast testing
                    max_depth=3,
                    use_cross_validation=True,
                    cv_folds=3
                ),
                IsolationForestConfig(
                    model_name="isolation_forest_integration_test",
                    n_estimators=30,  # Small for fast testing
                    use_cross_validation=True,
                    cv_folds=3
                )
            ]
        )
        
        # Run training pipeline
        print("Running training pipeline...")
        pipeline = TrainingPipeline(config)
        results = pipeline.run()
        
        # Validate results
        print("Validating results...")
        assert len(results) == 2, f"Expected 2 models, got {len(results)}"
        
        # Check XGBoost results
        xgb_result = results["xgboost_integration_test_0"]
        assert xgb_result.model is not None, "XGBoost model not trained"
        assert xgb_result.training_time > 0, "Invalid training time"
        assert "roc_auc" in xgb_result.test_metrics, "Missing ROC-AUC metric"
        assert 0.5 <= xgb_result.test_metrics["roc_auc"] <= 1.0, "Invalid ROC-AUC value"
        
        # Check Isolation Forest results
        if_result = results["isolation_forest_integration_test_1"]
        assert if_result.model is not None, "Isolation Forest model not trained"
        assert if_result.training_time > 0, "Invalid training time"
        assert "roc_auc" in if_result.test_metrics, "Missing ROC-AUC metric"
        
        # Check artifacts were created
        artifacts_dir = config.artifacts_base_dir
        assert artifacts_dir.exists(), "Artifacts directory not created"
        
        # Check registry
        registry_dir = config.registry_path
        assert registry_dir.exists(), "Registry directory not created"
        assert (registry_dir / "models.json").exists(), "Models registry not created"
        
        # Check evaluation reports
        model_dirs = list(artifacts_dir.glob("*"))
        assert len(model_dirs) >= 2, "Model artifact directories not created"
        
        for model_dir in model_dirs:
            evaluation_dir = model_dir / "evaluation"
            if evaluation_dir.exists():
                assert (evaluation_dir / "evaluation_metrics.json").exists(), "Evaluation metrics not saved"
        
        print("✓ Integration test passed successfully!")
        
        return {
            "success": True,
            "test_type": "integration_test",
            "models_trained": len(results),
            "xgb_roc_auc": xgb_result.test_metrics.get("roc_auc"),
            "if_roc_auc": if_result.test_metrics.get("roc_auc"),
            "artifacts_path": str(artifacts_dir),
            "registry_path": str(registry_dir)
        }
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "test_type": "integration_test",
            "error": str(e)
        }
        
    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_cli_test() -> Dict[str, Any]:
    """Test command-line interface."""
    
    print("\n" + "="*60)
    print("RUNNING CLI TEST")
    print("="*60)
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create test dataset
        dataset_path = temp_dir / "cli_test_data.csv"
        create_sample_dataset(n_samples=200, output_path=dataset_path)
        
        # Test CLI command
        cmd = [
            sys.executable, "scripts/train_models.py",
            "--data", str(dataset_path),
            "--models", "xgboost",
            "--quick",
            "--output-dir", str(temp_dir / "output"),
            "--tracker", "local",
            "--no-optimization"  # Skip for faster testing
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        success = result.returncode == 0
        
        if success:
            print("✓ CLI test passed successfully!")
            # Check output directory was created
            output_dir = temp_dir / "output"
            artifacts_created = output_dir.exists() and list(output_dir.glob("**/*"))
        else:
            print("✗ CLI test failed")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            artifacts_created = False
        
        return {
            "success": success,
            "test_type": "cli_test",
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "artifacts_created": artifacts_created
        }
        
    except subprocess.TimeoutExpired:
        print("✗ CLI test timed out")
        return {
            "success": False,
            "test_type": "cli_test",
            "error": "Test timed out"
        }
        
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
        return {
            "success": False,
            "test_type": "cli_test",
            "error": str(e)
        }
        
    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def run_performance_test() -> Dict[str, Any]:
    """Test training performance and resource usage."""
    
    print("\n" + "="*60)
    print("RUNNING PERFORMANCE TEST")
    print("="*60)
    
    import time
    import psutil
    
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create larger dataset for performance testing
        print("Creating performance test dataset...")
        dataset_path = temp_dir / "performance_test_data.csv"
        test_data = create_sample_dataset(n_samples=2000, output_path=dataset_path)
        
        # Monitor system resources
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_time = time.time()
        
        # Configure quick training
        config = PipelineConfig(
            pipeline_name="performance_test",
            dataset_path=dataset_path,
            experiment_tracker_type="local",
            registry_path=temp_dir / "registry",
            artifacts_base_dir=temp_dir / "artifacts",
            generate_evaluation_reports=False,  # Skip for speed
            optimize_thresholds=False,  # Skip for speed
            trainer_configs=[
                XGBoostConfig(
                    model_name="xgboost_perf_test",
                    n_estimators=50,
                    max_depth=4,
                    use_cross_validation=False  # Skip CV for speed
                )
            ]
        )
        
        # Run training
        print("Running performance test...")
        pipeline = TrainingPipeline(config)
        results = pipeline.run()
        
        # Calculate metrics
        end_time = time.time()
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        training_time = end_time - start_time
        memory_usage = end_memory - start_memory
        peak_memory = max(start_memory, end_memory)
        
        # Performance thresholds
        max_training_time = 60  # seconds
        max_memory_usage = 500  # MB
        
        performance_ok = (
            training_time <= max_training_time and
            peak_memory <= max_memory_usage
        )
        
        if performance_ok:
            print(f"✓ Performance test passed!")
        else:
            print(f"✗ Performance test failed (time: {training_time:.1f}s, memory: {peak_memory:.1f}MB)")
        
        print(f"Training time: {training_time:.1f}s")
        print(f"Memory usage: {memory_usage:.1f}MB (peak: {peak_memory:.1f}MB)")
        
        return {
            "success": performance_ok,
            "test_type": "performance_test",
            "training_time_seconds": training_time,
            "memory_usage_mb": memory_usage,
            "peak_memory_mb": peak_memory,
            "dataset_size": len(test_data),
            "models_trained": len(results)
        }
        
    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        return {
            "success": False,
            "test_type": "performance_test",
            "error": str(e)
        }
        
    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def generate_test_report(test_results: list) -> None:
    """Generate comprehensive test report."""
    
    print("\n" + "="*60)
    print("TEST REPORT")
    print("="*60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results if result["success"])
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    print("\nDetailed Results:")
    print("-" * 40)
    
    for result in test_results:
        status = "✓ PASS" if result["success"] else "✗ FAIL"
        test_type = result["test_type"].replace("_", " ").title()
        print(f"{status} - {test_type}")
        
        if not result["success"] and "error" in result:
            print(f"    Error: {result['error']}")
        
        # Show specific metrics
        if result["test_type"] == "integration_test" and result["success"]:
            print(f"    Models trained: {result.get('models_trained', 'N/A')}")
            print(f"    XGBoost ROC-AUC: {result.get('xgb_roc_auc', 'N/A'):.3f}")
            print(f"    Isolation Forest ROC-AUC: {result.get('if_roc_auc', 'N/A'):.3f}")
            
        elif result["test_type"] == "performance_test" and result["success"]:
            print(f"    Training time: {result.get('training_time_seconds', 'N/A'):.1f}s")
            print(f"    Peak memory: {result.get('peak_memory_mb', 'N/A'):.1f}MB")
    
    # Save report to file
    report_path = Path("test_report.json")
    with open(report_path, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)
    
    print(f"\nDetailed report saved to: {report_path}")
    
    # Overall result
    if failed_tests == 0:
        print("\n🎉 All tests passed! ML Phase 2 training pipeline is ready for production.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review and fix issues before production deployment.")


def main():
    """Main test runner."""
    
    print("ML Phase 2 Training Pipeline - Test Suite")
    print("=" * 60)
    
    # Setup logging
    setup_logging(level="INFO")
    
    # Run all tests
    test_results = []
    
    try:
        # 1. Unit Tests
        unit_result = run_unit_tests()
        test_results.append(unit_result)
        
        # 2. Integration Test
        integration_result = run_integration_test()
        test_results.append(integration_result)
        
        # 3. CLI Test
        cli_result = run_cli_test()
        test_results.append(cli_result)
        
        # 4. Performance Test
        performance_result = run_performance_test()
        test_results.append(performance_result)
        
        # Generate report
        generate_test_report(test_results)
        
        # Exit with appropriate code
        all_passed = all(result["success"] for result in test_results)
        sys.exit(0 if all_passed else 1)
        
    except KeyboardInterrupt:
        print("\n\nTest run interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n\nTest runner failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()