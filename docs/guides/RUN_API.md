# Quick Start - Run the API

## Method 1: Using Poetry (Recommended for Development)

```bash
cd backend

# Install dependencies
poetry install

# Run the API
poetry run uvicorn src.presentation.main:app --reload --host 0.0.0.0 --port 8000
```

## Method 2: Using Makefile

```bash
cd backend

# Install dependencies
make dev

# Run the API
make run
```

## Method 3: Using Docker Compose (Recommended for Testing)

```bash
# From project root
cd backend
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## Method 4: Direct Python (if Poetry not available)

```bash
cd backend

# Create virtual environment
python3.12 -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Unix/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run API
python -m uvicorn src.presentation.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Verify API is Running

### 1. Check Health Endpoint

Open browser or use curl:
```bash
curl http://localhost:8000/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-07-07T12:00:00Z"
}
```

### 2. Check API Documentation

Open in browser:
- **Swagger UI**: http://localhost:8000/v1/docs
- **ReDoc**: http://localhost:8000/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/v1/openapi.json

### 3. Check Root Endpoint

```bash
curl http://localhost:8000/
```

Expected response:
```json
{
  "name": "Enterprise Fraud Detection Platform",
  "version": "0.1.0",
  "environment": "development",
  "status": "operational",
  "docs_url": "/v1/docs"
}
```

---

## Troubleshooting

### Port Already in Use
```bash
# Use different port
poetry run uvicorn src.presentation.main:app --port 8001
```

### Database Connection Error
```bash
# Start PostgreSQL with Docker
cd backend
docker-compose up -d postgres

# Or update .env with your database credentials
```

### Import Errors
```bash
# Reinstall dependencies
poetry install --no-cache

# Or
pip install -r requirements.txt --force-reinstall
```

### Module Not Found
```bash
# Ensure you're in the backend directory
cd backend

# Ensure Python path is correct
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Unix/macOS
set PYTHONPATH=%PYTHONPATH%;%CD%  # Windows
```

---

## What's Available Now

✅ **Health Check Endpoints**
- GET `/v1/health` - Basic health check
- GET `/v1/health/ready` - Readiness check (includes DB)
- GET `/v1/health/live` - Liveness probe

✅ **API Documentation**
- Swagger UI at `/v1/docs`
- ReDoc at `/v1/redoc`
- OpenAPI spec at `/v1/openapi.json`

✅ **Root Endpoint**
- GET `/` - API information

---

## Coming in Future Phases

🔜 **Phase 2: ML Layer**
- Model training endpoints
- Inference engine
- Feature engineering

🔜 **Phase 3: Business APIs**
- POST `/v1/predict` - Fraud prediction
- POST `/v1/feedback` - Analyst feedback
- GET `/v1/predictions` - Prediction history

🔜 **Phase 4: Monitoring**
- GET `/v1/drift/reports` - Drift detection results
- Metrics endpoints
- Performance dashboards

---

**Status**: ✅ Phase 1 Complete - API Running Successfully!
