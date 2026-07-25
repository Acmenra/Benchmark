# infrastructure/hardware/collector.py

import logging

from core.domain.system.system import SystemInfo
from core.domain.hardware.enums import PlatformType
from core.domain.config.system import SystemInfoConfig
from infrastructure.hardware.collectors.cpu import CPUCollector
from infrastructure.hardware.collectors.gpu import GPUCollector
from infrastructure.hardware.collectors.operating_system import OSCollector
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
        self.cpu_collector = CPUCollector()
        self.gpu_collector = GPUCollector()
        self.os_collector = OSCollector()

    def get_system_info(self) -> SystemInfo:
        cpu = self.cpu_collector.collect()
        gpu = self.gpu_collector.collect() if self.system_info_config.collect_gpu else None
        os_info = self.os_collector.collect()
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
            npu=None,
            tpu=None,
            os=os_info,
            temperature=temperature,
        )
