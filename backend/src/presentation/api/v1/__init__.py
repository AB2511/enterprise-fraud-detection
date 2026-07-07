"""API Version 1 - Main router."""

from fastapi import APIRouter

from .routes import customers, health

# Create main API router
api_router = APIRouter()

# Include route modules
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(customers.router, tags=["customers"])

# Future route includes (for next phases):
# api_router.include_router(merchants.router, tags=["merchants"])
# api_router.include_router(transactions.router, tags=["transactions"])
# api_router.include_router(alerts.router, tags=["alerts"])
# api_router.include_router(users.router, tags=["users"])
# api_router.include_router(predictions.router, tags=["predictions"])
# api_router.include_router(audit.router, tags=["audit"])
