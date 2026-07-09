from abc import ABC, abstractmethod


class MetricCollector(ABC):
    """Базовый класс для сборщиков метрик."""
    
    @abstractmethod
    def collect(self) -> ...:
        """Собрать набор метрик."""
