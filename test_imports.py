#!/usr/bin/env python3
"""
Quick import test to verify all modules load correctly.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("Testing ML Training Pipeline Imports...")

try:
    print("1. Testing base imports...")
    from ml.training.base import BaseTrainer, TrainingConfig, TrainingResult
    print("   ✓ Base classes imported successfully")
    
    print("2. Testing tracking imports...")
    from ml.training.tracking import ExperimentTracker, LocalTracker, create_tracker
    print("   ✓ Tracking classes imported successfully")
    
    print("3. Testing trainer imports...")
    from ml.training.trainers import XGBoostTrainer, XGBoostConfig
    print("   ✓ XGBoost trainer imported successfully")
    
    from ml.training.trainers import IsolationForestTrainer, IsolationForestConfig
    print("   ✓ Isolation Forest trainer imported successfully")
    
    print("4. Testing pipeline imports...")
    from ml.training.pipeline import TrainingPipeline, PipelineConfig
    print("   ✓ Pipeline classes imported successfully")
    
    print("5. Testing evaluation imports...")
    from ml.training.evaluation import ModelEvaluator
    print("   ✓ Evaluation classes imported successfully")
    
    print("6. Testing registry imports...")
    from ml.training.registry import ModelRegistry
    print("   ✓ Registry classes imported successfully")
    
    print("7. Testing optimization imports...")
    from ml.training.optimization import ThresholdOptimizer
    print("   ✓ Optimization classes imported successfully")
    
    print("\n🎉 All imports successful! ML Phase 2 is ready for validation.")
    
except Exception as e:
    print(f"\n❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)