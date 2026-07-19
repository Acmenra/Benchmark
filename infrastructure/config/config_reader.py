# infrastructure/config/config_reader.py

import logging

logger = logging.getLogger(__name__)

import yaml
from typing import Any
from pathlib import Path
from infrastructure.config.configs_validator import ConfigError, ConfigsValidator
from core.entities.config import BenchmarkConfig, BenchmarkRun, Config, ModelConfig, OutputConfig, SystemInfoConfig
from core.enums.model import DeviceType


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
    payload["device_type"] = DeviceType(benchmark_data.device_type) # .lower()
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