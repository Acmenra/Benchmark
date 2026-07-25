# infrastructure/reporting/utils.py

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Any, List, Dict
from dataclasses import fields, is_dataclass

from core.domain.metrics import MetricStatistics


logger = logging.getLogger(__name__)


def to_plain_data(value: Any) -> Any:
    """Рекурсивно преобразует объекты в примитивы (dict, list, str, int...)."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, MetricStatistics):
        return _metric_statistics_to_report(value)
    if is_dataclass(value):
        return {
            field.name: to_plain_data(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {
            str(key): to_plain_data(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [to_plain_data(item) for item in value]
    if hasattr(value, "__dict__"):
        return {
            key: to_plain_data(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return value


def _metric_statistics_to_report(metric: MetricStatistics) -> dict[str, Any]:
    """Преобразовать историю метрики в компактную статистику для отчета."""
    values = _metric_values_without_startup_zero(metric)

    return {
        "unit": metric.unit,
        "samples": len(values),
        "mean": _mean(values),
        "p50": _percentile(values, 0.50),
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def _metric_values_without_startup_zero(metric: MetricStatistics) -> list[float | int]:
    """Исключить стартовый 0.0, если есть реальные ненулевые замеры."""
    values = [point.value for point in metric.history]
    non_zero_values = [value for value in values if value != 0]
    return non_zero_values or values


def _mean(values: list[float | int]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _percentile(values: list[float | int], coeff: float) -> float | None:
    if not values:
        return None

    sorted_values = sorted(values)
    idx = int(coeff * (len(sorted_values) - 1))
    return sorted_values[min(idx, len(sorted_values) - 1)]


def flatten_dict(data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """Разворачивает вложенные словари в плоские ключи с разделителем '.'.
       Списки преобразуются в JSON-строки."""
    flat = {}
    for key, value in data.items():
        flat_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten_dict(value, flat_key))
        elif isinstance(value, list):
            flat[flat_key] = json.dumps(value, ensure_ascii=False)
        else:
            flat[flat_key] = value
    return flat


def to_report_items(data: Any) -> List[Dict[str, Any]]:
    """Преобразует входные данные (одиночную сущность или список) в список словарей."""
    plain = to_plain_data(data)
    if isinstance(plain, list):
        result = []
        for item in plain:
            if isinstance(item, dict):
                result.append(item)
            else:
                result.append({"value": item})
        return result
    else:
        if isinstance(plain, dict):
            return [plain]
        else:
            return [{"value": plain}]
