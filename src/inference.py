"""
API server for Ring Camera Person Detection.

Provides REST endpoints for processing images and detecting people.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from enum import Enum
from typing import Annotated, Any

import uvicorn
from fastapi import FastAPI, File, HTTPException, Response, UploadFile

from config import ConfigurationManager
from model import PersonDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Define application state as an Enum
class AppState(Enum):
    """Enum representing the application's operational state."""

    INITIALIZING = "initializing"
    READY = "ready"
    SHUTTING_DOWN = "shutting_down"


# Global variables
model: PersonDetector | None = None
state: AppState | None = None


async def load_model(config_manager: ConfigurationManager) -> PersonDetector:
    """Initialize and load the person detection model."""
    logger.info("Initializing model")
    model = PersonDetector(  # pylint: disable=redefined-outer-name
        model_config=config_manager.get_model_config(),
        inference_config=config_manager.get_inference_config(),
        classes_to_detect=config_manager.get_classes_to_detect(),
    )
    logger.info("Model loaded successfully")
    return model


@asynccontextmanager
async def lifespan(
    app: FastAPI,  # noqa: ARG001, pylint: disable=redefined-outer-name,disable=unused-argument
) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for the FastAPI application.

    Handles startup and shutdown events.
    """
    global model, state  # noqa: PLW0603, pylint: disable=global-statement

    # Startup logic
    state = AppState.INITIALIZING

    # Load configuration
    config = ConfigurationManager()

    # Load model with configuration
    model = await load_model(config)

    state = AppState.READY

    yield  # This is where the application runs

    # Shutdown logic
    state = AppState.SHUTTING_DOWN


# Create FastAPI app
app = FastAPI(
    title="Ring Camera Person Detector",
    description="API to detect if a person is in Ring camera images",
    lifespan=lifespan,
)


@app.get("/")
async def info() -> dict[str, str]:
    """
    Service information endpoint.

    Provides basic service metadata for monitoring and debugging.
    """
    return {
        # TODO: update with dynamic values
        "name": "Ring Camera Person Detector",
        "version": "0.1.0",
        "description": "API to detect if a person is in Ring camera images",
        "python_version": "3.12.11",
    }


@app.get("/livez")
async def liveness() -> Response:
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the service process is alive and can handle requests.
    Should only fail if the process needs to be restarted.
    """
    return Response(status_code=200)


@app.get("/readyz")
async def readiness() -> Response:
    """
    Kubernetes readiness probe endpoint.

    Returns 200 when service is ready to handle requests.
    Fails during initialization, shutdown, or when dependencies are unavailable.
    """
    if state != AppState.READY:
        logger.error("Service not ready for processing, current state: %s", state)
        raise HTTPException(status_code=503, detail="Service not ready")

    if model is None:
        logger.error("Model not loaded")
        raise HTTPException(status_code=503, detail="Model not loaded")

    # All checks passed
    return Response(status_code=200)


@app.post("/detect")
async def detect_person(
    file: Annotated[UploadFile, File()],
) -> dict[str, Any]:
    """Detect if a person is present in the uploaded image."""
    # Fail if application is shutting down
    if state != AppState.READY:
        logger.error("Service not ready for processing, current state: %s", state)
        raise HTTPException(status_code=503, detail="Service not ready")

    # Fail if model isn't loaded
    if model is None:
        logger.error("Model not loaded")
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Read and validate image bytes
    image_bytes = await file.read()
    if not image_bytes:
        logger.error("Empty file uploaded")
        raise HTTPException(status_code=400, detail="Empty file provided")

    filename = file.filename or "uploaded_image"
    logger.info("Processing detection request for: %s (%d bytes)", filename, len(image_bytes))

    # Process image through detector
    try:
        result = model.detect_persons(
            image_data=image_bytes,
            filename=filename,
        )
    except Exception:
        logger.exception("Unexpected error processing image")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during image processing",
        ) from None

    logger.info("Detection completed successfully for: %s", filename)
    return result


if __name__ == "__main__":
    # Load configuration
    server_config = ConfigurationManager().get_server_config()

    # Start server
    uvicorn.run(
        "inference:app",
        host=server_config.get("host", "0.0.0.0"),  # noqa: S104
        port=server_config.get("port", 8000),
        reload=server_config.get("reload", True),
        log_level="info",
    )
