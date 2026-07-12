from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml

from configs.configs_validator import ConfigError, ConfigsValidator


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


def to_plain_dict(value: Any) -> Any:
    """Преобразует dataclass-объекты и вложенные структуры в словари."""
    if isinstance(value, Path):
        return str(value)
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


def _build_benchmark_config(benchmark_data: Any) -> BenchmarkConfig:
    """Преобразует схему benchmark в dataclass BenchmarkConfig."""
    runs = []
    for run_data in benchmark_data.runs:
        models = tuple(
            ModelConfig(size=size, family=model.family)
            for model in run_data.models
            for size in model.sizes
        )
        runs.append(BenchmarkRun(models=models))

    payload = benchmark_data.model_dump(exclude={"runs", "formats"})
    payload["runs"] = tuple(runs)
    payload["formats"] = tuple(benchmark_data.formats)
    return BenchmarkConfig(**payload)


def read_yaml(path: Path | str) -> Config:
    """Загружает YAML-конфиг и возвращает объект конфигурации после валидации."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8") as handle:
        try:
            raw = yaml.safe_load(handle) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML: {e}") from e

    schema = ConfigsValidator.validate(raw)

    benchmark_data = schema.benchmark
    benchmark: BenchmarkConfig | None = None
    if benchmark_data is not None:
        benchmark = _build_benchmark_config(benchmark_data)

    output_data = schema.output
    output = OutputConfig(
        directory=Path(output_data.directory),
        formats=tuple(output_data.formats),
        use_timestamp=output_data.use_timestamp,
    )

    system_info_data = schema.system_info
    system_info = None
    if system_info_data is not None:
        system_info = SystemInfoConfig(
            collect_gpu=system_info_data.collect_gpu,
            collect_power=system_info_data.collect_power,
            collect_temperature=system_info_data.collect_temperature,
        )

    return Config(benchmark=benchmark, system_info=system_info, output=output)