# core/entities/metrics.py

import logging

logger = logging.getLogger(__name__)

from dataclasses import dataclass

from core.entities.config import BenchmarkRun

# TODO не плохо было бы знать для каждой из метрик её минимальное, медианное, среднее и максимальное значение
# TODO тогда можно будет "собрать" любую таблицу

# TODO ljk;ty
@dataclass
class DataPoint: # TODO значение чего-либо в данную ms
    time_in_ms: int
    value: float | int


class MetricStatistics: # TODO сделать очередью, которая за O(1) пересчитывает значения
    def __init__(self, unit: str | None = None) -> None: # TODO определить, что по итогу оно принимает это: "unit: str | None = None" или это: "DataPoint"
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
class PerformanceMetrics:
    fps: MetricStatistics | None = None # среднее?
    latency: MetricStatistics | None = None


# @dataclass(slots=True)
# class HardwareMetrics:
#     cpu_utilization: MetricStatistics | None = None
#     gpu_utilization: MetricStatistics | None = None
#     ram_usage: MetricStatistics | None = None
#     vram_usage: MetricStatistics | None = None
#     ...



# @dataclass(slots=True)
# class PowerMetrics:
#     cpu_power: MetricStatistics | None = None
#     gpu_power: MetricStatistics | None = None
#     system_power: MetricStatistics | None = None


# @dataclass(slots=True)
# class TemperatureMetrics:
#     cpu_temperature: MetricStatistics | None = None
#     gpu_temperature: MetricStatistics | None = None


class CPUMetrics:
    cpu_power: MetricStatistics
    cpu_utilization: MetricStatistics
    cpu_temperature: MetricStatistics

class GPUMetrics:
    vram_usage: MetricStatistics
    gpu_power: MetricStatistics
    gpu_utilization: MetricStatistics
    gpu_temperature: MetricStatistics

# @dataclass(slots=True) БЫЛО
# class BenchmarkResult:
#     case: BenchmarkRun
#     performance: PerformanceMetrics | None = None
#     hardware: HardwareMetrics | None = None
#     power: PowerMetrics | None = None
#     temperature: TemperatureMetrics | None = None

@dataclass(slots=True)
class BenchmarkResult:
    case: BenchmarkRun
    gpu: CPUMetrics | None = None
    cpu: GPUMetrics | None = None
    # ram_usage Сделаем, когда случится первый прогон