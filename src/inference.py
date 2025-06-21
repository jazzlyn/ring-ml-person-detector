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
from fastapi import FastAPI, File, Response, UploadFile

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


@app.get("/livez")
async def liveness() -> Response:
    """Kubernetes liveness probe endpoint."""
    return Response(status_code=200)


@app.get("/readyz")
async def readiness() -> Response:
    """Kubernetes readiness probe endpoint."""
    # Fail readiness check if we're shutting down or initializing
    if state != AppState.READY:
        return Response(status_code=503)

    # Fail readiness check if model didn't load
    if model is None:
        return Response(status_code=503)

    # All checks passed
    return Response(status_code=200)


@app.post("/detect")
async def detect_person(
    file: Annotated[UploadFile, File()],
) -> Response | dict[str, Any]:
    """Detect if a person is present in the uploaded image."""
    # Fail if application is shutting down
    if state != AppState.READY:
        return Response(status_code=503)

    # Fail if model isn't loaded
    if model is None:
        return Response(status_code=503)

    # Process image through detector
    try:
        # Read image bytes
        image_bytes = await file.read()

        # Process image through detector
        # FIXME: model
        return model.detect_persons(
            image_data=image_bytes,
            filename=file.filename,  # type: ignore[arg-type]
        )
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Error processing image")
        return Response(status_code=500)


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
