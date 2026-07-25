# core/domain/config/model.py

import logging
from typing import Any
from dataclasses import dataclass

from core.domain.config.base import BaseConfig


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ModelConfig(BaseConfig):
    """Конфигурация одной модели в рамках BenchmarkCase."""
    size: str
    family: str

    @property
    def name(self) -> str:
        return f"{self.family}-{self.size}"