from application.benchmark.metrics.base import MetricCollector
from core.entities.metrics import HardwareMetrics


class HardwareMetricsCollector(MetricCollector): # TODO доделать
    def collect(self) -> HardwareMetrics:
        raise NotImplementedError()
    # должен собирать это:
    # cpu_utilization: MetricStatistics | None = None из infrastructure\hardware\collectors\cpu.py get_metrics
    # gpu_utilization: MetricStatistics | None = None этого пока нет
    # ram_usage: MetricStatistics | None = None из infrastructure\hardware\collectors\ram.py
    # vram_usage: MetricStatistics | None = None из infrastructure\hardware\collectors\cpu.py get_metrics тоже тянуть, но пока не реализовано