# application/benchmark/reporter/base.py

import logging
from typing import Any
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class BaseReporter(ABC):
    """Абстрактный базовый класс для репортеров конкретных форматов."""

    @abstractmethod
    def report(self, data: Any) -> None:
        """Записать данные (одиночную сущность или список) в отчёт."""
        pass