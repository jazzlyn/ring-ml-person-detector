"""
API server for Ring Camera Person Detection.
Provides REST endpoints for processing images and detecting people.
"""

import logging
import uvicorn

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from model import PersonDetector
from config import ConfigurationManager

# # Add the project root directory to the Python path
# project_root = Path(__file__).parent.parent
# if str(project_root) not in sys.path:
#     sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Ring Camera Person Detector",
    description="API to detect if a person is in Ring camera images",
)


# Dependency to get configuration
def get_config():
    """Dependency to get configuration manager."""
    return ConfigurationManager()


# Dependency to get model
def get_model(config: ConfigurationManager = Depends(get_config)):
    """Dependency to get detector model with configuration."""
    model_config = config.get_model_config()
    inference_config = config.get_inference_config()
    classes_to_detect = config.get_classes_to_detect()

    return PersonDetector(
        model_config=model_config,
        inference_config=inference_config,
        classes_to_detect=classes_to_detect,
    )


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {"status": "ok", "message": "Ring Camera Person Detector API is running"}


@app.post("/detect")
async def detect_person(
    file: UploadFile = File(...), detector: PersonDetector = Depends(get_model)
):
    """
    Detect if a person is present in the uploaded image.

    Args:
        file: Image file to process
        detector: PersonDetector model instance (injected)

    Returns:
        JSON response with person detection results
    """
    try:
        # Read image bytes
        image_bytes = await file.read()

        # Process image through detector
        results = detector.detect_persons(
            image_data=image_bytes, filename=file.filename
        )

        return JSONResponse(content=results)

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    """
    Start the FastAPI server with the given configuration.

    Args:
        host: Host to bind the server to
        port: Port to bind the server to
        reload: Whether to enable auto-reload
    """
    logger.info(f"Starting server on {host}:{port} (reload={reload})")
    uvicorn.run("inference:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    # Get configuration for server
    config = ConfigurationManager()
    server_config = config.get_server_config()

    # Start server with configuration
    start_server(
        host=server_config.get("host", "0.0.0.0"),
        port=server_config.get("port", 8000),
        reload=server_config.get("reload", True),
    )
