# infrastructure/hardware/collectors/base.py

import logging
from abc import ABC, abstractmethod
from typing import Any

from core.entities.config import SystemInfoConfig
from core.entities.hardware import CPUInfo, GPUInfo

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    def __init__(self, system_info_config: SystemInfoConfig) -> None:
        self.system_info_config = system_info_config

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
