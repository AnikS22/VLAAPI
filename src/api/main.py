"""Main FastAPI application for VLA Inference API Platform."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from src.api.routers import inference, models, monitoring, streaming
from src.api.routers.feedback import router as feedback_router
from src.core.config import settings
from src.core.database import close_db, init_db
from src.core.redis_client import close_redis, init_redis
from src.middleware.logging import RequestLoggingMiddleware
from src.monitoring.gpu_monitor import start_gpu_monitoring, stop_gpu_monitoring
from src.monitoring.prometheus_metrics import application_info, application_uptime_seconds
from src.services.embeddings.embedding_service import EmbeddingService
from src.services.model_loader import init_models, shutdown_models
from src.services.vla_inference import (
    start_inference_service,
    stop_inference_service,
)

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown.

    Args:
        app: FastAPI application instance

    Yields:
        None (context manager)
    """
    # Startup
    startup_time = time.time()
    logger.info("Starting VLA Inference API Platform")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    try:
        # Set application info in Prometheus
        application_info.info({
            "version": settings.app_version,
            "environment": settings.environment,
            "python_version": "3.10+"
        })

        # Initialize database
        logger.info("Initializing database connection")
        await init_db()

        # Initialize Redis
        logger.info("Initializing Redis connection")
        await init_redis()

        # Initialize GPU monitoring
        if settings.enable_gpu_monitoring:
            logger.info("Starting GPU monitoring")
            await start_gpu_monitoring()

        # Initialize embedding service
        if settings.enable_embeddings:
            logger.info("Initializing embedding service")
            app.state.embedding_service = EmbeddingService(
                text_model_name=settings.instruction_embedding_model,
                image_model_name=settings.image_embedding_model
            )
            logger.info("Embedding service initialized")

        # Load VLA models
        logger.info("Loading VLA models")
        await init_models()

        # Start inference service
        logger.info("Starting inference service")
        await start_inference_service()

        # Start uptime tracking
        app.state.startup_time = startup_time

        # Create background task for uptime metric
        async def update_uptime():
            while True:
                uptime = time.time() - startup_time
                application_uptime_seconds.set(uptime)
                await asyncio.sleep(10)

        uptime_task = asyncio.create_task(update_uptime())
        app.state.uptime_task = uptime_task

        logger.info("VLA Inference API Platform started successfully")

    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise

    yield  # Application is running

    # Shutdown
    logger.info("Shutting down VLA Inference API Platform")

    try:
        # Cancel uptime tracking
        if hasattr(app.state, 'uptime_task'):
            app.state.uptime_task.cancel()
            try:
                await app.state.uptime_task
            except asyncio.CancelledError:
                pass

        # Stop inference service
        logger.info("Stopping inference service")
        await stop_inference_service()

        # Shutdown models
        logger.info("Shutting down models")
        await shutdown_models()

        # Cleanup embedding service
        if hasattr(app.state, 'embedding_service'):
            logger.info("Cleaning up embedding service")
            app.state.embedding_service.cleanup()

        # Stop GPU monitoring
        if settings.enable_gpu_monitoring:
            logger.info("Stopping GPU monitoring")
            await stop_gpu_monitoring()

        # Close Redis
        logger.info("Closing Redis connection")
        await close_redis()

        # Close database
        logger.info("Closing database connection")
        await close_db()

        logger.info("VLA Inference API Platform shutdown complete")

    except Exception as e:
        logger.error(f"Shutdown error: {e}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Vision-Language-Action (VLA) inference API for robotics with integrated safety monitoring and live streaming",
    lifespan=lifespan,
    debug=settings.debug,
    docs_url="/docs" if not settings.is_production else None,  # Disable docs in production
    redoc_url="/redoc" if not settings.is_production else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Mount Prometheus metrics endpoint
if settings.enable_prometheus:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    logger.info("Prometheus metrics endpoint mounted at /metrics")

# Include routers
app.include_router(inference.router)
app.include_router(models.router)
app.include_router(monitoring.router)
app.include_router(streaming.router)  # WebSocket streaming
app.include_router(feedback_router)  # Feedback for ground truth collection


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "features": {
            "single_inference": True,
            "streaming_inference": True,
            "safety_monitoring": True,
            "feedback_collection": True,
        },
        "docs": "/docs" if not settings.is_production else "disabled",
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions globally.

    Args:
        request: Request that caused the exception
        exc: Exception instance

    Returns:
        JSON error response
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.debug else None,
        },
    )


if __name__ == "__main__":
    import uvicorn

    # Run with uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.auto_reload,
        log_level=settings.log_level.lower(),
        workers=1,  # Single worker for development (GPU limitations)
    )
