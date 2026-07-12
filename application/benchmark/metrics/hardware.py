from application.benchmark.metrics.base import MetricCollector
from core.entities.metrics import HardwareMetrics


class HardwareMetricsCollector(MetricCollector):
    def collect(self) -> HardwareMetrics:
        raise NotImplementedError()
