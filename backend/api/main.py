"""
FastAPI application for LLM Chat API.

Provides SSE endpoints for streaming chat responses.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from temporalio.client import Client


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


temporal_client: Client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI application.

    Connects to Temporal on startup, closes on shutdown.
    """
    global temporal_client

    logger.info("=" * 60)
    logger.info("Starting FastAPI Application")
    logger.info("=" * 60)

    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")

    logger.info(f"Connecting to Temporal: {temporal_address}")
    try:
        temporal_client = await Client.connect(
            temporal_address,
            namespace=temporal_namespace,
        )
        logger.info("✓ Temporal connected")
    except Exception as e:
        logger.error(f"✗ Temporal connection failed: {e}")
        raise

    logger.info("=" * 60)
    logger.info("API Server Ready")
    logger.info("=" * 60)

    yield

    logger.info("Shutting down...")
    logger.info("Shutdown complete")


app = FastAPI(
    title="LLM Chat API",
    description="Stream LLM responses for document-based queries",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware (configurable via environment)
# For development: CORS_ORIGINS=* (default)
# For production: CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "temporal": temporal_client is not None,
        "streaming": "native_temporal",
    }


from backend.api.routes import chat

app.include_router(chat.router, prefix="/api", tags=["chat"])


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )
