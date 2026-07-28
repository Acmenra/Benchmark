"""
Базовый модуль для всех сборщиков метрик железа.

Определяет строгий контракт (интерфейс), который должны реализовывать
все конкретные сборщики (CPU, GPU, NPU, OS и т.д.).
"""

import logging
from abc import ABC, abstractmethod
from typing import Union

from core.domain.hardware import CPUInfo, GPUInfo, NPUInfo, TPUInfo, RAMInfo
from core.domain.operating_system import OSInfo
from core.domain.config.system import SystemInfoConfig
from core.domain.metrics import MetricStatistics

logger = logging.getLogger(__name__)

# Объединенный тип для статической информации от любого коллектора
HardwareInfoType = Union[CPUInfo, GPUInfo, NPUInfo, TPUInfo, RAMInfo, OSInfo, None]


class BaseHardwareCollector(ABC):
    """
    Абстрактный базовый класс для сборщиков информации о компонентах системы.

    Этот класс задает минимальный контракт. Конкретные реализации могут
    добавлять свои специфичные методы (например, get_temperature), но
    обязаны реализовать эти два базовых.
    """

    def __init__(self, system_info_config: SystemInfoConfig | None = None) -> None:
        """
        Инициализация коллектора.

        Args:
            system_info_config: Конфигурация сбора. Может быть None, если
                                коллектору не нужны флаги включения/выключения.
        """
        self.system_info_config = system_info_config

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

    @abstractmethod
    def get_hardware_info(self) -> HardwareInfoType:
        """
        Возвращает СТАТИЧЕСКУЮ информацию о компоненте.

        Вызывается один раз при старте бенчмарка. Не должен содержать
        тяжелых или блокирующих операций, кроме первоначального опроса системы.

        Returns:
            Экземпляр соответствующего Info-класса (CPUInfo, GPUInfo, OSInfo и т.д.)
            или None, если компонент не обнаружен или информация недоступна.
        """
        pass

    def get_metrics(self) -> MetricStatistics | dict[str, MetricStatistics] | None:
        """
        Возвращает снимок ДИНАМИЧЕСКИХ (runtime) метрик компонента.

        Вызывается периодически в фоновом потоке во время инференса.
        Должен быть максимально быстрым и неблокирующим (< 50 мс).

        Returns:
            - MetricStatistics: если коллектор измеряет одну метрику (напр., CPU utilization).
            - dict[str, MetricStatistics]: если метрик несколько (напр., GPU: temp, vram, util).
            - None: если компонент не поддерживает динамические метрики (напр., OSCollector).

        Note:
            По умолчанию возвращает None. Переопределяется только там, где нужно.
        """
        return None

    def is_available(self) -> bool:
        """
        Проверяет, доступен ли компонент для сбора данных на текущей машине.

        Можно переопределить в наследниках для более сложной логики проверки.
        """
        try:
            return self.get_hardware_info() is not None
        except Exception as e:
            logger.debug("Компонент %s недоступен: %s", self.__class__.__name__, e)
            return False
