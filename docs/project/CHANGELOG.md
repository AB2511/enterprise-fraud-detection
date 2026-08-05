# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- ML model implementation (XGBoost, SHAP)
- Prediction API endpoints
- Analyst feedback system
- Drift detection
- AWS deployment

## [0.1.0] - 2026-07-07

### Added
- Initial project structure with Clean Architecture
- Domain layer with entities, value objects, enums
- Application layer with repository interfaces
- Infrastructure layer with database setup
- Presentation layer with FastAPI application
- Health check endpoints (/health, /health/ready, /health/live)
- Structured logging with JSON format
- Configuration management with Pydantic Settings
- Database migrations with Alembic
- Docker and Docker Compose setup
- Comprehensive testing structure
- CI/CD with GitHub Actions
- Code quality tools (ruff, black, isort, mypy)
- Pre-commit hooks
- Documentation (README, ARCHITECTURE, CONTRIBUTING)

### Technical
- Python 3.12
- FastAPI 0.109.0
- SQLAlchemy 2.0.25
- PostgreSQL 15
- Poetry for dependency management
- Clean Architecture implementation
- SOLID principles throughout
- Type hints on all functions
- Comprehensive docstrings
