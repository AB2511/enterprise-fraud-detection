# Enterprise Fraud Detection Platform
## Complete Repository Structure

```
enterprise-fraud-detection/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                           # Lint, test, security scan
│       ├── deploy-staging.yml               # Auto-deploy to staging
│       └── deploy-production.yml            # Manual deploy to production
│
├── backend/                                 # Python backend application
│   ├── src/
│   │   ├── domain/                          # Pure business logic (no dependencies)
│   │   │   ├── entities/                    # Core business objects
│   │   │   │   ├── __init__.py
│   │   │   │   ├── transaction.py           # Transaction aggregate root
│   │   │   │   ├── prediction.py            # Prediction aggregate root
│   │   │   │   ├── model.py                 # Model aggregate root
│   │   │   │   ├── drift_report.py          # DriftReport aggregate root
│   │   │   │   └── user.py                  # User entity
│   │   │   ├── value_objects/               # Immutable value objects
│   │   │   │   ├── __init__.py
│   │   │   │   ├── explanation.py           # SHAP explanation
│   │   │   │   ├── geolocation.py           # Lat/lon pair
│   │   │   │   ├── analyst_feedback.py      # Feedback value object
│   │   │   │   └── model_metadata.py        # Model training metadata
│   │   │   ├── enums/                       # Domain enumerations
│   │   │   │   ├── __init__.py
│   │   │   │   ├── transaction_type.py      # purchase, withdrawal, etc.
│   │   │   │   ├── prediction_class.py      # fraud, legitimate
│   │   │   │   ├── model_status.py          # training, staging, production
│   │   │   │   └── model_type.py            # xgboost, isolation_forest
│   │   │   ├── services/                    # Domain services
│   │   │   │   ├── __init__.py
│   │   │   │   ├── risk_scoring_service.py  # Convert probability to risk score
│   │   │   │   └── feature_engineering_service.py  # Feature transformations
│   │   │   └── exceptions/                  # Domain-specific exceptions
│   │   │       ├── __init__.py
│   │   │       ├── validation_error.py
│   │   │       └── business_rule_error.py
│   │   │
│   │   ├── application/                     # Application layer (use cases)
│   │   │   ├── __init__.py
│   │   │   ├── interfaces/                  # Ports (abstract interfaces)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── transaction_repository.py
│   │   │   │   ├── prediction_repository.py
│   │   │   │   ├── model_repository.py
│   │   │   │   ├── drift_repository.py
│   │   │   │   ├── feedback_repository.py
│   │   │   │   ├── ml_service.py            # ML inference interface
│   │   │   │   └── storage_service.py       # File storage interface
│   │   │   ├── use_cases/                   # Business workflows
│   │   │   │   ├── __init__.py
│   │   │   │   ├── predict_fraud.py         # Real-time prediction
│   │   │   │   ├── batch_predict.py         # Batch prediction
│   │   │   │   ├── submit_feedback.py       # Analyst feedback
│   │   │   │   ├── get_prediction_history.py
│   │   │   │   ├── train_model.py           # Model training orchestration
│   │   │   │   ├── deploy_model.py          # Model deployment
│   │   │   │   ├── detect_drift.py          # Drift detection
│   │   │   │   └── get_model_metrics.py
│   │   │   └── dto/                         # Data Transfer Objects
│   │   │       ├── __init__.py
│   │   │       ├── prediction_request.py
│   │   │       ├── prediction_response.py
│   │   │       ├── feedback_request.py
│   │   │       └── batch_request.py
│   │   │
│   │   ├── infrastructure/                  # External adapters (implementations)
│   │   │   ├── __init__.py
│   │   │   ├── database/                    # Database implementation
│   │   │   │   ├── __init__.py
│   │   │   │   ├── connection.py            # SQLAlchemy engine, session
│   │   │   │   ├── models.py                # SQLAlchemy ORM models
│   │   │   │   ├── repositories/            # Repository implementations
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── transaction_repository_impl.py
│   │   │   │   │   ├── prediction_repository_impl.py
│   │   │   │   │   ├── model_repository_impl.py
│   │   │   │   │   ├── drift_repository_impl.py
│   │   │   │   │   └── feedback_repository_impl.py
│   │   │   │   └── migrations/              # Alembic migrations
│   │   │   │       ├── env.py
│   │   │   │       ├── script.py.mako
│   │   │   │       └── versions/
│   │   │   │           └── 001_initial_schema.py
│   │   │   │
│   │   │   ├── ml/                          # ML implementation
│   │   │   │   ├── __init__.py
│   │   │   │   ├── model_loader.py          # Load models from S3
│   │   │   │   ├── inference_engine.py      # Run predictions
│   │   │   │   ├── explainer.py             # SHAP explanations
│   │   │   │   ├── feature_pipeline.py      # Feature engineering
│   │   │   │   ├── model_registry.py        # Model versioning
│   │   │   │   └── ensemble.py              # XGBoost + Isolation Forest
│   │   │   │
│   │   │   ├── storage/                     # S3 and file operations
│   │   │   │   ├── __init__.py
│   │   │   │   └── s3_client.py
│   │   │   │
│   │   │   ├── monitoring/                  # Observability
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cloudwatch_client.py     # CloudWatch metrics/logs
│   │   │   │   ├── logger.py                # Structured logging
│   │   │   │   └── tracer.py                # X-Ray distributed tracing
│   │   │   │
│   │   │   └── security/                    # Authentication & secrets
│   │   │       ├── __init__.py
│   │   │       ├── auth_service.py          # JWT validation
│   │   │       ├── rbac.py                  # Role-based access control
│   │   │       └── secrets_manager.py       # AWS Secrets Manager
│   │   │
│   │   ├── presentation/                    # API layer (FastAPI)
│   │   │   ├── __init__.py
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   └── v1/                      # API version 1
│   │   │   │       ├── __init__.py
│   │   │   │       ├── routes/              # API endpoints
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   ├── predictions.py   # /predict, /batch/predict
│   │   │   │       │   ├── feedback.py      # /feedback
│   │   │   │       │   ├── models.py        # /models, /models/{version}
│   │   │   │       │   ├── drift.py         # /drift/reports
│   │   │   │       │   └── health.py        # /health, /metrics
│   │   │   │       ├── schemas/             # Pydantic request/response models
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   ├── transaction_schema.py
│   │   │   │       │   ├── prediction_schema.py
│   │   │   │       │   ├── feedback_schema.py
│   │   │   │       │   ├── model_schema.py
│   │   │   │       │   └── error_schema.py
│   │   │   │       └── dependencies.py      # Dependency injection
│   │   │   │
│   │   │   ├── middleware/                  # Cross-cutting concerns
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth_middleware.py       # JWT validation
│   │   │   │   ├── logging_middleware.py    # Request/response logging
│   │   │   │   ├── error_handler.py         # Global exception handler
│   │   │   │   └── rate_limiter.py          # Rate limiting
│   │   │   │
│   │   │   └── main.py                      # FastAPI app initialization
│   │   │
│   │   ├── config/                          # Application configuration
│   │   │   ├── __init__.py
│   │   │   ├── settings.py                  # Pydantic settings (env vars)
│   │   │   └── logging_config.py            # Logging configuration
│   │   │
│   │   └── utils/                           # Shared utilities
│   │       ├── __init__.py
│   │       ├── validators.py                # Custom validators
│   │       ├── decorators.py                # Timing, caching decorators
│   │       └── constants.py                 # Application constants
│   │
│   ├── tests/                               # Comprehensive test suite
│   │   ├── __init__.py
│   │   ├── conftest.py                      # Pytest fixtures
│   │   ├── unit/                            # Unit tests (fast, isolated)
│   │   │   ├── domain/
│   │   │   │   ├── test_transaction.py
│   │   │   │   ├── test_prediction.py
│   │   │   │   └── test_risk_scoring.py
│   │   │   ├── application/
│   │   │   │   ├── test_predict_fraud.py
│   │   │   │   └── test_submit_feedback.py
│   │   │   └── infrastructure/
│   │   │       ├── test_feature_pipeline.py
│   │   │       └── test_explainer.py
│   │   ├── integration/                     # Integration tests (DB, S3)
│   │   │   ├── test_database.py
│   │   │   ├── test_ml_pipeline.py
│   │   │   ├── test_s3_storage.py
│   │   │   └── test_api_endpoints.py
│   │   └── e2e/                             # End-to-end tests
│   │       ├── test_prediction_flow.py
│   │       └── test_training_flow.py
│   │
│   ├── scripts/                             # Operational scripts
│   │   ├── train_model.py                   # Training job entry point
│   │   ├── detect_drift.py                  # Drift detection entry point
│   │   ├── generate_synthetic_data.py       # Generate test data
│   │   ├── seed_database.py                 # Populate DB with initial data
│   │   ├── deploy_model.py                  # Model deployment script
│   │   └── backup_database.py               # Database backup
│   │
│   ├── requirements.txt                     # Production dependencies
│   ├── requirements-dev.txt                 # Development dependencies
│   ├── Dockerfile                           # Production Docker image
│   ├── docker-compose.yml                   # Local development setup
│   ├── alembic.ini                          # Alembic configuration
│   ├── pytest.ini                           # Pytest configuration
│   ├── pyproject.toml                       # Ruff, mypy configuration
│   ├── .env.example                         # Environment variable template
│   └── README.md                            # Backend-specific documentation
│
├── ml/                                      # Machine learning experimentation
│   ├── notebooks/                           # Jupyter notebooks
│   │   ├── 01_data_exploration.ipynb
│   │   ├── 02_feature_engineering.ipynb
│   │   ├── 03_model_training.ipynb
│   │   ├── 04_model_evaluation.ipynb
│   │   └── 05_drift_analysis.ipynb
│   │
│   ├── training/                            # Training pipeline modules
│   │   ├── __init__.py
│   │   ├── trainer.py                       # Model training logic
│   │   ├── hyperparameter_tuning.py         # Optuna integration
│   │   ├── evaluation.py                    # Metrics computation
│   │   ├── data_preparation.py              # Data loading and splitting
│   │   └── cross_validation.py              # Time series CV
│   │
│   ├── drift/                               # Drift detection modules
│   │   ├── __init__.py
│   │   ├── drift_detector.py                # Main drift detection logic
│   │   ├── statistical_tests.py             # KS test, Chi-squared, PSI
│   │   └── performance_monitor.py           # Track model metrics over time
│   │
│   ├── config/                              # ML configuration
│   │   ├── model_config.yaml                # Model hyperparameters
│   │   ├── feature_config.yaml              # Feature definitions
│   │   └── training_config.yaml             # Training parameters
│   │
│   ├── data/                                # Local data (gitignored)
│   │   ├── raw/
│   │   ├── processed/
│   │   └── synthetic/
│   │
│   └── README.md                            # ML-specific documentation
│
├── frontend/                                # React dashboard (optional, Phase 7)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── PredictionTable.tsx
│   │   │   ├── ModelMetrics.tsx
│   │   │   └── DriftVisualization.tsx
│   │   ├── services/
│   │   │   └── api.ts                       # API client
│   │   ├── types/
│   │   │   └── index.ts                     # TypeScript types
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── README.md
│
├── monitoring/                              # Monitoring and dashboards
│   ├── dashboard/                           # Streamlit dashboard
│   │   ├── app.py                           # Main Streamlit app
│   │   ├── components/
│   │   │   ├── metrics_page.py              # Metrics visualization
│   │   │   ├── drift_page.py                # Drift analysis
│   │   │   └── model_performance_page.py    # Model performance
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   └── alerts/                              # Alert configuration
│       ├── alert_rules.yaml                 # CloudWatch alarm definitions
│       └── notification_config.yaml         # SNS topic configuration
│
├── infrastructure/                          # Infrastructure as Code
│   ├── terraform/                           # Terraform (future)
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── modules/
│   │   │   ├── networking/
│   │   │   ├── compute/
│   │   │   ├── database/
│   │   │   └── storage/
│   │   └── README.md
│   │
│   ├── docker/                              # Docker images
│   │   ├── api.Dockerfile                   # API service image
│   │   ├── training.Dockerfile              # Training job image
│   │   ├── monitoring.Dockerfile            # Monitoring dashboard image
│   │   └── drift.Dockerfile                 # Drift detection image
│   │
│   └── aws/                                 # AWS-specific configs
│       ├── ecs-task-definitions/
│       │   ├── api-service.json
│       │   ├── training-job.json
│       │   ├── drift-detection.json
│       │   └── monitoring-dashboard.json
│       ├── cloudwatch/
│       │   ├── log-groups.json
│       │   └── alarms.json
│       └── iam/
│           ├── ecs-task-role.json
│           ├── ecs-execution-role.json
│           └── policies/
│
├── docs/                                    # Documentation
│   ├── ARCHITECTURE.md                      # This architecture document
│   ├── API_DOCUMENTATION.md                 # API reference
│   ├── DEPLOYMENT_GUIDE.md                  # How to deploy
│   ├── DEVELOPMENT_SETUP.md                 # Local setup instructions
│   ├── MODEL_CARD.md                        # Model documentation
│   ├── RUNBOOK.md                           # Operational procedures
│   ├── CONTRIBUTING.md                      # Contribution guidelines
│   ├── SECURITY.md                          # Security policies
│   ├── diagrams/                            # Architecture diagrams
│   │   ├── system_context.png
│   │   ├── component_diagram.png
│   │   ├── data_flow.png
│   │   └── deployment.png
│   └── adr/                                 # Architecture Decision Records
│       ├── 001-use-clean-architecture.md
│       ├── 002-choose-xgboost.md
│       └── 003-use-shap.md
│
├── .gitignore                               # Git ignore patterns
├── .dockerignore                            # Docker ignore patterns
├── .pre-commit-config.yaml                  # Pre-commit hooks
├── README.md                                # Project overview
├── LICENSE                                  # License (MIT, Apache 2.0)
└── CHANGELOG.md                             # Version history
```

## Module Count Summary

- **Total Directories**: 87
- **Total Python Files**: ~150+ (including tests)
- **Configuration Files**: 25+
- **Documentation Files**: 15+

This structure represents a professional, production-ready repository that demonstrates enterprise software engineering practices.

