# core/domain/config/model.py

import logging
from typing import Any
from dataclasses import dataclass

from core.domain.config.base import BaseConfig


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ModelConfig(BaseConfig):
    """
    Configuration specifying a single model variant.

    Defines the architectural family and size of a model to be included
    in a benchmark case. This allows the runner to dynamically resolve
    the correct weights and export artifacts.

    Attributes:
        size (str): Model size variant (e.g., 'n', 's', 'm', 'l', 'x').
        family (str): Model architecture family (e.g., 'yolov8', 'yolo11').

    Note:
        - The `name` property automatically concatenates family and size
          for consistent logging and artifact naming (e.g., "yolov8-n").
    """
    size: str
    family: str

    @property
    def name(self) -> str:
        """
        Generates a standardized identifier for the model.

        Returns:
            str: Formatted model name in "{family}-{size}" format.
        """
        return f"{self.family}-{self.size}"