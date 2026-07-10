# infrastucture/models/loader.py

from abc import ABC, abstractmethod
from typing import Any


class BaseModelLoader(ABC):
    """Абстрактный базовый класс загрузчика модели."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Вернуть имя формата загрузчика."""

    @abstractmethod
    def load(self) -> Any:
        """Загрузить модель или исполняемый движок в память."""

    @abstractmethod
    def unload(self) -> None:
        """Освободить ресурсы, занятые загруженной моделью."""
        # потом можно еще запоминать если модель будет использована снова, и не очищать
