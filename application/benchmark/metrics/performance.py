from application.benchmark.metrics.base import MetricCollector
from core.entities.metrics import PerformanceMetrics


class PerformanceMetricsCollector(MetricCollector): # TODO доделать
    def collect(self) -> PerformanceMetrics:
        raise NotImplementedError()
    # cpu_power: MetricStatistics | None = None
    # gpu_power: MetricStatistics | None = None
    # system_power: MetricStatistics | None = None