# application/benchmark/metrics/cpu.py

import logging

logger = logging.getLogger(__name__)

from application.benchmark.metrics.base import MetricCollector
from core.entities.metrics import CPUMetrics


class CPUMetricsCollector(MetricCollector): # TODO доделать
    def __init__(self) -> None:
        super().__init__()
        
    def start(self) -> None:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()
    
    def get(self) -> CPUMetrics:
        return CPUMetrics()
    # TODO 

    # должен собирать это: тянуть из абстрактного класса c infrastructure\hardware\collectors\cpu.py
    # cpu_power: MetricStatistics
    # cpu_utilization: MetricStatistics
    # cpu_temperature: MetricStatistics

    # при  d