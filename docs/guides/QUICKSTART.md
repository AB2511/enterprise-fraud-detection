# Quick Start - 5 Minutes to Running API

## Prerequisites
- Python 3.12+
- Poetry (or pip)

## Step 1: Install Dependencies (1 minute)

```bash
cd backend
poetry install
```

## Step 2: Setup Environment (30 seconds)

```bash
# Copy environment file
cp .env.example .env

# No need to edit for quick start - defaults work!
```

## Step 3: Start API (30 seconds)

```bash
poetry run uvicorn src.presentation.main:app --reload
```

## Step 4: Verify (1 minute)

Open browser to: **http://localhost:8000/v1/docs**

You should see the Swagger API documentation! 🎉

## Test the API

```bash
# Test health endpoint
curl http://localhost:8000/v1/health

# Should return:
# {"status":"healthy","version":"0.1.0",...}
```

## What's Working?

✅ FastAPI application running  
✅ Structured logging active  
✅ Health check endpoints  
✅ API documentation  
✅ Error handling middleware  
✅ Request logging  

## What's Next?

- Read [SETUP_GUIDE.md](SETUP_GUIDE.md) for full setup
- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system
- Read [backend/README.md](backend/README.md) for development guide
- Start implementing Phase 2 (ML features)

## Troubleshooting

**Port 8000 in use?**
```bash
poetry run uvicorn src.presentation.main:app --port 8001
```

**Import errors?**
```bash
# Reinstall
poetry install --no-cache
```

**Want to use Docker instead?**
```bash
docker-compose up -d
```

---

**That's it! You have a production-grade API running in 5 minutes!** 🚀
