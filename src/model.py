"""
Model definition and loading for Detection.

This module handles the loading and configuration of the YOLO model.
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

import cv2  # pylint: disable=import-error
import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO  # type: ignore[import-untyped]

from config import InferenceConfig, ModelConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ModelSize(Enum):
    """Enum for YOLO model sizes."""

    NANO = "nano"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


class DeviceType(Enum):
    """Enum for supported device types."""

    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"
    XPU = "xpu"


class PersonDetector:
    """YOLO model for detection in images."""

    MODEL_FILES: ClassVar[dict[ModelSize, str]] = {
        ModelSize.NANO: "yolo11n.pt",
        ModelSize.SMALL: "yolo11s.pt",
        ModelSize.MEDIUM: "yolo11m.pt",
        ModelSize.LARGE: "yolo11l.pt",
        ModelSize.XLARGE: "yolo11x.pt",
    }

    def __init__(
        self,
        model_config: ModelConfig,
        inference_config: InferenceConfig,
        classes_to_detect: list[int],
    ) -> None:
        """
        Initialize the person detector with the specified YOLO model.

        Args:
            model_config: Model configuration dataclass
            inference_config: Inference configuration dataclass
            classes_to_detect: List of class IDs to detect

        """
        # store configuration
        self.model_config = model_config
        self.inference_config = inference_config
        self.classes_to_detect = classes_to_detect

        # initialize device
        self.device = model_config.device
        logger.info("Selected device: %s", self.device)

        # prepare model directory
        self.models_dir = Path(model_config.models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # model will be loaded lazily
        self._model: YOLO | None = None
        self._model_params: dict[str, Any] | None = None

    def _get_model_path(self) -> Path:
        """Get the path to the model file."""
        if self.model_config.custom_model_path:
            return Path(self.model_config.custom_model_path)

        model_size = ModelSize(self.model_config.size)
        model_filename = self.MODEL_FILES[model_size]
        return self.models_dir / model_filename

    def _load_model(self) -> None:
        """Load the YOLO model if not already loaded."""
        if self._model is not None:
            return

        model_path = self._get_model_path()

        logger.info("Loading model from: %s", model_path)

        try:
            self._model = YOLO(str(model_path))

            # configure model parameters
            self._model_params = {
                "conf": self.inference_config.conf_threshold,
                "iou": self.inference_config.iou_threshold,
                "imgsz": self.inference_config.img_size,
                "half": self.inference_config.half_precision,
                "device": self.device,
                "max_det": self.inference_config.max_detections,
                "classes": self.classes_to_detect,
                "retina_masks": True,
                "verbose": False,
            }

            logger.info("Model loaded successfully")

        except Exception as e:
            logger.exception("failed to load model from %s", model_path)
            msg = f"Failed to load model from {model_path}"
            raise RuntimeError(msg) from e

    @property
    def model(self) -> YOLO:
        """Get the loaded model, loading it if necessary."""
        if self._model is None:
            self._load_model()
        if self._model is None:
            msg = "Model should be loaded"
            raise RuntimeError(msg)
        return self._model

    @property
    def model_params(self) -> dict[str, Any]:
        """Get model parameters, ensuring model is loaded."""
        if self._model_params is None:
            self._load_model()
        if self._model_params is None:
            msg = "Model parameters should be set"
            raise RuntimeError(msg)
        return self._model_params

    def _decode_image_bytes(self, image_bytes: bytes) -> np.ndarray:
        """Efficiently decode image bytes to numpy array."""
        try:
            # use numpy frombuffer for efficiency
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)  # pylint: disable=no-member

            # convert BGR to RGB
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # pylint: disable=no-member

        except Exception as e:
            logger.exception("error decoding image bytes")
            msg = "Failed to decode image data"
            raise ValueError(msg) from e

    def _process_results(
        self,
        results: list[Any],
        filename: str,
    ) -> dict[str, Any]:
        """Process YOLO results and extract configured class detections."""
        detection_boxes: list[dict[str, Any]] = []
        max_confidence = 0.0

        for result in results:
            if result.boxes is None or len(result.boxes) == 0:
                continue

            # filter for configured classes only
            class_mask = torch.isin(result.boxes.cls, torch.tensor(self.classes_to_detect))
            if not class_mask.any():
                continue

            # get detections for configured classes
            class_confidences = result.boxes.conf[class_mask]
            class_bboxes = result.boxes.xyxy[class_mask]

            for conf, bbox in zip(class_confidences, class_bboxes, strict=True):
                confidence = float(conf.item())
                max_confidence = max(max_confidence, confidence)

                detection_boxes.append(
                    {
                        "confidence": confidence,
                        "bbox": bbox.tolist(),  # [x1, y1, x2, y2]
                    },
                )

        return {
            "filename": filename,
            "person_detected": len(detection_boxes) > 0,
            "confidence": max_confidence,
            "num_persons": len(detection_boxes),
            "person_boxes": detection_boxes,
        }

    def detect_persons(
        self,
        image_data: str | bytes | np.ndarray | Image.Image,
        filename: str = "unknown.jpg",
    ) -> dict[str, Any]:
        """
        Detect persons in an image.

        Args:
            image_data: Image data as file path, bytes, numpy array, or PIL Image
            filename: Optional filename for the image being processed

        Returns:
            Dictionary with detection results specifically for persons

        Raises:
            ValueError: If inference fails

        """
        try:
            # preprocess image data
            image = self._decode_image_bytes(image_data) if isinstance(image_data, bytes) else image_data

            # run inference
            results = self.model.predict(source=image, **self.model_params)  # type: ignore[misc]

            # process and return results
            return self._process_results(results, filename)

        except ValueError:
            # re-raise validation errors with more context
            logger.exception("validation error during inference for %s", filename)
            raise
        except (RuntimeError, OSError):
            logger.exception("unexpected error during inference for %s", filename)
            # return safe fallback response
            return {
                "filename": filename,
                "person_detected": False,
                "confidence": 0.0,
                "num_persons": 0,
                "person_boxes": [],
            }
