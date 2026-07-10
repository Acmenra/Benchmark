from abc import ABC, abstractmethod


class MetricCollector(ABC):
    """Базовый класс для оркестраторов сборщиков метрик."""
    
    @abstractmethod
    def collect(self) -> ...:
        """Собрать набор метрик."""
