from abc import ABC, abstractmethod
from typing import Any

class BaseReporter(ABC):
    """Абстрактный базовый класс (интерфейс) конкретного формата отчета."""

    @abstractmethod
    def report(self, entity: Any) -> None:
        """Записать данные сущности (датакласса) в отчет."""