#!/usr/bin/env python3
"""
Training Script for Fraud Detection Models

Command-line interface for running the ML training pipeline.
Supports various configurations and training scenarios.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
import yaml

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.training.pipeline import TrainingPipeline, ExperimentRunner, PipelineConfig
from ml.training.base import TrainingConfig
from ml.training.trainers import XGBoostConfig, IsolationForestConfig
from ml.training.tracking import create_tracker
from ml.utils.logging_config import setup_logging


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Train fraud detection models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with default configuration
  python scripts/train_models.py
  
  # Train with custom pipeline config
  python scripts/train_models.py --config config/training/pipeline_config.yaml
  
  # Train specific model types only
  python scripts/train_models.py --models xgboost isolation_forest
  
  # Train with custom data file
  python scripts/train_models.py --data data/my_dataset.csv
  
  # Run experiment with MLflow tracking
  python scripts/train_models.py --tracker mlflow --experiment-name my_experiment
  
  # Quick training (reduced parameters for testing)
  python scripts/train_models.py --quick
        """
    )
    
    # Configuration
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="Path to pipeline configuration YAML file"
    )
    
    # Data source
    parser.add_argument(
        "--data", "-d",
        type=Path,
        help="Path to training dataset (CSV, Parquet, or JSON)"
    )
    
    # Model selection
    parser.add_argument(
        "--models", "-m",
        nargs="+",
        choices=["xgboost", "isolation_forest", "all"],
        default=["all"],
        help="Model types to train"
    )
    
    # Experiment tracking
    parser.add_argument(
        "--tracker", "-t",
        choices=["auto", "local", "mlflow"],
        default="auto",
        help="Experiment tracker type"
    )
    
    parser.add_argument(
        "--experiment-name", "-e",
        type=str,
        default="fraud_detection_training",
        help="Experiment name for tracking"
    )
    
    parser.add_argument(
        "--tracking-uri",
        type=str,
        help="MLflow tracking server URI"
    )
    
    # Output configuration
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path("training_output"),
        help="Output directory for artifacts"
    )
    
    parser.add_argument(
        "--no-evaluation",
        action="store_true",
        help="Skip evaluation report generation"
    )
    
    parser.add_argument(
        "--no-optimization",
        action="store_true", 
        help="Skip threshold optimization"
    )
    
    # Training parameters
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick training with reduced parameters (for testing)"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of data to use for testing"
    )
    
    parser.add_argument(
        "--cv-folds",
        type=int,
        default=5,
        help="Number of cross-validation folds"
    )
    
    # Logging
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser


def create_trainer_configs(
    models: List[str], 
    quick: bool = False, 
    **kwargs
) -> List[TrainingConfig]:
    """Create trainer configurations based on model selection."""
    configs = []
    
    if "all" in models:
        models = ["xgboost", "isolation_forest"]
    
    # Common configuration
    common_config = {
        "test_size": kwargs.get("test_size", 0.2),
        "validation_size": 0.15,
        "random_seed": kwargs.get("seed", 42),
        "use_cross_validation": not quick,
        "cv_folds": kwargs.get("cv_folds", 5) if not quick else 3,
        "save_model": True,
        "save_predictions": True,
        "save_feature_importance": True,
        "save_plots": True
    }
    
    if "xgboost" in models:
        xgb_config = XGBoostConfig(
            model_name="xgboost_fraud_detector",
            model_version="1.0.0",
            n_estimators=10 if quick else 100,
            max_depth=3 if quick else 6,
            learning_rate=0.1,
            early_stopping=not quick,
            early_stopping_rounds=5 if quick else 10,
            **common_config
        )
        configs.append(xgb_config)
    
    if "isolation_forest" in models:
        if_config = IsolationForestConfig(
            model_name="isolation_forest_anomaly_detector", 
            model_version="1.0.0",
            n_estimators=50 if quick else 100,
            contamination="auto",
            **common_config
        )
        configs.append(if_config)
    
    return configs


def load_pipeline_config(config_path: Path) -> PipelineConfig:
    """Load pipeline configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        # Parse trainer configs
        trainer_configs = []
        if 'trainer_configs' in config_dict:
            for trainer_config in config_dict['trainer_configs']:
                model_name = trainer_config.get('model_name', '')
                if 'xgboost' in model_name.lower():
                    trainer_configs.append(XGBoostConfig.from_dict(trainer_config))
                elif 'isolation' in model_name.lower():
                    trainer_configs.append(IsolationForestConfig.from_dict(trainer_config))
                else:
                    # Default to TrainingConfig
                    trainer_configs.append(TrainingConfig.from_dict(trainer_config))
        
        config_dict['trainer_configs'] = trainer_configs
        
        return PipelineConfig(**config_dict)
        
    except Exception as e:
        logging.error(f"Failed to load configuration from {config_path}: {e}")
        sys.exit(1)


def create_default_pipeline_config(args) -> PipelineConfig:
    """Create default pipeline configuration from arguments."""
    
    # Create trainer configs
    trainer_configs = create_trainer_configs(
        args.models,
        quick=args.quick,
        seed=args.seed,
        test_size=args.test_size,
        cv_folds=args.cv_folds
    )
    
    config = PipelineConfig(
        pipeline_name="fraud_detection_training",
        dataset_path=args.data,
        experiment_tracker_type=args.tracker,
        experiment_name=args.experiment_name,
        tracking_uri=args.tracking_uri,
        registry_path=args.output_dir / "models" / "registry",
        artifacts_base_dir=args.output_dir / "artifacts",
        evaluation_output_dir=args.output_dir / "evaluation",
        generate_evaluation_reports=not args.no_evaluation,
        optimize_thresholds=not args.no_optimization,
        random_seed=args.seed,
        trainer_configs=trainer_configs
    )
    
    return config


def validate_inputs(args) -> None:
    """Validate command line arguments."""
    # Check data file exists
    if args.data and not args.data.exists():
        logging.error(f"Data file not found: {args.data}")
        sys.exit(1)
    
    # Check config file exists
    if args.config and not args.config.exists():
        logging.error(f"Configuration file not found: {args.config}")
        sys.exit(1)
    
    # Validate test size
    if not 0 < args.test_size < 1:
        logging.error(f"Test size must be between 0 and 1, got: {args.test_size}")
        sys.exit(1)
    
    # Validate CV folds
    if args.cv_folds < 2:
        logging.error(f"CV folds must be at least 2, got: {args.cv_folds}")
        sys.exit(1)


def print_summary(config: PipelineConfig, results: Dict[str, Any]) -> None:
    """Print training summary."""
    print("\n" + "="*60)
    print("TRAINING COMPLETED")
    print("="*60)
    
    print(f"Pipeline: {config.pipeline_name}")
    print(f"Experiment: {config.experiment_name}")
    print(f"Models trained: {len(results)}")
    print(f"Output directory: {config.artifacts_base_dir}")
    
    if results:
        print("\nModel Performance:")
        print("-" * 40)
        
        for model_name, result in results.items():
            print(f"\n{model_name}:")
            print(f"  Training time: {result.training_time:.1f}s")
            
            if result.test_metrics:
                test_metrics = result.test_metrics
                print(f"  Test Accuracy: {test_metrics.get('accuracy', 'N/A'):.3f}")
                print(f"  Test ROC-AUC: {test_metrics.get('roc_auc', 'N/A'):.3f}")
                print(f"  Test Precision: {test_metrics.get('precision', 'N/A'):.3f}")
                print(f"  Test Recall: {test_metrics.get('recall', 'N/A'):.3f}")
                print(f"  Test F1-Score: {test_metrics.get('f1_score', 'N/A'):.3f}")
    
    print(f"\nArtifacts saved to: {config.artifacts_base_dir}")
    print(f"Registry path: {config.registry_path}")
    print("\n" + "="*60)


def main():
    """Main training script entry point."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else getattr(logging, args.log_level)
    setup_logging(level=log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting fraud detection model training")
    
    try:
        # Validate inputs
        validate_inputs(args)
        
        # Load or create configuration
        if args.config:
            logger.info(f"Loading configuration from: {args.config}")
            config = load_pipeline_config(args.config)
            
            # Override with command line arguments
            if args.data:
                config.dataset_path = args.data
            if args.tracker != "auto":
                config.experiment_tracker_type = args.tracker
            if args.experiment_name != "fraud_detection_training":
                config.experiment_name = args.experiment_name
            if args.tracking_uri:
                config.tracking_uri = args.tracking_uri
                
        else:
            logger.info("Creating default configuration")
            config = create_default_pipeline_config(args)
        
        # Create output directories
        config.artifacts_base_dir.mkdir(parents=True, exist_ok=True)
        config.registry_path.mkdir(parents=True, exist_ok=True)
        
        # Log configuration
        logger.info(f"Pipeline: {config.pipeline_name}")
        logger.info(f"Models: {[tc.model_name for tc in config.trainer_configs]}")
        logger.info(f"Output directory: {config.artifacts_base_dir}")
        logger.info(f"Experiment tracker: {config.experiment_tracker_type}")
        
        # Create and run pipeline
        logger.info("Initializing training pipeline")
        pipeline = TrainingPipeline(config)
        
        logger.info("Starting model training")
        results = pipeline.run()
        
        # Print summary
        print_summary(config, results)
        
        logger.info("Training completed successfully")
        
    except KeyboardInterrupt:
        logger.warning("Training interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()