# infrastructure/hardware/collectors/operating_system.py

import logging
import platform

from core.domain.operating_system import OSInfo
from core.domain.config.system import SystemInfoConfig
from infrastructure.hardware.collectors.base import BaseHardwareCollector
from infrastructure.utils.utils import empty_to_none

logger = logging.getLogger(__name__)


class OSCollector(BaseHardwareCollector):
    """
    Сборщик информации об операционной системе.

    Реализует контракт BaseHardwareCollector.
    Не требует system_info_config, так как OS всегда собирается.
    """

    def __init__(self, system_info_config: SystemInfoConfig | None = None) -> None:
        # OS-коллектор не использует конфиг, но принимает его для совместимости
        super().__init__(system_info_config)

    def get_hardware_info(self) -> OSInfo:
        """
        РЕАЛИЗАЦИЯ АБСТРАКТНОГО МЕТОДА.
        Возвращает статическую информацию об операционной системе.
        """
        return OSInfo(
            system=empty_to_none(platform.system()),
            release=empty_to_none(platform.release()),
            kernel=empty_to_none(platform.version()),
            architecture=empty_to_none(platform.machine()),
        )

    def get_metrics(self) -> None:
        """
        ОС не имеет runtime-метрик в контексте бенчмарка.
        Возвращаем None, как определено в базовом классе.
        """
        return None