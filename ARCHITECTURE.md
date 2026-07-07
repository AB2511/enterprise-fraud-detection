# Enterprise AI Risk & Fraud Detection Platform
## Architecture Specification v1.0

**Document Status**: Architecture Design Phase  
**Last Updated**: July 7, 2026  
**Architecture Review**: Pending Implementation  
**Target Deployment**: AWS ECS with Multi-Region Support

---

## Executive Summary

This document defines the complete architecture for a production-grade, enterprise-scale fraud detection platform. The system is designed to process millions of transactions daily with sub-200ms inference latency, maintain 99.9% uptime, support real-time and batch prediction modes, and provide comprehensive explainability, monitoring, and automated model lifecycle management.

**Key Architectural Principles:**
- **Scalability**: Horizontal scaling via containerized microservices
- **Reliability**: Multi-AZ deployment, circuit breakers, graceful degradation
- **Maintainability**: Clean Architecture, dependency injection, modular design
- **Security**: Zero-trust architecture, secrets management, RBAC, audit logging
- **Observability**: Distributed tracing, structured logging, comprehensive metrics
- **Performance**: Caching strategies, async processing, database optimization

---

## Table of Contents

1. [System Context](#system-context)
2. [Business Requirements](#business-requirements)
3. [Technical Requirements](#technical-requirements)
4. [Architecture Overview](#architecture-overview)
5. [Domain Model](#domain-model)
6. [Component Architecture](#component-architecture)
7. [Data Architecture](#data-architecture)
8. [Machine Learning Architecture](#machine-learning-architecture)
9. [AWS Infrastructure Architecture](#aws-infrastructure-architecture)
10. [Security Architecture](#security-architecture)
11. [API Design](#api-design)
12. [Data Flow Diagrams](#data-flow-diagrams)
13. [Development Roadmap](#development-roadmap)
14. [Technology Justification](#technology-justification)
15. [Risk Analysis](#risk-analysis)
16. [Assumptions & Constraints](#assumptions-constraints)
17. [Open Questions](#open-questions)

---

## 1. System Context

### 1.1 Business Context

Financial institutions face evolving fraud threats that cost billions annually. Traditional rule-based systems generate excessive false positives (>90%) and fail to detect novel fraud patterns. This platform addresses these challenges through:

- **Adaptive ML Models**: Continuous learning from analyst feedback
- **Explainable Predictions**: SHAP values for regulatory compliance and analyst trust
- **Real-time Processing**: Sub-200ms prediction latency for transaction authorization
- **Automated Operations**: Self-healing model pipelines with drift detection and retraining
- **Audit Trail**: Complete decision provenance for compliance and investigation

### 1.2 User Personas

**Fraud Analyst**
- Reviews flagged transactions
- Investigates fraud patterns
- Provides feedback for model improvement
- Requires: Fast UI, explainability, investigation tools

**Data Scientist**
- Monitors model performance
- Analyzes drift and degradation
- Designs new features
- Requires: Model metrics, experiment tracking, feature analysis

**ML Engineer**
- Deploys and maintains models
- Manages retraining pipelines
- Handles infrastructure
- Requires: Model registry, deployment automation, observability

**Compliance Officer**
- Audits decisions
- Ensures regulatory compliance
- Reviews model fairness
- Requires: Audit logs, explainability reports, bias metrics

**System Administrator**
- Manages access control
- Monitors system health
- Handles incidents
- Requires: Dashboards, alerts, log aggregation


### 1.3 System Boundaries

**In Scope:**
- Real-time fraud prediction API
- Batch scoring pipeline
- Model training and retraining
- Feature engineering
- Explainability generation
- Drift detection and monitoring
- Analyst feedback loop
- Model registry and versioning
- REST APIs for all operations
- Role-based authentication and authorization
- Audit logging
- CloudWatch integration
- Docker containerization
- CI/CD pipeline

**Out of Scope (Future Phases):**
- Payment processing integration
- Mobile applications
- Graph-based fraud detection
- Multi-model ensembles beyond XGBoost + Isolation Forest
- Real-time feature computation from streaming data (Kafka/Kinesis)
- Custom AutoML framework
- Advanced A/B testing infrastructure
- Multi-tenancy

---

## 2. Business Requirements

### 2.1 Functional Requirements

**FR-1: Real-time Fraud Prediction**
- Accept transaction data via REST API
- Return fraud probability, risk score, and explanation within 200ms
- Support batch prediction for historical analysis

**FR-2: Model Explainability**
- Generate SHAP values for every prediction
- Provide top contributing features
- Store explanations for audit


**FR-3: Analyst Feedback**
- Analysts can confirm or dispute predictions
- Feedback stored and used for model retraining
- Investigation notes linked to transactions

**FR-4: Drift Detection**
- Monitor feature distributions daily
- Detect concept drift in model performance
- Trigger alerts when drift exceeds thresholds

**FR-5: Automated Retraining**
- Weekly retraining schedule
- Event-driven retraining on significant drift
- A/B testing before production promotion

**FR-6: Model Registry**
- Version all models with metadata
- Track experiment parameters
- Enable rollback to previous versions

**FR-7: Feature Store**
- Centralized feature definitions
- Consistent computation for training and inference
- Historical feature point-in-time queries

**FR-8: Authentication & Authorization**
- JWT-based authentication
- Role-based access control (Admin, Analyst, Data Scientist, Auditor)
- API key support for service-to-service calls

**FR-9: Audit Logging**
- Log all predictions with timestamps
- Track model changes
- Record analyst actions
- Immutable audit trail

**FR-10: Monitoring Dashboard**
- Real-time metrics (latency, throughput, error rate)
- Model performance trends
- Drift visualizations
- Alert status


### 2.2 Non-Functional Requirements

**NFR-1: Performance**
- Prediction latency: p95 < 200ms, p99 < 500ms
- Throughput: 10,000 requests/second per instance
- Batch scoring: 1M transactions/hour

**NFR-2: Availability**
- 99.9% uptime (8.76 hours downtime/year)
- Multi-AZ deployment
- Graceful degradation if secondary models unavailable

**NFR-3: Scalability**
- Horizontal scaling to 100+ instances
- Auto-scaling based on CPU and request queue depth
- Database connection pooling

**NFR-4: Security**
- Data encryption at rest and in transit
- No secrets in source code
- Secrets Manager for credentials
- VPC isolation
- HTTPS/TLS 1.3

**NFR-5: Maintainability**
- Clean Architecture (ports/adapters)
- 100% type hints
- Comprehensive docstrings
- Automated testing (unit, integration, e2e)
- Code coverage > 80%

**NFR-6: Observability**
- Structured JSON logging
- Distributed tracing (X-Ray)
- CloudWatch metrics and alarms
- Health check endpoints

**NFR-7: Compliance**
- GDPR-compliant data handling
- PCI-DSS considerations for transaction data
- SOC 2 audit trail requirements


---

## 3. Technical Requirements

### 3.1 Machine Learning Requirements

**Model Types:**
- Primary: XGBoost Classifier (supervised)
- Secondary: Isolation Forest (anomaly detection)
- Ensemble: Weighted combination based on validation performance

**Training Data:**
- Minimum 100,000 labeled transactions
- Class balance: Handle severe imbalance (fraud rate typically <1%)
- Temporal validation: Train on historical data, validate on future data

**Features:**
- Transaction amount and velocity features
- User behavior patterns
- Device and geolocation signals
- Temporal features (hour, day, month)
- Derived features (ratios, aggregations)
- Expected: 50-100 features after engineering

**Performance Metrics:**
- Primary: PR-AUC (Precision-Recall Area Under Curve)
- Secondary: F1 Score, Precision, Recall at operating threshold
- Business: False Positive Rate < 5%, True Positive Rate > 85%
- Calibration: Brier Score, reliability diagrams

**Explainability:**
- SHAP TreeExplainer for XGBoost
- Top 5 contributing features per prediction
- Global feature importance
- Explanation storage for audit

**Model Lifecycle:**
- Versioning: Semantic versioning (major.minor.patch)
- Registry: JSON metadata + pickled model artifacts
- Deployment: Blue-green strategy
- Rollback: One-command revert to previous version


### 3.2 Data Requirements

**Transaction Data Schema:**
```python
{
    "transaction_id": "uuid",
    "user_id": "string",
    "merchant_id": "string",
    "amount": "decimal",
    "currency": "string",
    "timestamp": "datetime",
    "device_id": "string",
    "ip_address": "string",
    "geolocation": {"lat": "float", "lon": "float"},
    "transaction_type": "enum",
    "merchant_category": "string",
    "card_type": "string"
}
```

**Prediction Output Schema:**
```python
{
    "prediction_id": "uuid",
    "transaction_id": "uuid",
    "fraud_probability": "float [0,1]",
    "risk_score": "int [0,100]",
    "predicted_class": "enum [fraud, legitimate]",
    "model_version": "string",
    "explanation": {
        "top_features": [{"feature": "string", "shap_value": "float"}],
        "base_value": "float"
    },
    "timestamp": "datetime",
    "latency_ms": "int"
}
```

**Data Storage:**
- Transactions: PostgreSQL (relational, ACID)
- Predictions: PostgreSQL (audit trail)
- Models: S3 (versioned artifacts)
- Features: S3 Parquet (training data)
- Logs: CloudWatch Logs
- Metrics: CloudWatch Metrics

**Data Retention:**
- Transactions: 7 years (regulatory)
- Predictions: 7 years
- Model artifacts: Indefinite
- Logs: 90 days (hot), 1 year (cold)


### 3.3 Infrastructure Requirements

**Compute:**
- API Service: AWS ECS Fargate (1-50 tasks, 2 vCPU, 4GB each)
- Training Jobs: AWS ECS Fargate (4 vCPU, 16GB, spot instances)
- Batch Scoring: AWS ECS Fargate (burst to 100 tasks)

**Storage:**
- Database: AWS RDS PostgreSQL 15 (Multi-AZ, 100GB, gp3)
- Object Storage: AWS S3 (versioned, encrypted)
- Caching: Redis (ElastiCache, optional future)

**Networking:**
- VPC with public and private subnets
- NAT Gateway for egress
- Application Load Balancer
- Security Groups with least privilege

**Secrets Management:**
- AWS Secrets Manager for database credentials
- AWS IAM roles for service-to-service auth
- Parameter Store for non-sensitive config

**Container Registry:**
- AWS ECR (private, scan on push)

**CI/CD:**
- GitHub Actions for build and test
- ECR for image storage
- ECS for deployment
- Rolling updates with health checks

---

## 4. Architecture Overview

### 4.1 Architectural Style

**Primary Pattern**: Clean Architecture (Hexagonal Architecture / Ports & Adapters)


**Layered Structure:**

```
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
│  (FastAPI Routes, Request/Response Models, Exception         │
│   Handlers, Middleware)                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Application Layer                         │
│  (Use Cases / Services: Prediction, Training, Monitoring)    │
│  - Orchestrates business logic                               │
│  - No framework dependencies                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                      Domain Layer                            │
│  (Entities, Value Objects, Domain Logic)                     │
│  - Pure Python                                               │
│  - No external dependencies                                  │
│  - Business rules and invariants                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                  Infrastructure Layer                        │
│  (Database, ML Models, External Services, S3, CloudWatch)    │
│  - Implements interfaces defined in upper layers             │
│  - Dependency Injection                                      │
└─────────────────────────────────────────────────────────────┘
```

**Rationale for Clean Architecture:**
- **Testability**: Business logic testable without databases or HTTP
- **Framework Independence**: Can swap FastAPI for Flask without touching core
- **Database Independence**: Repository pattern abstracts data access
- **Maintainability**: Changes localized to specific layers
- **Scalability**: Services can be extracted into microservices


### 4.2 Component Diagram (High-Level)

```
┌──────────────────────────────────────────────────────────────────┐
│                         External Clients                          │
│  (Mobile Apps, Payment Gateways, Analyst Dashboard)              │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                   AWS Application Load Balancer                 │
│              (SSL Termination, Health Checks)                   │
└────────────────────────────┬───────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
         ┌──────────▼──────────┐  ┌──▼──────────────────┐
         │   API Service        │  │  Monitoring Service │
         │   (FastAPI/ECS)      │  │  (Streamlit/ECS)    │
         │  - Predict           │  │  - Dashboards       │
         │  - Feedback          │  │  - Alerts           │
         │  - Batch             │  └─────────────────────┘
         └──────────┬───────────┘
                    │
        ┌───────────┼──────────────┬─────────────┐
        │           │              │             │
┌───────▼──────┐ ┌──▼───────┐ ┌───▼────────┐ ┌─▼──────────┐
│ ML Service   │ │PostgreSQL│ │    S3      │ │ CloudWatch │
│ - Inference  │ │  (RDS)   │ │ - Models   │ │ - Logs     │
│ - Training   │ │ - Txns   │ │ - Features │ │ - Metrics  │
│ - Drift      │ │ - Preds  │ │ - Exports  │ │ - Alarms   │
└──────────────┘ └──────────┘ └────────────┘ └────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Background Jobs (ECS Scheduled Tasks)           │
│  - Drift Detection (Daily)                                   │
│  - Model Retraining (Weekly)                                 │
│  - Feature Materialization (Hourly)                          │
└─────────────────────────────────────────────────────────────┘
```


### 4.3 Service Decomposition

**API Service (Primary):**
- FastAPI application
- Handles HTTP requests
- Orchestrates business logic
- Manages authentication
- Returns predictions

**ML Service (Library/Module within API Service):**
- Model loading and caching
- Feature engineering
- Inference execution
- SHAP explanation generation
- Model versioning

**Training Service (Batch Job):**
- Data extraction from database
- Feature engineering pipeline
- Hyperparameter optimization
- Model training and evaluation
- Model registration
- Experiment tracking

**Drift Detection Service (Scheduled Job):**
- Statistical distribution comparison
- Performance metric tracking
- Alert generation
- Retraining trigger

**Monitoring Dashboard (Separate Service):**
- Streamlit or React application
- Visualizes metrics
- Shows model performance
- Displays drift analysis

---

## 5. Domain Model

### 5.1 Core Entities

**Transaction** (Aggregate Root)
```python
@dataclass
class Transaction:
    transaction_id: UUID
    user_id: str
    merchant_id: str
    amount: Decimal
    currency: str
    timestamp: datetime
    device_id: str
    ip_address: str
    geolocation: Geolocation
    transaction_type: TransactionType
    merchant_category: str
    card_type: str
    is_fraud: Optional[bool]  # Ground truth label
    created_at: datetime
```


**Prediction** (Aggregate Root)
```python
@dataclass
class Prediction:
    prediction_id: UUID
    transaction_id: UUID
    fraud_probability: float  # [0, 1]
    risk_score: int  # [0, 100]
    predicted_class: PredictionClass
    model_version: str
    explanation: Explanation
    latency_ms: int
    timestamp: datetime
    analyst_feedback: Optional[AnalystFeedback]
```

**Model** (Aggregate Root)
```python
@dataclass
class Model:
    model_id: UUID
    version: str
    model_type: ModelType  # XGBOOST, ISOLATION_FOREST
    artifact_path: str  # S3 URI
    metadata: ModelMetadata
    metrics: Dict[str, float]
    training_date: datetime
    status: ModelStatus  # TRAINING, STAGING, PRODUCTION, ARCHIVED
    created_by: str
```

**AnalystFeedback** (Value Object)
```python
@dataclass
class AnalystFeedback:
    feedback_id: UUID
    prediction_id: UUID
    analyst_id: str
    confirmed_fraud: bool
    confidence: int  # [1, 5]
    notes: Optional[str]
    timestamp: datetime
```

**Explanation** (Value Object)
```python
@dataclass
class Explanation:
    top_features: List[FeatureContribution]
    base_value: float
    
@dataclass
class FeatureContribution:
    feature_name: str
    feature_value: float
    shap_value: float
```


**DriftReport** (Aggregate Root)
```python
@dataclass
class DriftReport:
    report_id: UUID
    model_version: str
    report_date: datetime
    feature_drift: Dict[str, float]  # feature -> KL divergence
    prediction_drift: float
    performance_metrics: Dict[str, float]
    drift_detected: bool
    alert_triggered: bool
```

### 5.2 Domain Services

**RiskScoringService**
- Converts fraud probability to risk score [0-100]
- Applies business rules and thresholds
- Considers transaction context

**FeatureEngineeringService**
- Computes derived features
- Handles temporal aggregations
- Manages feature transformations
- Ensures consistency between training and inference

**ModelEvaluationService**
- Calculates performance metrics
- Generates calibration plots
- Computes confusion matrices
- Validates model quality gates

---

## 6. Component Architecture

### 6.1 Detailed Folder Structure

```
enterprise-fraud-detection/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Build, test, lint
│       ├── deploy-staging.yml        # Deploy to staging
│       └── deploy-production.yml     # Deploy to production
├── backend/
│   ├── src/
│   │   ├── domain/                   # Pure domain logic
│   │   │   ├── entities/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── transaction.py
│   │   │   │   ├── prediction.py
│   │   │   │   ├── model.py
│   │   │   │   └── drift_report.py
│   │   │   ├── value_objects/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── explanation.py
│   │   │   │   ├── geolocation.py
│   │   │   │   └── analyst_feedback.py
│   │   │   ├── enums/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── transaction_type.py
│   │   │   │   ├── prediction_class.py
│   │   │   │   └── model_status.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── risk_scoring_service.py
│   │   │       └── feature_engineering_service.py
│   │   ├── application/               # Use cases / orchestration
│   │   │   ├── __init__.py
│   │   │   ├── interfaces/           # Repository interfaces (ports)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── transaction_repository.py
│   │   │   │   ├── prediction_repository.py
│   │   │   │   ├── model_repository.py
│   │   │   │   └── drift_repository.py
│   │   │   ├── use_cases/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── predict_fraud.py
│   │   │   │   ├── submit_feedback.py
│   │   │   │   ├── batch_predict.py
│   │   │   │   ├── detect_drift.py
│   │   │   │   ├── train_model.py
│   │   │   │   └── get_prediction_history.py
│   │   │   └── dto/                  # Data transfer objects
│   │   │       ├── __init__.py
│   │   │       ├── prediction_request.py
│   │   │       ├── prediction_response.py
│   │   │       └── feedback_request.py
│   │   ├── infrastructure/           # External concerns (adapters)
│   │   │   ├── __init__.py
│   │   │   ├── database/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── connection.py
│   │   │   │   ├── models.py         # SQLAlchemy models
│   │   │   │   ├── repositories/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── transaction_repository_impl.py
│   │   │   │   │   ├── prediction_repository_impl.py
│   │   │   │   │   ├── model_repository_impl.py
│   │   │   │   │   └── drift_repository_impl.py
│   │   │   │   └── migrations/       # Alembic migrations
│   │   │   │       ├── env.py
│   │   │   │       └── versions/
│   │   │   ├── ml/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── model_loader.py
│   │   │   │   ├── inference_engine.py
│   │   │   │   ├── explainer.py
│   │   │   │   ├── feature_pipeline.py
│   │   │   │   └── model_registry.py
│   │   │   ├── storage/
│   │   │   │   ├── __init__.py
│   │   │   │   └── s3_client.py
│   │   │   ├── monitoring/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cloudwatch_client.py
│   │   │   │   └── logger.py
│   │   │   └── security/
│   │   │       ├── __init__.py
│   │   │       ├── auth_service.py
│   │   │       └── secrets_manager.py
│   │   ├── presentation/             # API layer
│   │   │   ├── __init__.py
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── v1/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── routes/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── predictions.py
│   │   │   │   │   │   ├── feedback.py
│   │   │   │   │   │   ├── models.py
│   │   │   │   │   │   ├── drift.py
│   │   │   │   │   │   └── health.py
│   │   │   │   │   ├── schemas/      # Pydantic models
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── transaction_schema.py
│   │   │   │   │   │   ├── prediction_schema.py
│   │   │   │   │   │   └── feedback_schema.py
│   │   │   │   │   └── dependencies.py  # DI container
│   │   │   ├── middleware/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth_middleware.py
│   │   │   │   ├── logging_middleware.py
│   │   │   │   └── error_handler.py
│   │   │   └── main.py               # FastAPI app initialization
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── settings.py           # Pydantic settings
│   │   │   └── logging_config.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── validators.py
│   │       └── decorators.py
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   └── infrastructure/
│   │   ├── integration/
│   │   │   ├── test_database.py
│   │   │   ├── test_ml_pipeline.py
│   │   │   └── test_api.py
│   │   └── e2e/
│   │       └── test_prediction_flow.py
│   ├── scripts/
│   │   ├── train_model.py            # Training script
│   │   ├── detect_drift.py           # Drift detection script
│   │   ├── generate_synthetic_data.py
│   │   └── seed_database.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── .env.example
│   └── README.md
├── ml/
│   ├── notebooks/                    # Experimentation
│   │   ├── 01_eda.ipynb
│   │   ├── 02_feature_engineering.ipynb
│   │   ├── 03_model_training.ipynb
│   │   └── 04_model_evaluation.ipynb
│   ├── training/
│   │   ├── __init__.py
│   │   ├── trainer.py
│   │   ├── hyperparameter_tuning.py
│   │   ├── evaluation.py
│   │   └── data_preparation.py
│   ├── drift/
│   │   ├── __init__.py
│   │   ├── drift_detector.py
│   │   ├── statistical_tests.py
│   │   └── performance_monitor.py
│   ├── config/
│   │   ├── model_config.yaml
│   │   └── feature_config.yaml
│   └── README.md
├── monitoring/
│   ├── dashboard/
│   │   ├── app.py                    # Streamlit dashboard
│   │   ├── components/
│   │   │   ├── metrics.py
│   │   │   ├── drift_viz.py
│   │   │   └── model_performance.py
│   │   └── requirements.txt
│   └── alerts/
│       ├── alert_rules.yaml
│       └── notification_config.yaml
├── infrastructure/
│   ├── terraform/                    # Future: IaC
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── docker/
│   │   ├── api.Dockerfile
│   │   ├── training.Dockerfile
│   │   └── monitoring.Dockerfile
│   └── aws/
│       ├── ecs-task-definitions/
│       │   ├── api-service.json
│       │   ├── training-job.json
│       │   └── drift-detection.json
│       └── cloudformation/           # Future: Alternative to Terraform
├── docs/
│   ├── ARCHITECTURE.md               # This document
│   ├── API_DOCUMENTATION.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── DEVELOPMENT_SETUP.md
│   ├── MODEL_CARD.md
│   └── RUNBOOK.md
├── .gitignore
├── .dockerignore
├── README.md
└── LICENSE
```


### 6.2 Module Responsibilities

**Domain Layer**
- **Entities**: Core business objects with identity
- **Value Objects**: Immutable objects without identity
- **Domain Services**: Business logic that doesn't belong to a single entity
- **No Dependencies**: Pure Python, no frameworks

**Application Layer**
- **Use Cases**: Orchestrate domain objects to fulfill business operations
- **Interfaces**: Define contracts for repositories and external services
- **DTOs**: Data structures for inter-layer communication
- **Business Workflow**: Transaction scripts, saga patterns

**Infrastructure Layer**
- **Database**: SQLAlchemy ORM, connection management, migrations
- **ML**: Model loading, inference, explainability
- **Storage**: S3 operations, file handling
- **Monitoring**: CloudWatch integration, structured logging
- **Security**: Authentication, authorization, secrets

**Presentation Layer**
- **API Routes**: FastAPI endpoints
- **Schemas**: Pydantic models for validation
- **Middleware**: Cross-cutting concerns (auth, logging, errors)
- **DI Container**: Dependency injection setup

---

## 7. Data Architecture

### 7.1 Database Schema

**PostgreSQL Schema:**

```sql
-- Transactions table
CREATE TABLE transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    merchant_id VARCHAR(255) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(255),
    ip_address INET,
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6),
    transaction_type VARCHAR(50) NOT NULL,
    merchant_category VARCHAR(100),
    card_type VARCHAR(50),
    is_fraud BOOLEAN,  -- Ground truth
    created_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_user_timestamp (user_id, timestamp),
    INDEX idx_timestamp (timestamp),
    INDEX idx_is_fraud (is_fraud)
);
```

```sql
-- Predictions table
CREATE TABLE predictions (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id),
    fraud_probability NUMERIC(5, 4) NOT NULL,  -- [0, 1]
    risk_score INT NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    predicted_class VARCHAR(20) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    explanation JSONB NOT NULL,
    latency_ms INT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_transaction (transaction_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_model_version (model_version)
);

-- Models table
CREATE TABLE models (
    model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(50) UNIQUE NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    artifact_path TEXT NOT NULL,  -- S3 URI
    metadata JSONB NOT NULL,
    metrics JSONB NOT NULL,
    training_date TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL,  -- TRAINING, STAGING, PRODUCTION, ARCHIVED
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_status (status),
    INDEX idx_version (version)
);

-- Analyst feedback table
CREATE TABLE analyst_feedback (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id UUID NOT NULL REFERENCES predictions(prediction_id),
    analyst_id VARCHAR(255) NOT NULL,
    confirmed_fraud BOOLEAN NOT NULL,
    confidence INT NOT NULL CHECK (confidence BETWEEN 1 AND 5),
    notes TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_prediction (prediction_id),
    INDEX idx_analyst (analyst_id),
    INDEX idx_timestamp (timestamp)
);

-- Drift reports table
CREATE TABLE drift_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version VARCHAR(50) NOT NULL,
    report_date DATE NOT NULL,
    feature_drift JSONB NOT NULL,
    prediction_drift NUMERIC(10, 6) NOT NULL,
    performance_metrics JSONB NOT NULL,
    drift_detected BOOLEAN NOT NULL,
    alert_triggered BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    INDEX idx_model_version (model_version),
    INDEX idx_report_date (report_date)
);
```


### 7.2 S3 Bucket Structure

```
s3://fraud-detection-platform-{account-id}/
├── models/
│   ├── xgboost/
│   │   ├── v1.0.0/
│   │   │   ├── model.pkl
│   │   │   ├── metadata.json
│   │   │   └── explainer.pkl
│   │   ├── v1.1.0/
│   │   └── v2.0.0/
│   └── isolation-forest/
│       ├── v1.0.0/
│       └── v1.1.0/
├── features/
│   ├── training/
│   │   ├── 2026-01/
│   │   │   └── features.parquet
│   │   └── 2026-02/
│   └── validation/
│       └── 2026-03/
├── predictions/
│   ├── batch/
│   │   └── 2026-07-07.parquet
│   └── exports/
│       └── monthly_report_2026-06.csv
└── experiments/
    ├── exp-001/
    │   ├── config.yaml
    │   ├── model.pkl
    │   └── results.json
    └── exp-002/
```

### 7.3 Data Partitioning Strategy

**Transactions Table:**
- Partition by month (timestamp)
- Retention: 7 years
- Hot data: Last 3 months (frequent queries)
- Warm data: 3-12 months (occasional queries)
- Cold data: >12 months (archival, rarely queried)

**Predictions Table:**
- Partition by month (timestamp)
- Retention: 7 years
- Co-located with transactions for join performance

**Performance Optimization:**
- B-tree indexes on foreign keys
- GIN indexes on JSONB columns for explanation queries
- Materialized views for common aggregations
- Connection pooling (10-50 connections)
- Read replicas for analytics queries


---

## 8. Machine Learning Architecture

### 8.1 Model Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        Training Pipeline                         │
└─────────────────────────────────────────────────────────────────┘

1. Data Extraction
   ├── Query transactions from PostgreSQL (last 6 months)
   ├── Filter: Only confirmed labels (is_fraud NOT NULL)
   └── Export to Parquet on S3

2. Feature Engineering
   ├── Temporal features (hour, day_of_week, month)
   ├── Velocity features (transactions per user in 1hr, 24hr, 7d)
   ├── Amount aggregations (mean, std, max per user)
   ├── Geolocation distance from user home
   ├── Device fingerprinting features
   └── Merchant risk scores

3. Train/Validation Split
   ├── Temporal split: Train on first 80%, validate on last 20%
   ├── Stratified by fraud class
   └── Preserve time ordering

4. Hyperparameter Optimization
   ├── Optuna with Tree-structured Parzen Estimator
   ├── Objective: Maximize PR-AUC
   ├── 50 trials with early stopping
   └── Cross-validation: 3-fold time series split

5. Model Training
   ├── XGBoost with optimized hyperparameters
   ├── Class weight adjustment for imbalance
   ├── Early stopping on validation PR-AUC
   └── Feature importance extraction

6. Model Evaluation
   ├── Metrics: PR-AUC, F1, Precision, Recall, ROC-AUC
   ├── Calibration: Brier score, reliability diagram
   ├── Confusion matrix at optimal threshold
   └── Business metrics: FPR at 85% TPR

7. Model Registration
   ├── Save model artifact to S3
   ├── Store metadata in PostgreSQL
   ├── Version: Semantic versioning
   └── Status: STAGING (awaits approval)

8. SHAP Explainer Training
   ├── TreeExplainer for XGBoost
   ├── Background dataset: 100 representative samples
   └── Save explainer to S3
```


### 8.2 Inference Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                       Inference Pipeline                         │
└─────────────────────────────────────────────────────────────────┘

1. Request Validation
   ├── Pydantic schema validation
   ├── Required fields check
   └── Data type enforcement

2. Feature Engineering
   ├── Compute same features as training
   ├── Handle missing values (same imputation strategy)
   └── Feature alignment (match training order)

3. Model Inference
   ├── Load model from memory (cached)
   ├── Predict fraud probability
   └── Track inference latency

4. Anomaly Detection (Secondary)
   ├── Isolation Forest prediction
   ├── Combine with XGBoost (weighted average)
   └── Fallback if primary model fails

5. Risk Scoring
   ├── Convert probability to risk score [0-100]
   ├── Apply business rules (high-risk merchants, amounts)
   └── Threshold-based classification

6. Explainability
   ├── SHAP values for top 5 features
   ├── Base value from training
   └── Format explanation JSON

7. Persistence
   ├── Save prediction to PostgreSQL
   ├── Log to CloudWatch
   └── Emit CloudWatch metrics

8. Response
   ├── Return prediction + explanation
   ├── Include model version
   └── Track total latency
```

### 8.3 Feature Engineering Details

**Temporal Features:**
- `hour_of_day` (0-23)
- `day_of_week` (0-6)
- `is_weekend` (boolean)
- `is_night` (boolean, 22:00-06:00)

**Velocity Features (requires historical queries):**
- `txn_count_1h`: Transactions by user in last 1 hour
- `txn_count_24h`: Transactions by user in last 24 hours
- `txn_count_7d`: Transactions by user in last 7 days
- `amount_sum_1h`: Total amount by user in last 1 hour
- `amount_sum_24h`: Total amount by user in last 24 hours

**Amount Features:**
- `amount_log`: Log-transformed amount
- `amount_zscore`: Z-score relative to user's history
- `amount_percentile`: Percentile relative to user's history

**Geolocation Features:**
- `distance_from_home`: Haversine distance from user's primary location
- `new_country`: Boolean if country differs from user's country
- `velocity_kmh`: Speed implied by distance and time from last transaction

**Device Features:**
- `device_change`: Boolean if device_id differs from user's primary device
- `new_device`: Boolean if device_id never seen for user

**Merchant Features:**
- `merchant_risk_score`: Pre-computed risk score for merchant
- `merchant_fraud_rate`: Historical fraud rate for merchant
- `merchant_category_encoded`: One-hot encoded merchant category

**Interaction Features:**
- `amount_x_hour`: Amount * hour_of_day
- `amount_x_merchant_risk`: Amount * merchant_risk_score

**Total Features**: ~50-70 after encoding

### 8.4 Model Versioning Strategy

**Version Format**: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (feature schema changes)
- **MINOR**: New features, model architecture changes
- **PATCH**: Hyperparameter tuning, bug fixes

**Model Metadata (stored in registry):**
```json
{
  "model_id": "uuid",
  "version": "1.2.3",
  "model_type": "xgboost",
  "training_date": "2026-07-07T00:00:00Z",
  "hyperparameters": {
    "max_depth": 6,
    "learning_rate": 0.05,
    "n_estimators": 200,
    "scale_pos_weight": 10
  },
  "metrics": {
    "pr_auc": 0.87,
    "roc_auc": 0.94,
    "f1_score": 0.81,
    "precision": 0.78,
    "recall": 0.85,
    "fpr_at_85_tpr": 0.04
  },
  "training_data": {
    "n_samples": 500000,
    "fraud_rate": 0.012,
    "date_range": ["2025-12-01", "2026-06-01"]
  },
  "feature_importance": [
    {"feature": "amount_log", "importance": 0.23},
    {"feature": "txn_count_1h", "importance": 0.18}
  ]
}
```


### 8.5 Drift Detection Strategy

**Statistical Tests:**

**Feature Drift (Daily):**
- Kolmogorov-Smirnov test for continuous features
- Chi-squared test for categorical features
- KL divergence for distribution comparison
- Alert if p-value < 0.01 or KL divergence > 0.1

**Prediction Drift (Daily):**
- Compare prediction distribution (mean, std)
- Population Stability Index (PSI)
- Alert if PSI > 0.25 (significant drift)

**Performance Drift (Weekly):**
- Requires ground truth labels (delayed)
- Compare PR-AUC, F1, Precision, Recall
- Alert if PR-AUC drops > 5% relative to baseline

**Retraining Triggers:**
- Scheduled: Weekly (every Sunday at 2 AM UTC)
- Event-driven: Significant drift detected
- Manual: Data scientist requests retraining

**Drift Mitigation:**
- Automated retraining pipeline
- A/B test new model against production
- Gradual rollout (10% -> 50% -> 100%)
- Rollback if performance degrades

---

## 9. AWS Infrastructure Architecture

### 9.1 Network Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                           AWS VPC                             │
│                      CIDR: 10.0.0.0/16                        │
├──────────────────────────────────────────────────────────────┤
│  Availability Zone A          │   Availability Zone B         │
├──────────────────────────────┼───────────────────────────────┤
│  Public Subnet (10.0.1.0/24) │   Public Subnet (10.0.2.0/24)│
│  ├─ NAT Gateway A             │   ├─ NAT Gateway B            │
│  └─ Application Load Balancer (Multi-AZ)                     │
├──────────────────────────────┼───────────────────────────────┤
│  Private Subnet (10.0.10.0/24)│  Private Subnet (10.0.20.0/24)│
│  ├─ ECS Tasks (API Service)  │   ├─ ECS Tasks (API Service)  │
│  ├─ ECS Tasks (Training)     │   ├─ RDS Read Replica         │
│  └─ Lambda Functions          │                               │
├──────────────────────────────┼───────────────────────────────┤
│  Data Subnet (10.0.30.0/24)  │   Data Subnet (10.0.40.0/24)│
│  └─ RDS PostgreSQL (Primary) │   └─ RDS PostgreSQL (Standby)│
└──────────────────────────────┴───────────────────────────────┘
```


### 9.2 Compute Architecture

**ECS Fargate Services:**

**API Service:**
- Cluster: `fraud-detection-api`
- Service: `api-service`
- Task Definition: 2 vCPU, 4 GB RAM
- Desired Count: 3 (1 per AZ + 1 extra)
- Auto Scaling: Target CPU 70%, scale 3-50 tasks
- Health Check: `/health` endpoint
- Deployment: Rolling update, 50% minimum healthy

**Training Job (Scheduled Task):**
- Cluster: `fraud-detection-batch`
- Task Definition: 4 vCPU, 16 GB RAM
- Schedule: Cron (Weekly, Sunday 2 AM UTC)
- Spot Instances: Yes (cost optimization)
- Timeout: 4 hours
- On-Failure: SNS alert, retry once

**Drift Detection Job (Scheduled Task):**
- Task Definition: 2 vCPU, 8 GB RAM
- Schedule: Cron (Daily, 1 AM UTC)
- Timeout: 1 hour

**Monitoring Dashboard (Optional):**
- Cluster: `fraud-detection-monitoring`
- Service: `monitoring-dashboard`
- Task Definition: 1 vCPU, 2 GB RAM
- Desired Count: 1 (low priority)

### 9.3 Storage Architecture

**RDS PostgreSQL:**
- Engine: PostgreSQL 15
- Instance: db.r6g.xlarge (4 vCPU, 32 GB RAM)
- Multi-AZ: Yes (automatic failover)
- Storage: 100 GB gp3 (3000 IOPS, 125 MB/s throughput)
- Auto Scaling: Up to 500 GB
- Backup: Automated daily, 7-day retention
- Encryption: AES-256 at rest
- Read Replica: 1 instance for analytics queries

**S3 Buckets:**
- `fraud-detection-models-{account-id}`: Model artifacts
  - Versioning: Enabled
  - Encryption: SSE-S3
  - Lifecycle: Transition to Glacier after 90 days
- `fraud-detection-data-{account-id}`: Training data, exports
  - Versioning: Enabled
  - Lifecycle: Delete after 365 days
- `fraud-detection-logs-{account-id}`: Application logs
  - Lifecycle: Delete after 90 days


### 9.4 Security Architecture

**IAM Roles:**

**ECS Task Role (API Service):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::fraud-detection-models-*/*",
        "arn:aws:s3:::fraud-detection-models-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:fraud-detection/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

**ECS Task Role (Training Job):**
- S3 read/write to models and data buckets
- RDS read access via secrets manager
- CloudWatch logs and metrics
- SNS publish for alerts

**Security Groups:**

**ALB Security Group:**
- Inbound: HTTPS (443) from 0.0.0.0/0
- Outbound: HTTP (8000) to ECS tasks

**ECS Task Security Group:**
- Inbound: HTTP (8000) from ALB
- Outbound: PostgreSQL (5432) to RDS
- Outbound: HTTPS (443) to AWS services (S3, Secrets Manager)

**RDS Security Group:**
- Inbound: PostgreSQL (5432) from ECS tasks
- No public access

**Secrets Manager:**
- Secret: `fraud-detection/rds-credentials`
  - `username`: postgres
  - `password`: <auto-generated>
  - `host`: <rds-endpoint>
  - `port`: 5432
  - `database`: fraud_detection
- Rotation: 90 days (automated)


### 9.5 Monitoring & Observability

**CloudWatch Metrics:**

**Application Metrics:**
- `fraud-detection/prediction_latency` (Milliseconds, p50, p95, p99)
- `fraud-detection/prediction_count` (Count, per minute)
- `fraud-detection/fraud_rate` (Percentage, predicted fraud rate)
- `fraud-detection/model_version` (Gauge, current version)
- `fraud-detection/error_rate` (Percentage)

**Infrastructure Metrics:**
- ECS CPU utilization
- ECS memory utilization
- RDS CPU utilization
- RDS connections
- ALB request count
- ALB target response time

**CloudWatch Alarms:**
- High error rate (> 1% for 5 minutes) → SNS
- High latency (p99 > 1000ms for 10 minutes) → SNS
- Drift detected → SNS
- Training job failure → SNS
- RDS CPU > 80% → SNS

**CloudWatch Logs:**
- Log Group: `/ecs/fraud-detection/api`
- Log Group: `/ecs/fraud-detection/training`
- Structured JSON logging
- Retention: 90 days
- Insights queries for error analysis

**X-Ray Distributed Tracing:**
- Trace API requests end-to-end
- Identify bottlenecks (DB queries, model inference)
- Track external service calls (S3, Secrets Manager)
- Sampling: 10% of requests

### 9.6 Cost Estimation (Monthly)

**Compute:**
- ECS Fargate API (3 tasks * 24/7): ~$150
- ECS Fargate Training (weekly, 4 hours): ~$5
- ECS Fargate Drift Detection (daily, 1 hour): ~$10
- Total Compute: **~$165**

**Storage:**
- RDS PostgreSQL (db.r6g.xlarge, Multi-AZ): ~$600
- S3 (models, data, logs): ~$50
- Total Storage: **~$650**

**Data Transfer:**
- ALB to ECS: Minimal (same AZ)
- S3 data transfer: ~$20
- Total Transfer: **~$20**

**Monitoring:**
- CloudWatch Logs (10 GB ingestion): ~$5
- CloudWatch Metrics (100 custom metrics): ~$30
- X-Ray (1M traces): ~$5
- Total Monitoring: **~$40**

**Total Estimated Monthly Cost: ~$875**

*(Actual costs depend on traffic, data volume, and AWS region)*


---

## 10. Security Architecture

### 10.1 Authentication & Authorization

**Authentication Methods:**

**1. JWT Tokens (Human Users):**
- Issued by authentication service (future: AWS Cognito)
- Payload: `{user_id, roles, exp}`
- Expiration: 1 hour
- Refresh token: 30 days

**2. API Keys (Service-to-Service):**
- Stored in Secrets Manager
- Rotated every 90 days
- Rate limited per key

**Authorization Model (RBAC):**

**Roles:**
- `admin`: Full access to all endpoints
- `analyst`: Read predictions, submit feedback, view investigations
- `data_scientist`: Read models, metrics, drift reports, trigger training
- `auditor`: Read-only access to audit logs, predictions
- `service`: API key for external services (predict endpoint only)

**Permission Matrix:**

| Endpoint                | admin | analyst | data_scientist | auditor | service |
|-------------------------|-------|---------|----------------|---------|---------|
| POST /predict           | ✓     | ✓       | ✓              | ✗       | ✓       |
| POST /batch/predict     | ✓     | ✗       | ✓              | ✗       | ✓       |
| POST /feedback          | ✓     | ✓       | ✗              | ✗       | ✗       |
| GET /predictions        | ✓     | ✓       | ✓              | ✓       | ✗       |
| GET /models             | ✓     | ✗       | ✓              | ✓       | ✗       |
| POST /models/deploy     | ✓     | ✗       | ✓              | ✗       | ✗       |
| GET /drift              | ✓     | ✗       | ✓              | ✓       | ✗       |
| POST /drift/trigger     | ✓     | ✗       | ✓              | ✗       | ✗       |
| GET /audit-logs         | ✓     | ✗       | ✗              | ✓       | ✗       |


### 10.2 Data Security

**Encryption:**
- **At Rest**: AES-256 for RDS, S3, EBS volumes
- **In Transit**: TLS 1.3 for all HTTP communication
- **Secrets**: AWS Secrets Manager with automatic rotation

**PII Handling:**
- No raw PII stored (user_id is pseudonymized)
- IP addresses hashed before storage
- Geolocation truncated to 2 decimal places (~1 km accuracy)
- Right to deletion: Anonymization script for GDPR compliance

**Input Validation:**
- Pydantic schemas for all API requests
- SQL parameterized queries (SQLAlchemy prevents injection)
- Rate limiting: 100 requests/minute per IP

**Audit Logging:**
- All predictions logged with timestamp, user, model version
- All feedback logged with analyst ID
- All model deployments logged
- Immutable logs (write-only to CloudWatch)

### 10.3 Threat Model

**Threats & Mitigations:**

**T1: Unauthorized Access to Predictions**
- Mitigation: JWT authentication, HTTPS, VPC isolation

**T2: Model Extraction via API**
- Mitigation: Rate limiting, no raw model parameters exposed

**T3: Adversarial Attacks (input manipulation)**
- Mitigation: Input validation, anomaly detection, monitoring for suspicious patterns

**T4: Data Poisoning (malicious feedback)**
- Mitigation: Analyst feedback reviewed before retraining, anomaly detection on feedback patterns

**T5: Secrets Exposure**
- Mitigation: Secrets Manager, no secrets in code, automated rotation

**T6: DDoS**
- Mitigation: ALB with AWS Shield Standard, rate limiting, auto-scaling

**T7: Insider Threats**
- Mitigation: RBAC, audit logging, least privilege IAM policies

---

## 11. API Design

### 11.1 REST API Endpoints

**Base URL:** `https://api.fraud-detection.example.com/v1`


**Prediction Endpoints:**

**POST /predict**
- **Description**: Real-time fraud prediction for a single transaction
- **Auth**: JWT or API Key
- **Request Body**:
```json
{
  "transaction_id": "uuid",
  "user_id": "string",
  "merchant_id": "string",
  "amount": 125.50,
  "currency": "USD",
  "timestamp": "2026-07-07T10:30:00Z",
  "device_id": "string",
  "ip_address": "192.168.1.1",
  "geolocation": {"lat": 37.7749, "lon": -122.4194},
  "transaction_type": "purchase",
  "merchant_category": "electronics",
  "card_type": "visa"
}
```
- **Response**:
```json
{
  "prediction_id": "uuid",
  "transaction_id": "uuid",
  "fraud_probability": 0.87,
  "risk_score": 95,
  "predicted_class": "fraud",
  "model_version": "1.2.3",
  "explanation": {
    "top_features": [
      {"feature": "amount_log", "value": 4.83, "shap_value": 0.32},
      {"feature": "txn_count_1h", "value": 10, "shap_value": 0.28},
      {"feature": "distance_from_home", "value": 5000, "shap_value": 0.19},
      {"feature": "is_night", "value": 1, "shap_value": 0.12},
      {"feature": "device_change", "value": 1, "shap_value": 0.08}
    ],
    "base_value": 0.012
  },
  "latency_ms": 145,
  "timestamp": "2026-07-07T10:30:01Z"
}
```
- **Status Codes**:
  - 200: Success
  - 400: Invalid request
  - 401: Unauthorized
  - 500: Internal server error


**POST /batch/predict**
- **Description**: Batch prediction for multiple transactions
- **Auth**: JWT or API Key
- **Request Body**:
```json
{
  "transactions": [
    { /* transaction 1 */ },
    { /* transaction 2 */ }
  ]
}
```
- **Response**:
```json
{
  "predictions": [
    { /* prediction 1 */ },
    { /* prediction 2 */ }
  ],
  "total_count": 2,
  "latency_ms": 320
}
```

**Feedback Endpoints:**

**POST /feedback**
- **Description**: Submit analyst feedback on a prediction
- **Auth**: JWT (analyst role)
- **Request Body**:
```json
{
  "prediction_id": "uuid",
  "confirmed_fraud": true,
  "confidence": 5,
  "notes": "Confirmed with cardholder"
}
```
- **Response**:
```json
{
  "feedback_id": "uuid",
  "status": "recorded"
}
```

**GET /predictions/{prediction_id}**
- **Description**: Retrieve a specific prediction
- **Auth**: JWT
- **Response**: Prediction object with feedback if available

**GET /predictions**
- **Description**: List predictions with filters
- **Auth**: JWT
- **Query Parameters**:
  - `start_date`: ISO 8601 datetime
  - `end_date`: ISO 8601 datetime
  - `predicted_class`: fraud | legitimate
  - `min_risk_score`: integer [0, 100]
  - `limit`: integer (default 100, max 1000)
  - `offset`: integer (pagination)
- **Response**:
```json
{
  "predictions": [ /* array of predictions */ ],
  "total": 5000,
  "limit": 100,
  "offset": 0
}
```


**Model Endpoints:**

**GET /models**
- **Description**: List all models
- **Auth**: JWT (data_scientist role)
- **Query Parameters**:
  - `status`: PRODUCTION | STAGING | ARCHIVED
- **Response**:
```json
{
  "models": [
    {
      "model_id": "uuid",
      "version": "1.2.3",
      "model_type": "xgboost",
      "status": "production",
      "metrics": {
        "pr_auc": 0.87,
        "f1_score": 0.81
      },
      "training_date": "2026-07-01T00:00:00Z"
    }
  ]
}
```

**GET /models/{version}**
- **Description**: Retrieve specific model details
- **Auth**: JWT
- **Response**: Full model metadata

**POST /models/{version}/deploy**
- **Description**: Deploy a model to production
- **Auth**: JWT (admin or data_scientist)
- **Response**:
```json
{
  "status": "deployed",
  "version": "1.2.3",
  "deployed_at": "2026-07-07T11:00:00Z"
}
```

**Drift Endpoints:**

**GET /drift/reports**
- **Description**: List drift reports
- **Auth**: JWT
- **Query Parameters**:
  - `start_date`: ISO 8601 date
  - `end_date`: ISO 8601 date
  - `drift_detected`: boolean
- **Response**:
```json
{
  "reports": [
    {
      "report_id": "uuid",
      "model_version": "1.2.3",
      "report_date": "2026-07-07",
      "feature_drift": {
        "amount_log": 0.08,
        "txn_count_1h": 0.15
      },
      "prediction_drift": 0.12,
      "drift_detected": false
    }
  ]
}
```

**POST /drift/trigger**
- **Description**: Manually trigger drift detection
- **Auth**: JWT (data_scientist)
- **Response**:
```json
{
  "job_id": "uuid",
  "status": "started"
}
```


**Health & Monitoring Endpoints:**

**GET /health**
- **Description**: Service health check
- **Auth**: None
- **Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-07-07T10:30:00Z",
  "checks": {
    "database": "healthy",
    "model_loaded": "healthy",
    "s3": "healthy"
  }
}
```

**GET /metrics**
- **Description**: Prometheus-compatible metrics
- **Auth**: None (internal only, blocked by security group)
- **Response**: Prometheus text format

### 11.2 Error Response Format

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Missing required field: transaction_id",
    "details": {
      "field": "transaction_id",
      "constraint": "required"
    },
    "timestamp": "2026-07-07T10:30:00Z",
    "request_id": "uuid"
  }
}
```

**Error Codes:**
- `INVALID_REQUEST`: 400
- `UNAUTHORIZED`: 401
- `FORBIDDEN`: 403
- `NOT_FOUND`: 404
- `RATE_LIMIT_EXCEEDED`: 429
- `INTERNAL_SERVER_ERROR`: 500
- `MODEL_UNAVAILABLE`: 503

---

## 12. Data Flow Diagrams

### 12.1 Real-time Prediction Flow

```
┌──────────────┐
│ Client App   │ (Payment Gateway, Mobile App)
└──────┬───────┘
       │ HTTPS
       ▼
┌──────────────────────────────────────────────────────────┐
│                 Application Load Balancer                 │
│            (SSL Termination, Health Checks)               │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│                     API Service (ECS)                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 1. Request Validation (Pydantic)                   │  │
│  └────────────────┬───────────────────────────────────┘  │
│                   ▼                                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 2. Authentication & Authorization                  │  │
│  └────────────────┬───────────────────────────────────┘  │
│                   ▼                                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 3. Feature Engineering                             │  │
│  │    - Query historical data (PostgreSQL)            │  │
│  │    - Compute velocity features                     │  │
│  │    - Derive features                               │  │
│  └────────────────┬───────────────────────────────────┘  │
│                   ▼                                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 4. Model Inference                                 │  │
│  │    - Load model from cache (or S3)                 │  │
│  │    - XGBoost prediction                            │  │
│  │    - Isolation Forest (anomaly score)              │  │
│  └────────────────┬───────────────────────────────────┘  │
│                   ▼                                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 5. Explainability (SHAP)                           │  │
│  └────────────────┬───────────────────────────────────┘  │
│                   ▼                                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 6. Persist Prediction (PostgreSQL)                 │  │
│  └────────────────┬───────────────────────────────────┘  │
│                   ▼                                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 7. Log Metrics (CloudWatch)                        │  │
│  └────────────────┬───────────────────────────────────┘  │
│                   ▼                                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │ 8. Return Response                                 │  │
│  └────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

**Latency Breakdown (Target):**
- Request validation: 5ms
- Authentication: 10ms
- Feature engineering: 50ms (includes DB query)
- Model inference: 80ms
- Explainability: 30ms
- Persistence: 20ms
- Response: 5ms
- **Total: ~200ms**


### 12.2 Training Pipeline Flow

```
┌────────────────────────────────────────────────────────────┐
│         Trigger: Scheduled (Weekly) or Event (Drift)       │
└─────────────────────────┬──────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│            ECS Scheduled Task (Training Job)               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Extract Training Data                            │   │
│  │    - Query PostgreSQL (last 6 months)               │   │
│  │    - Filter: is_fraud NOT NULL                      │   │
│  │    - Export to Parquet (S3)                         │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 2. Feature Engineering                              │   │
│  │    - Compute all features                           │   │
│  │    - Handle missing values                          │   │
│  │    - Save feature statistics                        │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 3. Train/Validation Split                           │   │
│  │    - Temporal split (80/20)                         │   │
│  │    - Stratified sampling                            │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 4. Hyperparameter Optimization                      │   │
│  │    - Optuna (50 trials)                             │   │
│  │    - Objective: PR-AUC                              │   │
│  │    - 3-fold time series CV                          │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 5. Train Final Model                                │   │
│  │    - XGBoost with best params                       │   │
│  │    - Early stopping                                 │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 6. Model Evaluation                                 │   │
│  │    - Compute metrics (PR-AUC, F1, etc.)             │   │
│  │    - Calibration plots                              │   │
│  │    - Feature importance                             │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 7. Train SHAP Explainer                             │   │
│  │    - TreeExplainer                                  │   │
│  │    - Background dataset                             │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 8. Model Registration                               │   │
│  │    - Save artifacts to S3                           │   │
│  │    - Store metadata in PostgreSQL                   │   │
│  │    - Status: STAGING                                │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 9. Alert & Notification                             │   │
│  │    - SNS notification to data science team          │   │
│  │    - Dashboard update                               │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```


### 12.3 Drift Detection Flow

```
┌────────────────────────────────────────────────────────────┐
│           Trigger: Scheduled (Daily at 1 AM UTC)           │
└─────────────────────────┬──────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│       ECS Scheduled Task (Drift Detection Job)             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Load Production Model                            │   │
│  │    - Fetch from S3                                  │   │
│  │    - Load training data statistics                  │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 2. Extract Recent Data                              │   │
│  │    - Query predictions (last 24 hours)              │   │
│  │    - Query transactions (last 24 hours)             │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 3. Feature Drift Detection                          │   │
│  │    - KS test for each feature                       │   │
│  │    - Compare to training distribution               │   │
│  │    - Compute KL divergence                          │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 4. Prediction Drift Detection                       │   │
│  │    - Compute PSI                                    │   │
│  │    - Compare prediction distribution                │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 5. Performance Metrics (if labels available)        │   │
│  │    - Query feedback from analysts                   │   │
│  │    - Compute PR-AUC, F1, etc.                       │   │
│  │    - Compare to baseline                            │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 6. Alert Decision                                   │   │
│  │    - If drift detected → Trigger alert              │   │
│  │    - If performance drop → Trigger retraining       │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 7. Store Drift Report                               │   │
│  │    - Save to PostgreSQL                             │   │
│  │    - Update CloudWatch metrics                      │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 8. Notification                                     │   │
│  │    - SNS alert if drift detected                    │   │
│  │    - Dashboard update                               │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

---

## 13. Development Roadmap


### Phase 1: Foundation (Weeks 1-2)

**Week 1: Project Setup & Domain Layer**
- [ ] Initialize repository structure
- [ ] Setup Python environment (pyenv, poetry/pip)
- [ ] Configure linting (ruff, mypy)
- [ ] Configure pre-commit hooks
- [ ] Implement domain entities (Transaction, Prediction, Model)
- [ ] Implement value objects (Explanation, Geolocation, AnalystFeedback)
- [ ] Implement enums (TransactionType, PredictionClass, ModelStatus)
- [ ] Write unit tests for domain layer (100% coverage)
- [ ] Documentation: Domain model diagrams

**Week 2: Infrastructure & Database**
- [ ] Setup Docker and docker-compose
- [ ] Configure PostgreSQL with docker-compose
- [ ] Implement SQLAlchemy models
- [ ] Setup Alembic for migrations
- [ ] Create initial migration
- [ ] Implement repository interfaces (ports)
- [ ] Implement repository implementations (adapters)
- [ ] Write integration tests for database layer
- [ ] Seed database with synthetic data (1,000 transactions)

### Phase 2: Machine Learning (Weeks 3-4)

**Week 3: Feature Engineering & Training**
- [ ] Generate synthetic training data (100,000 transactions)
- [ ] Implement feature engineering pipeline
- [ ] Implement training script
- [ ] Integrate Optuna for hyperparameter tuning
- [ ] Train initial XGBoost model
- [ ] Implement model evaluation metrics
- [ ] Implement SHAP explainer training
- [ ] Save model artifacts to local filesystem (S3 later)
- [ ] Write tests for ML pipeline

**Week 4: Inference & Model Registry**
- [ ] Implement model loader with caching
- [ ] Implement inference engine
- [ ] Implement SHAP explainer for inference
- [ ] Implement model registry (local, S3 later)
- [ ] Train Isolation Forest (anomaly detection)
- [ ] Implement ensemble logic
- [ ] Write tests for inference pipeline
- [ ] Benchmark inference latency


### Phase 3: API Layer (Weeks 5-6)

**Week 5: FastAPI Application**
- [ ] Setup FastAPI application structure
- [ ] Implement Pydantic schemas
- [ ] Implement dependency injection container
- [ ] Implement prediction endpoint (POST /predict)
- [ ] Implement batch prediction endpoint
- [ ] Implement health check endpoint
- [ ] Implement error handling middleware
- [ ] Implement request logging middleware
- [ ] Write API integration tests
- [ ] Manual testing with Postman/curl

**Week 6: Feedback & Model Management**
- [ ] Implement feedback endpoint (POST /feedback)
- [ ] Implement prediction history endpoint (GET /predictions)
- [ ] Implement model listing endpoint (GET /models)
- [ ] Implement model deployment endpoint (POST /models/{version}/deploy)
- [ ] Implement authentication (JWT, simple in-memory for now)
- [ ] Implement authorization (RBAC decorator)
- [ ] Write e2e tests for complete flows
- [ ] API documentation (OpenAPI)

### Phase 4: Monitoring & Drift Detection (Weeks 7-8)

**Week 7: Logging & Metrics**
- [ ] Implement structured JSON logging
- [ ] Implement CloudWatch client (mock locally)
- [ ] Emit custom metrics (prediction count, latency, fraud rate)
- [ ] Implement X-Ray tracing (mock locally)
- [ ] Setup local Prometheus + Grafana (optional)
- [ ] Create Grafana dashboards
- [ ] Write tests for monitoring components

**Week 8: Drift Detection**
- [ ] Implement drift detection script
- [ ] Statistical tests (KS test, Chi-squared, KL divergence, PSI)
- [ ] Implement drift report generation
- [ ] Store drift reports in database
- [ ] Implement drift alert logic
- [ ] Implement drift endpoint (GET /drift/reports)
- [ ] Write tests for drift detection
- [ ] Run drift detection on historical data


### Phase 5: AWS Integration (Weeks 9-10)

**Week 9: S3 & Secrets Manager**
- [ ] Implement S3 client
- [ ] Migrate model artifacts to S3
- [ ] Update model registry to use S3 paths
- [ ] Implement Secrets Manager client
- [ ] Migrate database credentials to Secrets Manager
- [ ] Configure IAM roles and policies (local dev)
- [ ] Test S3 integration with localstack (optional)
- [ ] Update configuration for AWS resources

**Week 10: RDS & ECS Preparation**
- [ ] Provision RDS PostgreSQL (dev environment)
- [ ] Migrate database to RDS
- [ ] Update connection strings
- [ ] Optimize Dockerfile for production
- [ ] Build and tag Docker images
- [ ] Push images to ECR
- [ ] Create ECS task definitions
- [ ] Test container locally with production-like config

### Phase 6: Deployment & CI/CD (Weeks 11-12)

**Week 11: ECS Deployment**
- [ ] Provision ECS cluster
- [ ] Create ECS services (API, monitoring)
- [ ] Configure Application Load Balancer
- [ ] Configure auto-scaling policies
- [ ] Configure CloudWatch log groups
- [ ] Configure CloudWatch alarms
- [ ] Setup SNS topics for alerts
- [ ] Deploy to staging environment
- [ ] Smoke tests on staging

**Week 12: CI/CD & Production**
- [ ] Setup GitHub Actions workflows
- [ ] Workflow: Lint and test on PR
- [ ] Workflow: Build and push Docker images
- [ ] Workflow: Deploy to staging on merge to main
- [ ] Workflow: Deploy to production (manual approval)
- [ ] Configure scheduled tasks (training, drift detection)
- [ ] Deploy to production
- [ ] Production smoke tests
- [ ] Load testing (locust, k6)
- [ ] Documentation: Deployment guide, runbook


### Phase 7: Frontend & Advanced Features (Weeks 13-14)

**Week 13: Monitoring Dashboard**
- [ ] Setup React + TypeScript + Vite
- [ ] Implement authentication flow
- [ ] Implement metrics dashboard (Recharts)
- [ ] Implement model performance page
- [ ] Implement drift visualization page
- [ ] Implement prediction history table
- [ ] Implement feedback submission form
- [ ] Deploy dashboard to S3 + CloudFront

**Week 14: Polish & Documentation**
- [ ] Code review and refactoring
- [ ] Performance optimization
- [ ] Security audit
- [ ] Complete API documentation
- [ ] Complete README with architecture diagrams
- [ ] Write MODEL_CARD.md
- [ ] Write DEPLOYMENT_GUIDE.md
- [ ] Write DEVELOPMENT_SETUP.md
- [ ] Create demo video
- [ ] Prepare presentation

---

## 14. Technology Justification

### 14.1 Why XGBoost?

**Pros:**
- State-of-the-art performance on tabular data
- Native handling of missing values
- Built-in regularization (L1, L2)
- Feature importance extraction
- Scalable to large datasets
- SHAP TreeExplainer is highly optimized

**Alternatives Considered:**
- **LightGBM**: Similar performance, faster training, but XGBoost has better SHAP integration
- **CatBoost**: Better categorical handling, but slower inference
- **Neural Networks**: Overkill for tabular data, harder to explain, slower inference
- **Logistic Regression**: Too simple, lower performance

**Decision**: XGBoost for best balance of performance, explainability, and inference speed.


### 14.2 Why FastAPI?

**Pros:**
- Asynchronous support (high throughput)
- Automatic OpenAPI documentation
- Pydantic integration (type safety, validation)
- Excellent performance (comparable to Go, Node.js)
- Modern Python 3.12+ features
- Active community and ecosystem

**Alternatives Considered:**
- **Flask**: Synchronous, slower, less modern
- **Django**: Too heavy, batteries-included approach not needed
- **gRPC**: Better for microservices, but REST is simpler for this use case

**Decision**: FastAPI for performance, developer experience, and type safety.

### 14.3 Why PostgreSQL?

**Pros:**
- ACID compliance (critical for audit trail)
- JSONB support (explanations, metadata)
- Excellent query performance with proper indexing
- Proven reliability at scale
- Managed offering on AWS (RDS)
- Strong ecosystem (PgBouncer, PostGIS, TimescaleDB extensions)

**Alternatives Considered:**
- **MongoDB**: No ACID on transactions table, less mature analytics
- **DynamoDB**: Good for key-value, but complex queries expensive
- **Snowflake/BigQuery**: Overkill for OLTP, better for analytics only

**Decision**: PostgreSQL for transactional workloads with analytics capability.

### 14.4 Why AWS ECS Fargate?

**Pros:**
- Serverless containers (no EC2 management)
- Auto-scaling built-in
- Integrates with ALB, CloudWatch, X-Ray
- Cost-effective for variable workloads
- Supports scheduled tasks (training, drift detection)

**Alternatives Considered:**
- **EC2**: More control, but requires patching, scaling, monitoring
- **EKS (Kubernetes)**: More complex, overkill for this scale
- **Lambda**: 15-minute timeout too short for training, cold starts problematic
- **SageMaker**: More expensive, less flexible for custom logic

**Decision**: ECS Fargate for balance of simplicity, cost, and capabilities.


### 14.5 Why SHAP?

**Pros:**
- Theoretically grounded (Shapley values from game theory)
- Model-agnostic (works with any model)
- TreeExplainer is extremely fast for tree-based models
- Provides local (per-prediction) and global explanations
- Industry standard for explainability
- Regulatory acceptance

**Alternatives Considered:**
- **LIME**: Less theoretically grounded, slower, less stable
- **Feature importance**: Only global, no per-prediction explanations
- **Partial dependence plots**: Only global, computationally expensive

**Decision**: SHAP for regulatory compliance and robust explanations.

### 14.6 Why Optuna?

**Pros:**
- State-of-the-art hyperparameter optimization (TPE algorithm)
- Pruning for early stopping
- Parallel trials
- Visualization tools
- Integrates with MLflow, XGBoost, scikit-learn

**Alternatives Considered:**
- **Grid Search**: Exhaustive, computationally expensive
- **Random Search**: Simple, but less efficient
- **Hyperopt**: Older, less maintained
- **Bayesian Optimization (scikit-optimize)**: Good, but Optuna has better ecosystem

**Decision**: Optuna for efficient search and modern features.

---

## 15. Risk Analysis

### 15.1 Technical Risks

**R1: Model Performance Degradation**
- **Probability**: Medium
- **Impact**: High (false negatives = fraud losses, false positives = customer friction)
- **Mitigation**: Drift detection, automated retraining, A/B testing, canary deployments
- **Contingency**: Manual model rollback, rule-based fallback

**R2: Inference Latency Exceeds SLA**
- **Probability**: Low
- **Impact**: High (transaction authorization delays)
- **Mitigation**: Model caching, database query optimization, async processing, circuit breakers
- **Contingency**: Timeout with optimistic approval (higher risk tolerance)


**R3: Database Bottleneck**
- **Probability**: Medium
- **Impact**: High
- **Mitigation**: Connection pooling, read replicas, query optimization, caching (Redis)
- **Contingency**: Horizontal sharding, vertical scaling

**R4: Model Bias & Fairness Issues**
- **Probability**: Medium
- **Impact**: High (regulatory, reputational)
- **Mitigation**: Fairness metrics (demographic parity, equalized odds), bias testing, audit logging
- **Contingency**: Manual review process for high-risk segments

**R5: Data Quality Issues**
- **Probability**: High
- **Impact**: High (garbage in, garbage out)
- **Mitigation**: Input validation, data profiling, outlier detection, monitoring
- **Contingency**: Graceful degradation (use rule-based system if model confidence low)

**R6: Security Breach**
- **Probability**: Low
- **Impact**: Critical
- **Mitigation**: Zero-trust architecture, encryption, RBAC, audit logging, penetration testing
- **Contingency**: Incident response plan, secret rotation, forensic investigation

**R7: AWS Service Outage**
- **Probability**: Low
- **Impact**: High
- **Mitigation**: Multi-AZ deployment, health checks, auto-scaling, graceful degradation
- **Contingency**: Multi-region deployment (future), local cache for critical data

### 15.2 Business Risks

**R8: Label Quality (Ground Truth)**
- **Probability**: High
- **Impact**: High
- **Mitigation**: Analyst feedback loop, label auditing, confidence scoring
- **Contingency**: Semi-supervised learning, active learning

**R9: Evolving Fraud Patterns**
- **Probability**: High
- **Impact**: High
- **Mitigation**: Continuous retraining, anomaly detection, human-in-the-loop
- **Contingency**: Manual rule updates, increased analyst review

**R10: Cost Overruns**
- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**: Cost monitoring, budget alerts, auto-scaling limits, spot instances
- **Contingency**: Downgrade instance types, reduce retention periods


---

## 16. Assumptions & Constraints

### 16.1 Assumptions

**A1: Data Availability**
- Sufficient labeled training data (>100K transactions) is available
- Ground truth labels are reasonably accurate (>90% accuracy)
- Historical data is representative of future patterns

**A2: Infrastructure**
- AWS account with sufficient quotas (ECS, RDS, S3)
- Budget for AWS services (~$1000/month)
- CI/CD pipeline can access AWS resources

**A3: Team & Skills**
- Developer has ML, Python, and AWS experience
- Access to fraud domain expertise for feature engineering
- Analyst team available for feedback loop

**A4: Business Context**
- Real-time prediction requirement is genuine (not batch-only)
- 200ms latency SLA is achievable and sufficient
- False positive rate < 5% is acceptable

**A5: Security & Compliance**
- GDPR compliance is required
- PCI-DSS Level 1 compliance is future scope (not immediate)
- Audit trail requirements are well-defined

### 16.2 Constraints

**C1: Time**
- 14-week development timeline (one developer)
- MVP must be production-ready at end of Phase 6

**C2: Budget**
- AWS costs must stay under $1000/month
- No commercial ML platform subscriptions (SageMaker Feature Store, Databricks)

**C3: Technology**
- Must use Python (company standard)
- Must deploy on AWS (company cloud provider)
- Must use PostgreSQL (company database standard)

**C4: Scalability**
- Initial load: 1000 transactions/minute
- Must scale to 10,000 transactions/minute (future)

**C5: Data**
- No real customer data during development (use synthetic data)
- Model must work with <100 features (inference speed)

**C6: Explainability**
- Every prediction must have an explanation
- Explanation must be human-readable (top 5 features)


---

## 17. Open Questions

### 17.1 Business Questions

**Q1: What is the acceptable false positive rate?**
- **Context**: Higher FPR = more customer friction, Lower FPR = more fraud losses
- **Current Assumption**: 5%
- **Impact**: Model threshold selection, business metrics
- **Needs Input From**: Product, Business Analytics

**Q2: What is the cost of false negatives vs. false positives?**
- **Context**: Asymmetric costs affect optimal threshold
- **Current Assumption**: FN cost = 10x FP cost
- **Impact**: Loss function, threshold optimization
- **Needs Input From**: Finance, Risk Management

**Q3: How quickly do labels become available?**
- **Context**: Affects retraining frequency and drift detection
- **Current Assumption**: 7-30 days
- **Impact**: Retraining schedule, performance monitoring
- **Needs Input From**: Operations, Fraud Team

**Q4: What is the acceptable downtime during deployments?**
- **Context**: Zero-downtime vs. scheduled maintenance
- **Current Assumption**: Zero-downtime (rolling updates)
- **Impact**: Deployment strategy, testing requirements
- **Needs Input From**: Product, Engineering

### 17.2 Technical Questions

**Q5: Should we use feature store (AWS SageMaker Feature Store)?**
- **Context**: Centralized feature management, online/offline consistency
- **Current Assumption**: No (cost constraint, custom implementation)
- **Impact**: Architecture complexity, feature serving latency
- **Trade-off**: Cost vs. operational simplicity

**Q6: Should we implement real-time feature computation?**
- **Context**: Velocity features require historical queries (potential bottleneck)
- **Current Assumption**: Yes, query database for user history
- **Impact**: Inference latency, database load
- **Alternative**: Pre-compute and cache, Kafka/Kinesis streaming


**Q7: Should we implement A/B testing infrastructure?**
- **Context**: Safely test new models before full rollout
- **Current Assumption**: Yes, manual configuration (canary deployment)
- **Impact**: Deployment complexity, monitoring requirements
- **Alternative**: Full cutover with fast rollback capability

**Q8: Should we use caching for model predictions?**
- **Context**: Identical transactions might be submitted multiple times
- **Current Assumption**: No (fraud patterns change rapidly)
- **Impact**: Latency, cache invalidation complexity
- **Trade-off**: Performance vs. freshness

**Q9: What level of model interpretability is required?**
- **Context**: Global vs. local explanations, regulatory requirements
- **Current Assumption**: SHAP local explanations + global feature importance
- **Impact**: Compute overhead, regulatory compliance
- **Needs Input From**: Legal, Compliance

**Q10: Should we support multiple models simultaneously?**
- **Context**: Multi-model ensemble, A/B testing
- **Current Assumption**: One production model + one staging model
- **Impact**: Memory usage, deployment complexity
- **Alternative**: Model ensembles for better performance

### 17.3 Data Questions

**Q11: How should we handle cold start (new users)?**
- **Context**: No historical data for velocity features
- **Current Assumption**: Use default values (e.g., user_mean_amount = global_mean)
- **Impact**: Model performance on new users
- **Alternative**: Separate model for cold start

**Q12: How should we handle class imbalance?**
- **Context**: Fraud rate typically <1%
- **Current Assumption**: Class weights + SMOTE + stratified sampling
- **Impact**: Model training, metric selection
- **Needs Input From**: Data Science

**Q13: Should we implement data versioning?**
- **Context**: Reproducibility, debugging, compliance
- **Current Assumption**: S3 versioning for training data snapshots
- **Impact**: Storage costs, complexity
- **Alternative**: DVC (Data Version Control)


**Q14: What is the data retention policy?**
- **Context**: Storage costs, regulatory requirements
- **Current Assumption**: 7 years (financial industry standard)
- **Impact**: Database size, backup strategy
- **Needs Input From**: Legal, Compliance

### 17.4 Operational Questions

**Q15: Who is on-call for production incidents?**
- **Context**: Alerting, escalation, response time
- **Current Assumption**: Development team
- **Impact**: Runbook requirements, SLA commitments
- **Needs Input From**: Engineering Management

**Q16: What is the disaster recovery strategy?**
- **Context**: RTO (Recovery Time Objective), RPO (Recovery Point Objective)
- **Current Assumption**: Multi-AZ (RTO: 5 min, RPO: 0)
- **Impact**: Backup frequency, cross-region replication
- **Needs Input From**: Infrastructure, Security

**Q17: How should we handle model rollback?**
- **Context**: Model deployment failure, performance degradation
- **Current Assumption**: One-click rollback to previous version
- **Impact**: Model registry design, deployment automation
- **Alternative**: Gradual rollout with automatic rollback on metrics

**Q18: Should we implement blue-green deployment?**
- **Context**: Zero-downtime, fast rollback
- **Current Assumption**: Rolling updates (ECS)
- **Impact**: Infrastructure cost (double resources during deployment)
- **Alternative**: Canary deployment (gradual rollout)

---

## 18. Future Enhancements (Post-MVP)

### Phase 8: Advanced ML Features
- Graph-based fraud detection (user-merchant network)
- Deep learning for sequential patterns (LSTM, Transformer)
- Multi-model ensembles (stacking, blending)
- Active learning (select most informative samples for labeling)
- Online learning (incremental updates without full retraining)

### Phase 9: Scalability & Performance
- Redis caching layer (model predictions, user features)
- Apache Kafka for real-time feature computation
- AWS SageMaker Feature Store
- ElastiCache for session management
- Database read replicas for analytics


### Phase 10: Observability & Operations
- Custom Grafana dashboards (replace Streamlit)
- Prometheus for metrics collection
- Jaeger for distributed tracing (alternative to X-Ray)
- ELK stack for log aggregation and search
- Automated anomaly detection on metrics
- Chaos engineering experiments (fault injection)

### Phase 11: Advanced Features
- Multi-tenancy support (multiple financial institutions)
- Real-time collaboration (analysts can see each other's reviews)
- Advanced investigation tools (graph visualization, timeline)
- Automated report generation for compliance
- Integration with case management systems
- Mobile app for analysts

### Phase 12: Governance & Compliance
- Model governance framework (approval workflows)
- Bias and fairness monitoring (demographic parity, equalized odds)
- Model documentation (model cards)
- Regulatory reporting automation
- GDPR compliance features (right to explanation, right to deletion)
- SOC 2 audit preparation

---

## 19. Success Criteria

### 19.1 Technical Success Metrics

**Performance:**
- [ ] Inference latency p95 < 200ms
- [ ] API throughput > 1,000 requests/second
- [ ] System uptime > 99.9%
- [ ] Model PR-AUC > 0.85
- [ ] Model F1 Score > 0.80
- [ ] False Positive Rate < 5% at 85% TPR

**Code Quality:**
- [ ] Test coverage > 80%
- [ ] All code type-hinted
- [ ] Zero critical security vulnerabilities (Snyk, Bandit)
- [ ] Zero linting errors (ruff)
- [ ] All public APIs documented

**Architecture:**
- [ ] Clean Architecture implemented (layers isolated)
- [ ] Dependency injection used throughout
- [ ] Repository pattern for data access
- [ ] SOLID principles followed


### 19.2 Business Success Metrics

**Fraud Detection:**
- [ ] 85% of fraudulent transactions detected
- [ ] False positive rate < 5%
- [ ] Average investigation time < 5 minutes
- [ ] Analyst feedback adoption rate > 50%

**Operational:**
- [ ] Automated retraining every 7 days
- [ ] Drift detection running daily
- [ ] Zero production incidents in first month
- [ ] Mean time to recovery (MTTR) < 15 minutes

**Portfolio Quality:**
- [ ] GitHub repository has professional README
- [ ] Architecture diagrams included
- [ ] Complete API documentation
- [ ] Deployment guide complete
- [ ] Project receives positive feedback from senior engineers

---

## 20. Conclusion

This architecture specification defines a production-grade fraud detection platform that demonstrates enterprise software engineering best practices. The system is designed to be:

- **Scalable**: Horizontal scaling via ECS, database optimization, caching
- **Reliable**: Multi-AZ deployment, health checks, graceful degradation
- **Maintainable**: Clean Architecture, SOLID principles, comprehensive testing
- **Secure**: Zero-trust, encryption, RBAC, audit logging
- **Observable**: Structured logging, metrics, distributed tracing, dashboards
- **ML-Driven**: Automated training, drift detection, explainability, model lifecycle management

The 14-week roadmap provides a clear path from foundation to production deployment, with each phase building incrementally on the previous one. The architecture is designed to handle millions of transactions daily while maintaining sub-200ms latency and providing comprehensive explainability for every prediction.

This is not a toy project or tutorial. This is a professional portfolio project that demonstrates the ability to design and implement enterprise-scale ML systems.

---

**Next Steps:**
1. Review and approve this architecture specification
2. Answer open questions (Section 17)
3. Begin Phase 1 implementation (project setup and domain layer)
4. Schedule weekly architecture review meetings
5. Maintain architecture decision records (ADRs) for significant changes

**Document Status**: Ready for Implementation ✓

