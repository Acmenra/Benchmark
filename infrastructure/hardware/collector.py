# infrastructure/hardware/collector.py

import logging

from core.entities.config import SystemInfoConfig
from core.entities.hardware import SystemInfo
from core.enums.hardware import PlatformType
from infrastructure.hardware.collectors.cpu import collect_cpu
from infrastructure.hardware.collectors.gpu import collect_gpu
from infrastructure.hardware.collectors.operating_system import collect_os
from infrastructure.hardware.collectors.temperature import collect_temperature

logger = logging.getLogger(__name__)


class HardwareCollector:
    """Сборщик информации об аппаратном окружении системы.

    Класс отвечает за координацию сбора характеристик устройства:
    процессора, графического процессора, операционной системы и других
    аппаратных компонентов.

    Attributes:
        system_info_config (SystemInfoConfig):
            Конфигурация сбора информации о системе.
            Определяет, какие компоненты необходимо собирать.
    """

    def __init__(self, system_info_config: SystemInfoConfig) -> None:
        self.system_info_config = system_info_config

    def get_system_info(self) -> SystemInfo:
        cpu = collect_cpu()
        gpu = collect_gpu() if self.system_info_config.collect_gpu else None
        os_info = collect_os()
        temperature = (
            collect_temperature()
            if self.system_info_config.collect_temperature
            else None
        )

        return SystemInfo(
            platform=PlatformType.UNKNOWN,
            device_name=None,
            cpu=cpu,
            gpu=gpu,
            os=os_info,
            temperature=temperature,
        )
