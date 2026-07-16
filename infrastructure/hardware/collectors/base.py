# infrastructure/hardware/collectors/base.py

import logging

logger = logging.getLogger(__name__)
# потом перенесу в interfaces


from abc import ABC, abstractmethod
from typing import Any

from core.entities.config import SystemInfoConfig
from core.entities.hardware import CPUInfo, GPUInfo

# будет контрактом для cpu и gpu
class BaseCollector(ABC):
    # Если строк кода много - сделать папку GPU и там уже 3 (или больше) файлов, 
    # которые реализуют этот класс (в каждом из этих двух методов создаетмся CPUStaticInfoCollector и он уже прокидывает в return)

    def __init__(self, system_info_config: SystemInfoConfig) -> None:
        self.system_info_config = system_info_config
        # потом при надобности можно еще собирать только определенные метрики 
        # MetricsConfig

    @abstractmethod
    def info(self) -> GPUInfo | CPUInfo:
        ...

    @abstractmethod
    def tmp(self) -> Any:
        ...

    @abstractmethod
    def frq(self) -> Any:
        ...

    @abstractmethod
    def prsnt(self) -> Any:
        ...

    @abstractmethod 
    def get_hardware_info(self) -> ...: 
        """Возвращает статические данные о железе."""

    @abstractmethod
    def get_metrics(self) -> ...:
        """Возвращает метрики во время одного пробега."""


def is_valid_temperature(temp: float) -> bool:
    """Проверка, что значение температуры находится в допустимом диапазоне."""
    return isinstance(temp, (int, float)) and 0 <= temp < 150

