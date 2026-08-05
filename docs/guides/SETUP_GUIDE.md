# Setup Guide - Enterprise Fraud Detection Platform

Complete setup instructions for local development.

## Prerequisites

### Required
- **Python 3.12+**: [Download Python](https://www.python.org/downloads/)
- **Poetry**: Python dependency manager
  ```bash
  pip install poetry
  ```
- **PostgreSQL 15**: [Download PostgreSQL](https://www.postgresql.org/download/)
- **Git**: Version control

### Optional
- **Docker Desktop**: For containerized development
- **VS Code**: Recommended IDE with Python extension
- **pgAdmin**: PostgreSQL GUI (optional)

---

## Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/enterprise-fraud-detection.git
cd enterprise-fraud-detection
```

---

## Step 2: Backend Setup

### 2.1 Install Dependencies

```bash
cd backend

# Install Poetry (if not already installed)
pip install poetry

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### 2.2 Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Key variables to update:
# - DATABASE_URL
# - SECRET_KEY (generate a secure random string)
```

### 2.3 Database Setup

**Option A: Using Docker Compose (Recommended)**

```bash
# Start PostgreSQL in Docker
docker-compose up -d postgres

# Database will be available at:
# postgresql://fraud_user:fraud_password@localhost:5432/fraud_detection
```

**Option B: Local PostgreSQL**

```bash
# Create database
createdb fraud_detection

# Create user
psql -c "CREATE USER fraud_user WITH PASSWORD 'fraud_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE fraud_detection TO fraud_user;"

# Update .env with your credentials
DATABASE_URL=postgresql://fraud_user:fraud_password@localhost:5432/fraud_detection
```

### 2.4 Run Migrations

```bash
# Apply database migrations
poetry run alembic upgrade head
```

### 2.5 Verify Setup

```bash
# Run verification script
poetry run python scripts/verify_setup.py

# Should see all checks pass ✓
```

---

## Step 3: Start Development Server

```bash
# Option 1: Using Poetry
poetry run uvicorn src.presentation.main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Using Makefile
make run

# Option 3: Using Docker Compose
docker-compose up -d
```

**Server will be available at:**
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/v1/docs
- ReDoc: http://localhost:8000/v1/redoc

---

## Step 4: Verify API is Working

### 4.1 Using Browser
Visit http://localhost:8000/v1/health

Should return:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-07-07T12:00:00Z"
}
```

### 4.2 Using curl
```bash
curl http://localhost:8000/v1/health
```

### 4.3 Using Python
```python
import requests

response = requests.get("http://localhost:8000/v1/health")
print(response.json())
```

---

## Step 5: Run Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

---

## Step 6: Code Quality Checks

```bash
# Run linters
poetry run ruff check .

# Format code
poetry run black .

# Sort imports
poetry run isort .

# Type checking
poetry run mypy src/

# Run all checks
poetry run pre-commit run --all-files
```

---

## Step 7: Install Pre-commit Hooks (Optional but Recommended)

```bash
# Install hooks
poetry run pre-commit install

# Now hooks will run automatically on git commit
```

---

## Development Workflow

### Daily Development

```bash
# 1. Pull latest changes
git pull origin main

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Start development server
make run

# 4. Make changes and test
make test

# 5. Run quality checks
make lint

# 6. Commit changes
git add .
git commit -m "feat: add your feature"

# 7. Push and create PR
git push origin feature/your-feature-name
```

### Common Commands

```bash
# Start server
make run

# Run tests
make test

# Lint code
make lint

# Format code
make format

# Clean cache
make clean

# Database migrations
make migrate

# Docker
make docker-up
make docker-down
```

---

## Troubleshooting

### Issue: "Poetry not found"
```bash
# Install Poetry
pip install poetry

# Or using official installer
curl -sSL https://install.python-poetry.org | python3 -
```

### Issue: "Database connection failed"
```bash
# Check PostgreSQL is running
pg_isready

# Check credentials in .env
cat .env | grep DATABASE_URL

# Test connection
psql -U fraud_user -d fraud_detection -h localhost
```

### Issue: "Import errors"
```bash
# Reinstall dependencies
poetry install --no-cache

# Verify installation
poetry run python scripts/verify_setup.py
```

### Issue: "Port 8000 already in use"
```bash
# Find process using port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process or use different port
uvicorn src.presentation.main:app --port 8001
```

### Issue: "Tests failing"
```bash
# Run tests with verbose output
poetry run pytest -v

# Run single test
poetry run pytest tests/unit/domain/test_transaction.py -v

# Clear test cache
rm -rf .pytest_cache
```

---

## IDE Setup (VS Code)

### Recommended Extensions
- Python (Microsoft)
- Pylance
- Ruff
- Black Formatter
- GitLens
- Docker

### Settings (.vscode/settings.json)
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

---

## Next Steps

1. ✅ Complete Phase 1 setup
2. 📖 Read [ARCHITECTURE.md](ARCHITECTURE.md)
3. 🧑‍💻 Review [CONTRIBUTING.md](CONTRIBUTING.md)
4. 🚀 Start implementing Phase 2 (ML features)

---

## Getting Help

- **Documentation**: See [docs/](docs/) folder
- **Issues**: [GitHub Issues](https://github.com/yourusername/enterprise-fraud-detection/issues)
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Setup Complete!** 🎉

You now have a production-grade fraud detection platform foundation ready for development.
