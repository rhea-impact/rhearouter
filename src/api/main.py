"""Main FastAPI application for RheaRouter"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.core.config import get_settings
from src.observability.logging import setup_logging, get_logger
from src.backend.ollama_adapter import OllamaAdapter
from src.middleware.error_handler import ErrorHandlerMiddleware
from src.middleware.request_id import RequestIDMiddleware
from src.middleware.rate_limiter import RateLimiterMiddleware
from src.middleware.vram_flow_valve import VRAMFlowValve
from src.api.routes import chat, analytics

settings = get_settings()
logger = setup_logging(log_level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting RheaRouter", extra={"version": settings.app_version})

    # Initialize Ollama adapter
    adapter = OllamaAdapter(
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout
    )

    # Check Ollama is running
    if not await adapter.health_check():
        logger.error("Ollama health check failed - service may not be running")
    else:
        logger.info("Ollama connection established")

    # Set adapter in chat router
    chat.set_ollama_adapter(adapter)

    yield

    # Cleanup
    await adapter.close()
    logger.info("Shutting down RheaRouter")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Personal OpenRouter - Self-hosted inference server",
    lifespan=lifespan,
)

# Register middleware (reverse execution order)
# Error handler wraps everything
app.add_middleware(ErrorHandlerMiddleware)
# Request ID for tracking/logging
app.add_middleware(RequestIDMiddleware)
# Rate limiting before resource-intensive operations
app.add_middleware(RateLimiterMiddleware)
# VRAM flow valve right before inference
app.add_middleware(VRAMFlowValve)

# Include routers
app.include_router(chat.router)
app.include_router(analytics.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse(
        content={
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "online",
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return JSONResponse(
        content={
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
        }
    )


@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible models endpoint"""
    logger.debug("Models list requested")
    return JSONResponse(
        content={
            "object": "list",
            "data": [
                {
                    "id": settings.default_text_model,
                    "object": "model",
                    "created": 1704067200,
                    "owned_by": "rhearouter",
                },
                {
                    "id": settings.default_vision_model,
                    "object": "model",
                    "created": 1704067200,
                    "owned_by": "rhearouter",
                },
                {
                    "id": settings.reasoning_model,
                    "object": "model",
                    "created": 1704067200,
                    "owned_by": "rhearouter",
                },
            ],
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_config=None,  # Use custom logging
    )
