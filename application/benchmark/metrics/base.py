from abc import ABC, abstractmethod

from core.entities.metrics import MetricStatistics


class MetricCollector(ABC):
    """Базовый класс для оркестраторов сборщиков метрик."""
    
    def measure(self) -> MetricStatistics:
        ...

    @abstractmethod
    def collect(self) -> ...:
        """Собрать набор метрик."""

