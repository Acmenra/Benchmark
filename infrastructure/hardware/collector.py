# infrastructure/hardware/collector.py

from configs.config import SystemInfoConfig
from infrastructure.hardware.collectors.cpu import collect_cpu
from core.entities.hardware import SystemInfo
from core.enums.hardware import PlatformType
from infrastructure.hardware.collectors.gpu import collect_gpu
from infrastructure.hardware.collectors.operating_system import collect_os
from infrastructure.hardware.collectors.temperature import collect_temperature


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
        cpu = collect_cpu() if ... else None
        gpu = collect_gpu() if self.system_info_config.collect_gpu else None
        os = collect_os() if ... else None
        temperature = collect_temperature() if self.system_info_config.collect_temperature else None
        ...
        
        raise NotImplementedError()
    
        return SystemInfo(
            platform=PlatformType.UNKNOWN,
            device_name='',
            cpu=cpu,
            gpu=gpu,
            os=os,
            temperature=temperature,
        )