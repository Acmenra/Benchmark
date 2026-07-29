# infrastructure/config/config_reader.py

import yaml
import logging
from typing import Any
from pathlib import Path
from core.enums.model import DeviceType, QuantizationLevel, TaskType
from infrastructure.config.configs_validator import ConfigError, ConfigsValidator
from core.domain.config import BenchmarkConfig, ModelConfig, BenchmarkCase, Config, ReportConfig, SystemInfoConfig


logger = logging.getLogger(__name__)


def _build_benchmark_config(benchmark_data: Any) -> BenchmarkConfig:
    """Преобразует схему benchmark в dataclass BenchmarkConfig."""
    runs = []
    for run_data in benchmark_data.runs:
        models = tuple(
            ModelConfig(size=size, family=model.family)
            for model in run_data.models
            for size in model.sizes
        )
        runs.append(BenchmarkCase(models=models))

    payload = benchmark_data.model_dump(
        exclude={"runs", "formats", "quantization", "task_type", "models_dir"}
    )
    payload["runs"] = tuple(runs)
    payload["formats"] = tuple(benchmark_data.formats)
    payload["quantization"] = tuple(
        benchmark_data.quantization or [QuantizationLevel.FP32.value]
    )
    payload["task_type"] = (
        TaskType(benchmark_data.task_type)
        if benchmark_data.task_type is not None
        else TaskType.DETECT
    )

    if benchmark_data.devices:
        payload["devices"] = tuple(DeviceType(dev) for dev in benchmark_data.devices)
    else:
        payload["devices"] = None

    if benchmark_data.models_dir:
        payload["models_dir"] = Path(benchmark_data.models_dir).resolve()
    else:
        payload["models_dir"] = Path("./models_dir").resolve()

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
    output = ReportConfig(directory=Path(output_data.directory),
                          formats=tuple(output_data.formats),
                          use_timestamp=output_data.use_timestamp)

    system_info_data = schema.system_info
    system_info = None
    if system_info_data is not None:
        system_info = SystemInfoConfig(collect_cpu=system_info_data.collect_cpu,
                                       collect_gpu=system_info_data.collect_gpu,
                                       collect_power=system_info_data.collect_power,
                                       collect_temperature=system_info_data.collect_temperature)

    return Config(benchmark=benchmark, system_info=system_info, output=output)

