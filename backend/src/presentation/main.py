"""FastAPI Application Factory and Initialization."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.logging_config import get_logger, setup_logging
from src.config.settings import get_settings
from src.infrastructure.database import close_db, init_db
from src.presentation.api.v1 import api_router
from src.presentation.middleware.error_handler import add_exception_handlers
from src.presentation.middleware.logging_middleware import LoggingMiddleware

# Initialize logging first
setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events.

    Handles startup and shutdown events for the FastAPI application.

    Args:
        app: FastAPI application instance

    Yields:
        None during application runtime
    """
    # Startup
    logger.info(
        "Starting application",
        environment=settings.environment,
        version=settings.app_version,
    )

    # Initialize database (for development)
    if settings.is_development:
        await init_db()
        logger.info("Database initialized")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application")
    await close_db()
    logger.info("Application shutdown complete")


def create_application() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Production-grade AI platform for real-time fraud detection",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_credentials,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
    )

    # Custom middleware
    app.add_middleware(LoggingMiddleware)

    # Exception handlers
    add_exception_handlers(app)

    # Include API router
    app.include_router(api_router, prefix=settings.api_prefix)

    # Root endpoint
    @app.get("/", tags=["root"])
    async def root() -> JSONResponse:
        """Root endpoint with API information."""
        return JSONResponse(
            content={
                "name": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
                "status": "operational",
                "docs_url": f"{settings.api_prefix}/docs",
            }
        )

    logger.info("Application created successfully")
    return app


# Create application instance
app = create_application()
