# application/benchmark/metrics/base.py

from abc import ABC, abstractmethod

from core.entities.metrics import MetricStatistics


class MetricCollector(ABC):
    """Базовый класс для оркестраторов сборщиков метрик."""

    @abstractmethod
    def start(self) -> ...:
        """Собрать набор метрик."""

    @abstractmethod
    def stop(self) -> ...:
        """Собрать набор метрик."""

    @abstractmethod
    def get(self) -> ...:
        """Собрать набор метрик."""