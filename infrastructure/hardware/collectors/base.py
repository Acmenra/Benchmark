# infrastructure/hardware/collectors/base.py

import logging
from typing import Any
from abc import ABC, abstractmethod

from core.domain.hardware import GPUInfo, CPUInfo
from core.domain.config.system import SystemInfoConfig

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
