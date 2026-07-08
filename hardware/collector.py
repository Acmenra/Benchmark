# hardware/collector.py

from config import SystemInfoConfig
from hardware.collectors.cpu import collect_cpu
from hardware.entities import SystemInfo
from hardware.enums import HardwarePlatform
from hardware.collectors.gpu import collect_gpu
from hardware.collectors.operating_system import collect_os


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
        ...
        
        raise NotImplementedError()
    
        return SystemInfo(
            HardwarePlatform.UNKNOWN,
            '',
            cpu=cpu,
            gpu=gpu,
            os=os,
        )