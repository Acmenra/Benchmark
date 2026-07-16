# application/benchmark/reporter/base.py

from abc import ABC, abstractmethod
from typing import Any

class BaseReporter(ABC):
    """Абстрактный базовый класс для репортеров конкретных форматов."""

    @abstractmethod
    def report(self, data: Any) -> None:
        """Записать данные (одиночную сущность или список) в отчёт."""
        pass