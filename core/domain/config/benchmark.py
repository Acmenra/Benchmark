# core/domain/config/benchmark.py

import logging
from typing import Any, Optional, List
from dataclasses import dataclass

from core.domain.config.base import BaseConfig
from core.domain.config.model import ModelConfig
from core.enums.model import DeviceType, TaskType


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class BenchmarkCase(BaseConfig):
    """Конфигурация одного сценария (кейса) запуска бенчмарка.

    Ранее назывался BenchmarkRun. Переименован, так как сущность должна
    выражаться существительным, а не глаголом.
    """
    models: tuple[ModelConfig, ...]

    @property
    def model_names(self) -> tuple[str, ...]:
        return tuple(model.name for model in self.models)


@dataclass(slots=True, frozen=True)
class BenchmarkConfig(BaseConfig):
    """Глобальная конфигурация бенчмарка, содержащая сценарии и общие параметры."""
    runs: tuple[BenchmarkCase, ...]
    formats: tuple[str, ...] = ()
    quantization: tuple[str, ...] = ()
    task_type: TaskType | None = None
    device_type: DeviceType | None = None
    devices: tuple[DeviceType, ...] | None = None
    input_size: int | None = None
    batch_size: int | None = None
    warmup_iterations: int | None = None
    main_iterations: int | None = None
    confidence_threshold: float | None = None
    test_images: str | None = None


