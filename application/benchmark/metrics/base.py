# application/benchmark/metrics/base.py

import logging
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class BaseMetricsCollector(ABC):
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