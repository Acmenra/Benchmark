# infrastructure/models/backend.py

from abc import ABC, abstractmethod
from typing import Any


class BaseModelBackend(ABC):
    """Абстрактный базовый класс backend-а инференса модели."""

    def __init__(self, model: Any) -> None:
        self._model = model

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Вернуть имя backend-а."""

    @abstractmethod
    def infer(self, inputs: Any) -> Any:
        """Выполнить инференс."""

    @abstractmethod
    def warmup(self, iterations: int, inputs: Any) -> None:
        """Прогреть модель перед benchmark."""

    @abstractmethod
    def release(self) -> None:
        """Освободить ресурсы backend-а."""