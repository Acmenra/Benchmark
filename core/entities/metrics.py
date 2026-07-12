from dataclasses import dataclass

# TODO не плохо было бы знать для каждой из метрик её минимальное, медианное, среднее и максимальное значение
# TODO тогда можно будет "собрать" любую таблицу


@dataclass
class DataPoint:
    time_in_ms: int
    value: float | int


class MetricStatistics:
    def __init__(self, unit: str | None = None) -> None:
        self.history: list[DataPoint] = []
        self.unit: str | None = unit

    @property
    def minimum(self):
        ...

    @property
    def maximum(self):
        ...

    @property
    def mean(self):
        ...
    
    @property
    def median(self):
        ...

    @property
    def p95(self):
        ...

    @property
    def p99(self):
        ...

    @property
    def p50(self):
        ...


@dataclass(slots=True)
class PerformanceMetrics:
    fps: MetricStatistics | None = None
    latency: MetricStatistics | None = None


@dataclass(slots=True)
class HardwareMetrics:
    cpu_utilization: MetricStatistics | None = None
    gpu_utilization: MetricStatistics | None = None
    ram_usage: MetricStatistics | None = None
    vram_usage: MetricStatistics | None = None
    ...


@dataclass(slots=True)
class PowerMetrics:
    cpu_power: MetricStatistics | None = None
    gpu_power: MetricStatistics | None = None
    system_power: MetricStatistics | None = None


@dataclass(slots=True)
class TemperatureMetrics:
    cpu_temperature: MetricStatistics | None = None
    gpu_temperature: MetricStatistics | None = None

#Заглушка (потом создать рядом файл config, из config.py перенести туда все сущности)
class BenchmarkRun: ...

@dataclass(slots=True)
class BenchmarkResult:
    case: BenchmarkRun
    performance: PerformanceMetrics | None = None
    hardware: HardwareMetrics | None = None
    power: PowerMetrics | None = None
    # TemperatureMetrics
