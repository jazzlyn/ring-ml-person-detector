"""
API server for Ring Camera Person Detection.
Provides REST endpoints for processing images and detecting people.
"""

import logging
import signal
import threading
import uvicorn

from fastapi import FastAPI, UploadFile, File
from fastapi import Response
from contextlib import asynccontextmanager
from model import PersonDetector
from config import ConfigurationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Flag to track shutdown state
is_shutting_down = threading.Event()

# Global variables for configuration and model
config_manager = None
detector_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    global config_manager, detector_model

    # Startup logic
    logger.info("Application starting up")
    is_shutting_down.clear()  # Ensure we start in a ready state

    # Load configuration and model once at startup
    try:
        logger.info("Loading configuration")
        config_manager = ConfigurationManager()

        logger.info("Initializing model")
        detector_model = PersonDetector(
            model_config=config_manager.get_model_config(),
            inference_config=config_manager.get_inference_config(),
            classes_to_detect=config_manager.get_classes_to_detect(),
        )
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        # Continue initialization, but the readiness check will fail

    # Register signal handlers for graceful shutdown
    original_sigterm_handler = signal.getsignal(signal.SIGTERM)
    original_sigint_handler = signal.getsignal(signal.SIGINT)

    def sigterm_handler(sig, frame):
        """Handle SIGTERM by marking app as not ready before shutdown"""
        logger.info("Received SIGTERM. Starting graceful shutdown...")
        is_shutting_down.set()  # Set the shutdown flag to fail readiness checks
        logger.info("Readiness probes now failing, completing requests...")

        # Allow some time for requests and K8s to notice readiness state change
        threading.Timer(10, original_sigterm_handler, args=[sig, frame]).start()

    signal.signal(signal.SIGTERM, sigterm_handler)

    yield  # This is where the application runs

    # Restore original signal handlers
    signal.signal(signal.SIGTERM, original_sigterm_handler)
    signal.signal(signal.SIGINT, original_sigint_handler)

    # Shutdown logic
    logger.info("Application shutting down")


# Create FastAPI app
app = FastAPI(
    title="Ring Camera Person Detector",
    description="API to detect if a person is in Ring camera images",
    lifespan=lifespan,
)


@app.get("/livez")
async def liveness():
    """Kubernetes liveness probe endpoint."""
    return Response(status_code=200)


@app.get("/readyz")
async def readiness():
    """Kubernetes readiness probe endpoint."""
    # Fail readiness check if we're shutting down
    if is_shutting_down.is_set():
        return Response(status_code=503)

    # Fail readiness check if model didn't load
    if detector_model is None:
        return Response(status_code=503)

    # All checks passed
    return Response(status_code=200)


@app.post("/detect")
async def detect_person(file: UploadFile = File(...)):
    """Detect if a person is present in the uploaded image."""
    # Fail if application is shutting down
    if is_shutting_down.is_set():
        return Response(status_code=503)

    # Fail if model isn't loaded
    if detector_model is None:
        return Response(status_code=503)

    try:
        # Read image bytes
        image_bytes = await file.read()

        # Process image through detector
        results = detector_model.detect_persons(
            image_data=image_bytes, filename=file.filename
        )
        return results

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return Response(status_code=500)


if __name__ == "__main__":
    # Get server configuration
    temp_config = ConfigurationManager()
    server_config = temp_config.get_server_config()

    # Start server
    uvicorn.run(
        "inference:app",
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8000),
        reload=server_config.get("reload", True),
        log_level="info",
    )
