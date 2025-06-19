"""
Configuration management for Ring Camera Person Detection.
Loads configuration from YAML file specified by environment variable.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join("config", "configuration.yaml")
CONFIG_ENV_VAR = "RING_DETECTOR_CONFIG"


class ConfigurationManager:
    """Manages configuration loading from YAML files."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file. If None, uses environment variable
            or default path.
        """
        # Determine configuration path
        if config_path is None:
            config_path = os.environ.get(CONFIG_ENV_VAR, DEFAULT_CONFIG_PATH)

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Dictionary containing configuration.

        Raises:
            FileNotFoundError: If configuration file does not exist
            Exception: If configuration loading fails
        """
        logger.info("Loading configuration from %s", self.config_path)

        if not self.config_path.exists():
            logger.error("Configuration file %s not found.", self.config_path)
            raise FileNotFoundError(f"Configuration file {self.config_path} not found.")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config:
                logger.error("Empty configuration file or invalid YAML.")
                raise ValueError(
                    "Configuration file is empty or contains invalid YAML."
                )

            logger.info("Configuration loaded successfully")
            return config
        except Exception as e:
            logger.error("Error loading configuration: %s", e)
            raise

    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration."""
        return self.config.get("server", {})

    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration."""
        return self.config.get("model", {})

    def get_inference_config(self) -> Dict[str, Any]:
        """Get inference configuration."""
        return self.config.get("inference", {})

    def get_classes_to_detect(self) -> list:
        """Get list of classes to detect."""
        return self.config.get(
            "classes_to_detect", [0]
        )  # Default to person class (0) if not specified
