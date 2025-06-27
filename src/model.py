"""
Model definition and loading for Ring Camera Person Detection.
This module handles the loading and configuration of the YOLOv8 model.
"""

import logging
import os
from typing import Any, Dict, Union

import cv2
import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO

from config import InferenceConfig, ModelConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PersonDetector:
    """YOLOv8 model for person detection in Ring camera images."""

    MODELS = {
        "nano": "yolov8n.pt",
        "small": "yolov8s.pt",
        "medium": "yolov8m.pt",
        "large": "yolov8l.pt",
        "xlarge": "yolov8x.pt",
    }

    def __init__(
        self,
        model_config: ModelConfig,
        inference_config: InferenceConfig,
        classes_to_detect: list[int] | None = None,
    ) -> None:
        """
        Initialize the person detector with the specified YOLOv8 model.

        Args:
            model_config: Model configuration dataclass.
            inference_config: Inference configuration dataclass.
            classes_to_detect: List of class IDs to detect. Default is [0] (person).
        """
        # Model configuration
        model_size = model_config.size
        device = model_config.device
        custom_model_path = model_config.custom_model_path
        models_dir = model_config.models_dir

        # Inference configuration
        self.confidence_threshold = inference_config.conf_threshold
        self.iou_threshold = inference_config.iou_threshold
        self.max_detections = inference_config.max_detections
        self.img_size = inference_config.img_size
        self.half_precision = inference_config.half_precision

        # Classes to detect (default to person only)
        self.classes_to_detect = classes_to_detect if classes_to_detect else [0]

        # Handle 'auto' device selection
        if device == "auto":
            device = None

        # Auto-select device if not specified
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            if (
                self.device == "cpu"
                and hasattr(torch.backends, "mps")
                and torch.backends.mps.is_available()
            ):
                self.device = "mps"  # Use Apple Silicon GPU if available
        else:
            self.device = device

        logger.info(f"Using device: {self.device}")

        os.makedirs(models_dir, exist_ok=True)

        # Load model
        if custom_model_path:
            model_path = custom_model_path
            logger.info(f"Loading custom model from {model_path}")
        else:
            if model_size not in self.MODELS:
                logger.warning(
                    f"Unknown model size: {model_size}, using 'small' instead"
                )
                model_size = "small"

            model_name = self.MODELS[model_size]
            model_path = os.path.join(models_dir, model_name)

            # Check if model exists in the specified directory
            if not os.path.exists(model_path):
                logger.info(
                    f"Pre-trained model not found at {model_path}, will download and save there"
                )
            else:
                logger.info(f"Using pre-trained model from {model_path}")

            logger.info(f"Loading pretrained YOLOv8 {model_size} model")

        try:
            # Set environment variable for cache directory before importing YOLO
            os.environ["YOLO_CACHE_DIR"] = os.path.abspath(models_dir)
            self.model = YOLO(model_path)

            # Configure model parameters
            self.model_params = {
                "conf": self.confidence_threshold,
                "iou": self.iou_threshold,
                "max_det": self.max_detections,
                "device": self.device,
                "classes": self.classes_to_detect,
                "half": self.half_precision,
                "imgsz": self.img_size,
            }

            # Warmup the model
            logger.info("Warming up model with a test inference...")
            self.model.predict(
                torch.zeros(1, 3, 640, 640).to(self.device), **self.model_params
            )
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def detect_persons(
        self,
        image_data: Union[str, bytes, np.ndarray, Image.Image],
        filename: str = "unknown.jpg",
    ) -> Dict[str, Any]:
        """
        Detect persons in an image.

        Args:
            image_data: Image data as file path, bytes, numpy array, or PIL Image.
            filename: Optional filename for the image being processed.

        Returns:
            Dictionary with detection results specifically for persons.
        """
        try:
            # Convert bytes to numpy array if needed
            if isinstance(image_data, bytes):
                try:
                    # Convert bytes to numpy array using OpenCV
                    nparr = np.frombuffer(image_data, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Convert to RGB
                except Exception as e:
                    logger.error(f"Error converting image bytes: {e}")
                    return {
                        "filename": filename,
                        "person_detected": False,
                        "confidence": 0.0,
                        "num_persons": 0,
                        "person_boxes": [],
                    }
            else:
                image = image_data

            # Run inference with configured parameters
            results = self.model.predict(
                source=image, verbose=False, **self.model_params
            )

            # Focus only on person class (class 0 in COCO dataset)
            person_boxes = []
            max_confidence = 0.0

            for result in results:
                for i, cls in enumerate(result.boxes.cls):
                    cls_id = int(cls)
                    if cls_id == 0:  # Only person class
                        confidence = float(result.boxes.conf[i].item())
                        if confidence > max_confidence:
                            max_confidence = confidence

                        # Get bounding box coordinates
                        box = result.boxes.xyxy[i].tolist()
                        person_boxes.append(
                            {"confidence": confidence, "bbox": box}  # [x1, y1, x2, y2]
                        )

            # Create response in the desired format
            response = {
                "filename": filename,
                "person_detected": len(person_boxes) > 0,
                "confidence": max_confidence,
                "num_persons": len(person_boxes),
                "person_boxes": person_boxes,
            }

            return response

        except Exception as e:
            logger.error(f"Error during inference: {e}")
            return {
                "filename": filename,
                "person_detected": False,
                "confidence": 0.0,
                "num_persons": 0,
                "person_boxes": [],
            }
