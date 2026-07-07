# Enterprise Fraud Detection Platform - Backend

Production-grade FastAPI backend with Clean Architecture.

## Quick Start

### Prerequisites

- Python 3.12+
- Poetry
- PostgreSQL 15
- Docker (optional)

### Local Development Setup

```bash
# Install Poetry
pip install poetry

# Install dependencies
poetry install

# Copy environment file
cp .env.example .env
# Edit .env with your database credentials

# Run database migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn src.presentation.main:app --reload --host 0.0.0.0 --port 8000
```

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

The API will be available at http://localhost:8000

## Project Structure

```
backend/
├── src/
│   ├── domain/          # Pure business logic (entities, value objects)
│   ├── application/     # Use cases and interfaces (ports)
│   ├── infrastructure/  # External adapters (database, ML, AWS)
│   ├── presentation/    # FastAPI routes and schemas
│   ├── config/          # Configuration and settings
│   └── utils/           # Shared utilities
├── tests/
│   ├── unit/           # Unit tests (domain, application)
│   ├── integration/    # Integration tests (database, API)
│   └── e2e/            # End-to-end tests
└── scripts/            # Operational scripts
```

## Architecture

This project follows **Clean Architecture** (Hexagonal Architecture):

- **Domain Layer**: Pure Python, no external dependencies
- **Application Layer**: Use cases, business workflows
- **Infrastructure Layer**: Database, ML models, AWS services
- **Presentation Layer**: FastAPI REST API

### Dependency Rule

Dependencies point inward: Presentation → Application → Domain ← Infrastructure

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test categories
poetry run pytest tests/unit/
poetry run pytest tests/integration/
poetry run pytest tests/e2e/

# Run single test file
poetry run pytest tests/unit/domain/test_transaction.py
```

## Code Quality

```bash
# Lint with Ruff
poetry run ruff check .

# Format with Black
poetry run black .

# Sort imports
poetry run isort .

# Type check with mypy
poetry run mypy src/

# Run all checks
poetry run pre-commit run --all-files
```

## Database Migrations

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback one migration
poetry run alembic downgrade -1

# View migration history
poetry run alembic history
```

## API Documentation

Once the server is running, visit:

- Swagger UI: http://localhost:8000/v1/docs
- ReDoc: http://localhost:8000/v1/redoc
- OpenAPI JSON: http://localhost:8000/v1/openapi.json

## Environment Variables

See `.env.example` for all configuration options.

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key
- `ENVIRONMENT`: development, staging, production
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR

## Development Workflow

1. Create feature branch
2. Write tests first (TDD)
3. Implement feature
4. Run tests and linting
5. Commit with conventional commits
6. Create pull request

## Future Phases

- **Phase 2**: ML implementation (XGBoost, SHAP)
- **Phase 3**: API endpoints (predictions, feedback)
- **Phase 4**: Monitoring and drift detection
- **Phase 5**: AWS integration (S3, Secrets Manager)
- **Phase 6**: Deployment and CI/CD

## License

MIT License - See LICENSE file
