from application.benchmark.metrics.base import MetricCollector
from core.entities.metrics import PerformanceMetrics


class PerformanceMetricsCollector(MetricCollector):
    def collect(self) -> PerformanceMetrics:
        raise NotImplementedError()
