from application.benchmark.metrics.base import MetricCollector
from core.entities.metrics import PowerMetrics


class PowerMetricsCollector(MetricCollector): # TODO доделать
    def collect(self) -> PowerMetrics:
        raise NotImplementedError()

