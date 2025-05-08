"""
API server for Ring Camera Person Detection.
Provides REST endpoints for processing images and detecting people.
"""

import logging
import signal
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

# Application state variable
# Possible values: "initializing", "ready", "shutting_down"
state = "initializing"

# Global variables for configuration and model
config_manager = None
detector_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    global config_manager, detector_model, state

    # Startup logic
    logger.info("Application starting up")
    state = "initializing"

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
        state = "ready"
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        # Continue initialization, but the readiness check will fail

    # Register signal handlers for graceful shutdown
    original_sigterm_handler = signal.getsignal(signal.SIGTERM)
    original_sigint_handler = signal.getsignal(signal.SIGINT)

    def sigterm_handler(sig, frame):
        """Handle SIGTERM by marking app as not ready before shutdown"""
        global state
        logger.info("Received SIGTERM. Starting graceful shutdown...")
        state = "shutting_down"  # Update app state to fail readiness checks
        logger.info("Readiness probes now failing, completing current requests...")

        # Give Kubernetes time to recognize the readiness change (10 seconds)
        # but no threading is needed, we can just proceed to call the original handler
        logger.info("Initiating shutdown sequence...")
        # Call original handler to perform the actual shutdown
        original_sigterm_handler(sig, frame)

    signal.signal(signal.SIGTERM, sigterm_handler)

    signal.signal(signal.SIGTERM, sigterm_handler)

    yield  # This is where the application runs

    # Restore original signal handlers
    signal.signal(signal.SIGTERM, original_sigterm_handler)
    signal.signal(signal.SIGINT, original_sigint_handler)

    # Shutdown logic
    state = "shutting_down"
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
    # Fail readiness check if we're shutting down or initializing
    if state != "ready":
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
    if state != "ready":
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
    manager = ConfigurationManager()
    server_config = manager.get_server_config()

    # Start server
    uvicorn.run(
        "inference:app",
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8000),
        reload=server_config.get("reload", True),
        log_level="info",
    )
