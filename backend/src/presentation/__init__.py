"""Presentation Layer - FastAPI application and HTTP concerns.

This layer contains:
- FastAPI routes and endpoints
- Request/response schemas (Pydantic)
- Middleware (auth, logging, error handling)
- Dependencies injection setup

This layer depends on application layer but not domain or infrastructure directly.
"""
