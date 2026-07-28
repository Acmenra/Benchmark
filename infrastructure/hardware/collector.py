import logging
import socket

from core.domain.hardware.enums import PlatformType
from core.domain.config.system import SystemInfoConfig
from core.domain.system.system import SystemInfo
from infrastructure.hardware.collectors.cpu.collector import CPUCollector
from infrastructure.hardware.collectors.gpu.collector import GPUCollector
from infrastructure.hardware.collectors.ram.collector import RAMCollector  # <-- ДОБАВИЛИ
from infrastructure.hardware.collectors.operating_system import OSCollector
from infrastructure.hardware.collectors.temperature import collect_temperature

logger = logging.getLogger(__name__)


class HardwareCollector:
    """Сборщик статической информации об аппаратном окружении системы."""

    def __init__(self, system_info_config: SystemInfoConfig | None = None) -> None:
        self.system_info_config = system_info_config or SystemInfoConfig(
            collect_cpu=True, collect_gpu=True, collect_power=False, collect_temperature=False
        )
        self.cpu_collector = CPUCollector(self.system_info_config)
        self.gpu_collector = GPUCollector(self.system_info_config)
        self.ram_collector = RAMCollector(self.system_info_config)
        self.os_collector = OSCollector()

    def get_system_info(self) -> SystemInfo:
        cpu_info = self.cpu_collector.get_hardware_info()
        gpu_info = self.gpu_collector.get_hardware_info() if self.system_info_config.collect_gpu else None
        ram_info = self.ram_collector.get_hardware_info()
        os_info = self.os_collector.get_hardware_info()

        temp_capabilities = None
        if self.system_info_config.collect_temperature:
            temp_capabilities = collect_temperature()

        return SystemInfo(
            platform=self.gpu_collector._detect_platform(),
            device_name=socket.gethostname(),
            cpu=cpu_info,
            gpu=gpu_info,
            ram=ram_info,
            npu=None,
            tpu=None,
            os=os_info,
            temperature=temp_capabilities,
        )