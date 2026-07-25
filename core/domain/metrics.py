# core/domain/metrics.py

import logging
from typing import Any, Dict
from dataclasses import dataclass

from core.domain.config import BenchmarkCase

logger = logging.getLogger(__name__)


@dataclass
class DataPoint:
    time_in_ms: int
    value: float | int


class MetricStatistics:
    def __init__(self, unit: str | None = None) -> None:
        self.history: list[DataPoint] = []
        self.unit: str | None = unit

    @property
    def minimum(self) -> float | None:
        if len(self.history) == 0:
            return None
        return min([i.value for i in self.history])

    @property
    def maximum(self) -> float | None:
        if len(self.history) == 0:
            return None
        return max([i.value for i in self.history])

    @property
    def mean(self) -> float | None:
        if len(self.history) == 0:
            return None
        values = [i.value for i in self.history]
        return sum(values) / len(values)
    
    @property
    def median(self) -> float | None:
        if len(self.history) == 0:
            return None

        values = [i.value for i in self.history]
        values.sort()

        n = len(values)
        if n % 2 == 0:
            return (values[n // 2] + values[n // 2 - 1]) / 2
        else:
            return values[n // 2]

    @property
    def p95(self) -> float | None:
        return self._percentile(0.95)

    @property
    def p99(self) -> float | None:
        return self._percentile(0.99)

    def _percentile(self, coeff: float) -> float | None:
        if len(self.history) == 0:
            return None
        
        values = [i.value for i in self.history]
        values.sort()

        idx = int(coeff * (len(values) - 1))

        return values[min(idx, len(values)-1)]


@dataclass(slots=True)
class LatencyStats:
    fps: float | None
    mean_ms: float | None
    p50_ms: float | None
    p95_ms: float | None
    p99_ms: float | None
    min_ms: float | None
    max_ms: float | None

    @classmethod
    def from_history(cls, history: list[DataPoint]) -> "LatencyStats | None":
        """Собирает статистику из истории замеров latency.

        Args:
            history: Список точек latency (value в миллисекундах).

        Returns:
            ``LatencyStats`` или ``None``, если история пуста.
        """
        if not history:
            return None

        values = sorted(point.value for point in history)
        mean = sum(values) / len(values)

        return cls(
            fps=1000.0 / mean if mean > 0 else None,
            mean_ms=mean,
            p50_ms=_percentile(values, 0.50),
            p95_ms=_percentile(values, 0.95),
            p99_ms=_percentile(values, 0.99),
            min_ms=values[0],
            max_ms=values[-1],
        )


def _percentile(sorted_values: list[float], coeff: float) -> float:
    """Возвращает процентиль по отсортированному списку.

    Формула совпадает с MetricStatistics._percentile, но работает
    по уже отсортированным значениям без повторной сортировки.
    """
    idx = int(coeff * (len(sorted_values) - 1))
    return sorted_values[min(idx, len(sorted_values) - 1)]


@dataclass(slots=True)
class CPUMetrics:
    cpu_power: MetricStatistics | None = None
    cpu_utilization: MetricStatistics | None = None
    cpu_temperature: MetricStatistics | None = None


@dataclass(slots=True)
class GPUMetrics:
    vram_usage: MetricStatistics | None = None
    gpu_power: MetricStatistics | None = None
    gpu_utilization: MetricStatistics | None = None
    gpu_temperature: MetricStatistics | None = None


@dataclass(slots=True)
class BenchmarkResult:
    """
    Результат бенчмарка для ОДНОГО кейса (может содержать несколько моделей).
    Используется для агрегированных данных по кейсу.
    """
    case: BenchmarkCase
    performance: LatencyStats | None = None
    cpu: CPUMetrics | None = None
    gpu: GPUMetrics | None = None


@dataclass(slots=True)
class QualityMetrics:
    """Метрики качества модели."""
    recall: float | None = None
    precision: float | None = None
    f1_score: float | None = None
    map50: float | None = None
    map50_95: float | None = None


@dataclass(slots=True)
class ModelBenchmarkResult:
    """
    Результат бенчмарка для ОДНОЙ модели в рамках кейса.
    Используется для детализированных отчётов по моделям.
    """
    model: Dict[str, Any]  # {family, size, task_type, format, quantization}
    status: str = "success"
    error: str | None = None
    performance: LatencyStats | None = None
    cpu: CPUMetrics | None = None
    gpu: GPUMetrics | None = None
    quality: QualityMetrics | None = None
