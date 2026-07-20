# core/entities/config.py

import logging
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from core.enums.model import DeviceType

logger = logging.getLogger(__name__)


def to_plain_dict(value: Any) -> Any:
    """Преобразует dataclass-объекты и вложенные структуры в словари."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: to_plain_dict(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain_dict(item) for item in value]
    if is_dataclass(value):
        return {
            field.name: to_plain_dict(getattr(value, field.name))
            for field in fields(value)
        }
    return value


class _ConfigBase:
    """Базовый класс для преобразования конфигурации в словарь."""

    def to_dict(self) -> dict[str, Any]:
        return to_plain_dict(self)


@dataclass(slots=True, frozen=True)
class ModelConfig(_ConfigBase):
    """Конфигурация одной модели в BenchmarkRun."""

    size: str
    family: str

    @property
    def name(self) -> str:
        return f"{self.family}-{self.size}"


@dataclass(slots=True, frozen=True)
class BenchmarkRun(_ConfigBase):
    """Конфигурация одного запуска бенчмарка."""

    models: tuple[ModelConfig, ...]

    @property
    def model_names(self) -> tuple[str, ...]:
        return tuple(model.name for model in self.models)


@dataclass(slots=True, frozen=True)
class BenchmarkConfig(_ConfigBase):
    """Конфигурация бенчмарка, содержащая несколько запусков и общие параметры."""

    runs: tuple[BenchmarkRun, ...]
    formats: tuple[str, ...] = ()
    quantization: tuple[str, ...] = ()
    device_type: DeviceType | None = None
    input_size: int | None = None
    batch_size: int | None = None
    warmup_iterations: int | None = None
    main_iterations: int | None = None
    confidence_threshold: float | None = None
    test_images: str | None = None


@dataclass(slots=True, frozen=True)
class SystemInfoConfig(_ConfigBase):
    """Конфигурация сбора системной информации."""

    collect_gpu: bool
    collect_power: bool
    collect_temperature: bool


@dataclass(slots=True, frozen=True)
class OutputConfig(_ConfigBase):
    """Конфигурация вывода результатов бенчмарка."""

    directory: Path
    formats: tuple[str, ...]
    use_timestamp: bool


@dataclass(slots=True, frozen=True)
class Config(_ConfigBase):
    """Общая конфигурация, объединяющая все разделы."""

    benchmark: BenchmarkConfig | None
    system_info: SystemInfoConfig | None
    output: OutputConfig
