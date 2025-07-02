"""
Configuration management for Ring Camera Person Detection.

Loads configuration from YAML file specified by environment variable.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config") / "configuration.yaml"
CONFIG_ENV_VAR = "CONFIG_PATH"


@dataclass
class ServerConfig:
    """Configuration for the server."""

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True


@dataclass
class ModelConfig:
    """Configuration for the ML model."""

    size: str = "small"
    device: str = "cpu"
    custom_model_path: str | None = None
    models_dir: str = "./models"
    download_on_startup: bool = True


@dataclass
class InferenceConfig:
    """Configuration for inference settings."""

    conf_threshold: float = 0.25
    iou_threshold: float = 0.45
    max_detections: int = 300
    img_size: int = 640
    half_precision: bool = False
    retina_masks: bool = True
    verbose: bool = False


@dataclass
class AppConfig:
    """Unified application configuration containing all settings."""

    server: ServerConfig
    model: ModelConfig
    inference: InferenceConfig
    classes_to_detect: list[int]


class ConfigurationManager:
    """Manages configuration loading from YAML files."""

    def __init__(self, config_path: str | None = None) -> None:
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file. If None, uses environment variable
            or default path.

        """
        # Determine configuration path
        if config_path is None:
            config_path = os.environ.get(CONFIG_ENV_VAR, str(DEFAULT_CONFIG_PATH))

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Dictionary containing configuration.

        Raises:
            FileNotFoundError: If configuration file does not exist
            ValueError: If configuration file is empty or contains invalid YAML
            Exception: If configuration loading fails

        """
        logger.info("Loading configuration from %s", self.config_path)

        if not self.config_path.exists():
            logger.error("Configuration file %s not found.", self.config_path)
            msg = f"Configuration file {self.config_path} not found."
            raise FileNotFoundError(msg)

        try:
            with self.config_path.open(encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception:
            logger.exception("Error loading configuration")
            raise

        if not config:
            logger.error("Empty configuration file or invalid YAML.")
            msg = "Configuration file is empty or contains invalid YAML."
            raise ValueError(msg)

        logger.info("Configuration loaded successfully")
        return config

    def get_config(self) -> AppConfig:
        """Get unified application configuration with validation and defaults."""
        return AppConfig(
            server=self.get_server_config(),
            model=self.get_model_config(),
            inference=self.get_inference_config(),
            classes_to_detect=self.get_classes_to_detect(),
        )

    def get_server_config(self) -> ServerConfig:
        """Get server configuration with validation and defaults."""
        server_data = self.config.get("server", {})
        return ServerConfig(
            host=server_data.get("host", "127.0.0.1"),  # Use localhost by default for security
            port=server_data.get("port", 8000),
            reload=server_data.get("reload", True),
        )

    def get_model_config(self) -> ModelConfig:
        """Get model configuration with validation and defaults."""
        model_data = self.config.get("model", {})
        return ModelConfig(
            size=model_data.get("size", "small"),
            device=model_data.get("device", "cpu"),
            custom_model_path=model_data.get("custom_model_path"),
            models_dir=model_data.get("models_dir", "./models"),
            download_on_startup=model_data.get("download_on_startup", True),
        )

    def get_inference_config(self) -> InferenceConfig:
        """Get inference configuration with validation and defaults."""
        inference_data = self.config.get("inference", {})
        return InferenceConfig(
            conf_threshold=inference_data.get("conf_threshold", 0.25),
            iou_threshold=inference_data.get("iou_threshold", 0.45),
            max_detections=inference_data.get("max_detections", 300),
            img_size=inference_data.get("img_size", 640),
            half_precision=inference_data.get("half_precision", False),
            retina_masks=inference_data.get("retina_masks", True),
            verbose=inference_data.get("verbose", False),
        )

    def get_classes_to_detect(self) -> list[int]:
        """Get list of classes to detect."""
        return self.config.get("classes_to_detect", [0])  # Default to person class (0) if not specified
