"""
Tests for experiment tracking functionality.
"""

import pytest
import pandas as pd
from datetime import datetime
from pathlib import Path
import json
import tempfile
import shutil

from ml.training.tracking import (
    ExperimentRun, ExperimentTracker, LocalTracker, create_tracker
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture 
def local_tracker(temp_dir):
    """Create LocalTracker instance for tests."""
    tracker_dir = temp_dir / "test_tracking"
    return LocalTracker("test_experiment", tracker_dir)


class TestExperimentRun:
    """Test ExperimentRun data class."""
    
    def test_experiment_run_creation(self):
        """Test basic ExperimentRun creation."""
        run = ExperimentRun(
            run_id="test-run-123",
            experiment_id="test-exp-456"
        )
        
        assert run.run_id == "test-run-123"
        assert run.experiment_id == "test-exp-456"
        assert run.status == "RUNNING"
        assert isinstance(run.start_time, datetime)
        assert run.metrics == {}
        assert run.params == {}
        assert run.tags == {}
        assert run.artifacts == []


class TestLocalTracker:
    """Test LocalTracker implementation."""
    
    def test_local_tracker_initialization(self, temp_dir):
        """Test LocalTracker initialization."""
        tracker_dir = temp_dir / "tracking"
        tracker = LocalTracker("test_experiment", tracker_dir)
        
        assert tracker.experiment_name == "test_experiment"
        assert tracker.tracking_dir == tracker_dir
        assert tracker_dir.exists()
        assert (tracker_dir / "runs").exists()
        assert (tracker_dir / "experiments.json").exists()
        
        # Check experiment was created
        assert tracker.experiment_id is not None
        assert tracker.experiment_id in tracker._experiments
        
    def test_create_experiment(self, local_tracker):
        """Test experiment creation."""
        exp_id = local_tracker.create_experiment("new_experiment")
        
        assert exp_id is not None
        assert exp_id in local_tracker._experiments
        assert local_tracker._experiments[exp_id]["name"] == "new_experiment"
        assert "creation_time" in local_tracker._experiments[exp_id]
        
    def test_start_end_run(self, local_tracker):
        """Test run lifecycle."""
        run_id = local_tracker.start_run("test_run")
        
        assert run_id is not None
        
        # Check run exists
        run = local_tracker.get_run(run_id)
        assert run is not None
        assert run.run_name == "test_run"
        assert run.status == "RUNNING"
        
        # End run
        local_tracker.end_run(run_id, "FINISHED")
        
        # Check run is finished
        run = local_tracker.get_run(run_id)
        assert run.status == "FINISHED"
        assert run.end_time is not None
        
    def test_log_params(self, local_tracker):
        """Test parameter logging."""
        run_id = local_tracker.start_run()
        
        # Log single param
        local_tracker.log_param(run_id, "learning_rate", 0.01)
        
        run = local_tracker.get_run(run_id)
        assert run.params["learning_rate"] == 0.01
        
        # Log multiple params
        params = {"n_estimators": 100, "max_depth": 6}
        local_tracker.log_params(run_id, params)
        
        run = local_tracker.get_run(run_id)
        assert run.params["n_estimators"] == 100
        assert run.params["max_depth"] == 6
        assert run.params["learning_rate"] == 0.01  # Previous param still there
        
    def test_log_metrics(self, local_tracker):
        """Test metric logging."""
        run_id = local_tracker.start_run()
        
        # Log single metric
        local_tracker.log_metric(run_id, "accuracy", 0.95)
        
        run = local_tracker.get_run(run_id)
        assert run.metrics["accuracy"] == 0.95
        
        # Log multiple metrics
        metrics = {"precision": 0.90, "recall": 0.85}
        local_tracker.log_metrics(run_id, metrics)
        
        run = local_tracker.get_run(run_id)
        assert run.metrics["precision"] == 0.90
        assert run.metrics["recall"] == 0.85
        assert run.metrics["accuracy"] == 0.95  # Previous metric still there
        
    def test_log_artifact(self, local_tracker, temp_dir):
        """Test artifact logging."""
        run_id = local_tracker.start_run()
        
        # Create test file
        test_file = temp_dir / "test_artifact.txt"
        test_file.write_text("This is a test artifact")
        
        # Log artifact
        local_tracker.log_artifact(run_id, test_file, "model.txt")
        
        run = local_tracker.get_run(run_id)
        assert "model.txt" in run.artifacts
        
        # Check artifact was copied
        artifacts_dir = local_tracker.runs_dir / run_id / "artifacts"
        assert (artifacts_dir / "model.txt").exists()
        
    def test_set_tags(self, local_tracker):
        """Test tag setting."""
        run_id = local_tracker.start_run()
        
        # Set single tag
        local_tracker.set_tag(run_id, "model_type", "xgboost")
        
        run = local_tracker.get_run(run_id)
        assert run.tags["model_type"] == "xgboost"
        
        # Set multiple tags
        tags = {"version": "1.0", "dataset": "fraud_v1"}
        local_tracker.set_tags(run_id, tags)
        
        run = local_tracker.get_run(run_id)
        assert run.tags["version"] == "1.0"
        assert run.tags["dataset"] == "fraud_v1"
        assert run.tags["model_type"] == "xgboost"  # Previous tag still there
        
    def test_list_runs(self, local_tracker):
        """Test listing runs."""
        # Create multiple runs
        run_ids = []
        for i in range(3):
            run_id = local_tracker.start_run(f"run_{i}")
            local_tracker.log_metric(run_id, "score", i * 0.1)
            local_tracker.end_run(run_id)
            run_ids.append(run_id)
        
        # List runs
        runs = local_tracker.list_runs()
        
        assert len(runs) == 3
        # Should be sorted by start_time (newest first)
        assert runs[0].run_name == "run_2"
        assert runs[1].run_name == "run_1" 
        assert runs[2].run_name == "run_0"
        
    def test_persistence(self, temp_dir):
        """Test that data persists across tracker instances."""
        tracker_dir = temp_dir / "persistent_tracking"
        
        # Create first tracker and add data
        tracker1 = LocalTracker("persist_test", tracker_dir)
        run_id = tracker1.start_run("persistent_run")
        tracker1.log_params(run_id, {"param1": "value1"})
        tracker1.log_metrics(run_id, {"metric1": 0.95})
        tracker1.end_run(run_id)
        
        # Create second tracker with same directory
        tracker2 = LocalTracker("persist_test", tracker_dir)
        
        # Should be able to retrieve the run
        run = tracker2.get_run(run_id)
        assert run is not None
        assert run.run_name == "persistent_run"
        assert run.params["param1"] == "value1"
        assert run.metrics["metric1"] == 0.95


class TestCreateTracker:
    """Test tracker factory function."""
    
    def test_create_local_tracker(self, temp_dir):
        """Test creating local tracker."""
        tracker = create_tracker(
            "test_experiment", 
            tracker_type="local",
            tracking_dir=temp_dir / "tracking"
        )
        
        assert isinstance(tracker, LocalTracker)
        assert tracker.experiment_name == "test_experiment"
        
    def test_create_auto_tracker_without_mlflow(self, temp_dir, monkeypatch):
        """Test auto tracker fallback to local when MLflow unavailable."""
        # Mock MLflow import to fail - use a safer approach
        import sys
        original_import = __builtins__['__import__']
        
        def mock_import(name, *args, **kwargs):
            if name == "mlflow":
                raise ImportError("No module named 'mlflow'")
            # Use original import to avoid recursion
            return original_import(name, *args, **kwargs)
        
        monkeypatch.setattr("builtins.__import__", mock_import)
        
        tracker = create_tracker(
            "test_experiment",
            tracker_type="auto",
            tracking_dir=temp_dir / "tracking"
        )
        
        assert isinstance(tracker, LocalTracker)
        
    def test_invalid_tracker_type(self):
        """Test error for invalid tracker type."""
        with pytest.raises(ValueError, match="Unknown tracker type"):
            create_tracker("test", tracker_type="invalid")


class TestMLflowTracker:
    """Test MLflowTracker implementation (if MLflow available)."""
    
    def test_mlflow_tracker_requires_mlflow(self):
        """Test that MLflowTracker requires MLflow."""
        # This test checks that MLflowTracker properly handles MLflow import
        from ml.training.tracking import MLflowTracker
        
        try:
            tracker = MLflowTracker("test_experiment")
            # If we get here, MLflow is available
            assert hasattr(tracker, 'mlflow')
        except ImportError as e:
            # MLflow not available, which is expected in test environment
            assert "MLflow is required" in str(e)