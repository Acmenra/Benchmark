"""Загрузка и валидация YAML-конфигурации в сущности `core.entities.AppConfig`."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from edge_ai_benchmark.core.entities import (
    AppConfig,
    BenchmarkConfig,
    ModelGroupConfig,
    OutputConfig,
    SystemInfoConfig,
)
from edge_ai_benchmark.core.enums import ModelFormat, ModelSource, Precision

logger = logging.getLogger(__name__)


class ConfigError(ValueError):
    """Ошибка валидации конфигурации."""


def _require(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise ConfigError(f"В разделе '{context}' отсутствует обязательное поле '{key}'")
    return mapping[key]


def _parse_model_group(raw: dict[str, Any]) -> ModelGroupConfig:
    family = _require(raw, "family", "benchmark.models[]")
    sizes = _require(raw, "sizes", "benchmark.models[]")
    if not isinstance(sizes, list) or not sizes:
        raise ConfigError(f"'sizes' для семейства '{family}' должен быть непустым списком")

    source_raw = raw.get("source", ModelSource.BUILTIN.value)
    try:
        source = ModelSource(source_raw)
    except ValueError as exc:
        raise ConfigError(f"Неизвестный source '{source_raw}' у семейства '{family}'") from exc

    return ModelGroupConfig(
        family=family,
        sizes=sizes,
        source=source,
        local_paths=raw.get("local_paths", {}),
        hf_repo_id=raw.get("hf_repo_id"),
        hf_filenames=raw.get("hf_filenames", {}),
    )


def _parse_benchmark(raw: dict[str, Any]) -> BenchmarkConfig:
    raw_models = _require(raw, "models", "benchmark")
    if not isinstance(raw_models, list) or not raw_models:
        raise ConfigError("'benchmark.models' должен быть непустым списком")
    models = [_parse_model_group(item) for item in raw_models]

    raw_formats = _require(raw, "formats", "benchmark")
    if not isinstance(raw_formats, list) or not raw_formats:
        raise ConfigError("'benchmark.formats' должен быть непустым списком")
    try:
        formats = [ModelFormat(fmt) for fmt in raw_formats]
    except ValueError as exc:
        raise ConfigError(f"Неизвестный формат в 'benchmark.formats': {raw_formats}") from exc

    defaults = BenchmarkConfig(models=models, formats=formats)

    precision_raw = raw.get("precision", defaults.precision.value)
    try:
        precision = Precision(precision_raw)
    except ValueError as exc:
        raise ConfigError(f"Неизвестная precision '{precision_raw}'") from exc

    return BenchmarkConfig(
        models=models,
        formats=formats,
        input_size=raw.get("input_size", defaults.input_size),
        batch_size=raw.get("batch_size", defaults.batch_size),
        warmup_iterations=raw.get("warmup_iterations", defaults.warmup_iterations),
        main_iterations=raw.get("main_iterations", defaults.main_iterations),
        duration_minutes=raw.get("duration_minutes", defaults.duration_minutes),
        confidence_threshold=raw.get("confidence_threshold", defaults.confidence_threshold),
        test_images=raw.get("test_images", defaults.test_images),
        task=raw.get("task", defaults.task),
        accuracy_dataset=raw.get("accuracy_dataset", defaults.accuracy_dataset),
        measure_accuracy=raw.get("measure_accuracy", defaults.measure_accuracy),
        precision=precision,
        save_predictions=raw.get("save_predictions", defaults.save_predictions),
        predictions_dir=raw.get("predictions_dir", defaults.predictions_dir),
    )


def _parse_output(raw: dict[str, Any] | None) -> OutputConfig:
    defaults = OutputConfig()
    raw = raw or {}
    return OutputConfig(
        directory=raw.get("directory", defaults.directory),
        formats=raw.get("formats", defaults.formats),
        timestamp=raw.get("timestamp", defaults.timestamp),
    )


def _parse_system_info(raw: dict[str, Any] | None) -> SystemInfoConfig:
    defaults = SystemInfoConfig()
    raw = raw or {}
    return SystemInfoConfig(
        collect_cpu=raw.get("collect_cpu", defaults.collect_cpu),
        collect_ram=raw.get("collect_ram", defaults.collect_ram),
        collect_disk=raw.get("collect_disk", defaults.collect_disk),
        collect_gpu=raw.get("collect_gpu", defaults.collect_gpu),
        collect_power=raw.get("collect_power", defaults.collect_power),
        collect_temperature=raw.get("collect_temperature", defaults.collect_temperature),
    )


def load_config(path: str | Path) -> AppConfig:
    """Загрузить и провалидировать YAML-конфигурацию бенчмарка.

    Args:
        path: Путь к YAML-файлу конфигурации.

    Returns:
        Провалидированный `AppConfig`.

    Raises:
        ConfigError: Если конфигурация некорректна или содержит неизвестные значения.
        FileNotFoundError: Если файл конфигурации не найден.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Файл конфигурации не найден: {path}")

    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    if not isinstance(raw, dict):
        raise ConfigError(f"Корень конфигурации {path} должен быть YAML-словарём")

    logger.debug("Загружена конфигурация из %s", path)
    return AppConfig(
        benchmark=_parse_benchmark(_require(raw, "benchmark", "root")),
        output=_parse_output(raw.get("output")),
        system_info=_parse_system_info(raw.get("system_info")),
    )
