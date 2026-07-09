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
    def model_names(self) -> list[str]:
        return [model.name for model in self.models]


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


def read_yaml(path: Path | str) -> Config:
    """Загружает и разбирает YAML-конфиг на неизменяемые структуры."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8") as handle:
        try:
            raw = yaml.safe_load(handle) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML: {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError("YAML root must be a mapping")

    benchmark_data = raw.get("benchmark")
    benchmark: BenchmarkConfig | None = None
    if benchmark_data is not None:
        if not isinstance(benchmark_data, dict):
            raise ConfigError("benchmark must be a mapping")

        runs_data = benchmark_data.get("runs", [])
        if not isinstance(runs_data, list):
            raise ConfigError("benchmark.runs must be a list")

        runs = []
        for run_data in runs_data:
            if not isinstance(run_data, dict):
                raise ConfigError("each benchmark run must be a mapping")
            raw_models = ConfigsValidator.parse_models(
                run_data.get("models", []),
                field_name="benchmark.run.models",
            )
            models = tuple(
                ModelConfig(size=item["size"], family=item["family"])
                for item in raw_models
            )
            runs.append(BenchmarkRun(models=models))

        benchmark = BenchmarkConfig(
            runs=tuple(runs),
            formats=ConfigsValidator.validate_str_list(
                benchmark_data.get("formats"),
                field_name="benchmark.formats",
            ),
            input_size=benchmark_data.get("input_size"),
            batch_size=benchmark_data.get("batch_size"),
            warmup_iterations=benchmark_data.get("warmup_iterations"),
            main_iterations=benchmark_data.get("main_iterations"),
            confidence_threshold=benchmark_data.get("confidence_threshold"),
            test_images=benchmark_data.get("test_images"),
        )

    output_data = raw.get("output")
    if output_data is None:
        raise ConfigError("output section is required")
    if not isinstance(output_data, dict):
        raise ConfigError("output must be a mapping")

    directory = output_data.get("directory", "./results")
    if not isinstance(directory, str) or not directory:
        raise ConfigError("output.directory must be a non-empty string")

    system_info_data = raw.get("system_info")
    system_info = None
    if system_info_data is not None:
        if not isinstance(system_info_data, dict):
            raise ConfigError("system_info must be a mapping")
        system_info = SystemInfoConfig(
            collect_gpu=bool(system_info_data.get("collect_gpu", False)),
            collect_power=bool(system_info_data.get("collect_power", False)),
            collect_temperature=bool(system_info_data.get("collect_temperature", False)),
        )

    output = OutputConfig(
        directory=Path(directory),
        formats=ConfigsValidator.validate_str_list(
            output_data.get("formats"),
            field_name="output.formats",
        ),
        use_timestamp=bool(output_data.get("timestamp", output_data.get("use_timestamp", False))),
    )

    return Config(benchmark=benchmark, system_info=system_info, output=output)