"""FastAPI application factory and main entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from legacylens.api.routes.files import router as files_router
from legacylens.api.routes.health import router as health_router
from legacylens.api.routes.query import router as query_router
from legacylens.core.config import get_settings
from legacylens.db import close_db, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()

    # Startup
    logger.info("Starting LegacyLens API...")
    logger.info(f"Database URL: {settings.database_url.split('@')[-1]}")

    try:
        # Initialize database connection and create tables
        await init_db()
        logger.info("Database connection established and tables verified")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Verify OpenAI API key is configured
    if not settings.openai_api_key:
        logger.warning("OpenAI API key not configured - some features will be unavailable")

    logger.info("LegacyLens API ready")

    yield

    # Shutdown
    logger.info("Shutting down LegacyLens API...")
    await close_db()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="LegacyLens",
        description="RAG system for legacy Fortran scientific codebases",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, tags=["health"])
    # API v1 endpoints
    app.include_router(query_router, prefix="/api/v1", tags=["query"])
    app.include_router(files_router, prefix="/api/v1", tags=["files"])

    return app


# Create the application instance
app = create_app()
