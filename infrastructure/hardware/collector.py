# infrastructure/hardware/collector.py

import socket
import logging
from typing import Optional

from core.domain.system.system import SystemInfo
from core.domain.config.system import SystemInfoConfig
from infrastructure.hardware.collectors.cpu.collector import CPUCollector
from infrastructure.hardware.collectors.gpu.collector import GPUCollector
from infrastructure.hardware.collectors.ram.collector import RAMCollector
from infrastructure.hardware.collectors.operating_system import OSCollector
from infrastructure.hardware.collectors.tmp.collector import collect_temperature

logger = logging.getLogger(__name__)


class HardwareCollector:
    """
    Facade for assembling the complete SystemInfo aggregate.

    This class orchestrates the collection of static hardware and OS metadata
    by delegating to specialized sub-collectors. It ensures that the application
    layer receives a fully populated, type-safe `SystemInfo` domain object,
    completely abstracting away the complexities of cross-platform API calls.

    Key design decisions:
    - Zero-overhead execution: All data gathering is performed during initialization
      or the first call to `get_system_info()`.
    - Graceful degradation: If a specific sub-collector fails or is disabled via
      configuration, the orchestrator safely substitutes `None` without crashing.
    - Domain isolation: Raw system calls are confined to the sub-collectors;
      this class only handles aggregation.
    """
    def __init__(self,
                 system_info_config: Optional[SystemInfoConfig] = None) -> None:
        """
        Initializes the hardware orchestrator and instantiates all sub-collectors.

        The sub-collectors are initialized eagerly to allow them to perform any
        necessary one-time OS-level probing or caching.

        Args:
            system_info_config: Configuration flags controlling which metrics to collect.
                                Defaults to a standard configuration if not provided.
        """
        self.system_info_config = system_info_config or SystemInfoConfig(collect_cpu=True,
                                                                         collect_gpu=True,
                                                                         collect_power=False,
                                                                         collect_temperature=False)

        self.cpu_collector = CPUCollector(self.system_info_config)
        self.gpu_collector = GPUCollector(self.system_info_config)
        self.ram_collector = RAMCollector(self.system_info_config)
        self.os_collector = OSCollector()

    def get_system_info(self) -> SystemInfo:
        """
        Assembles and returns the complete static system profile.

        Queries each enabled sub-collector for its cached static information,
        probes thermal capabilities if configured, and aggregates everything
        into a single, immutable `SystemInfo` domain object.

        Returns:
            SystemInfo: A comprehensive, immutable dataclass containing CPU, GPU,
                        RAM, OS, platform, and thermal capability metadata.

        Note:
            - The `platform` field is heuristically determined by the GPU collector.
            - The `device_name` is retrieved via the standard `socket.gethostname()`.
            - NPU and TPU fields are currently initialized to `None`, reserving the
              schema for future edge-accelerator expansions without breaking the API.
        """
        cpu_info = self.cpu_collector.get_hardware_info()
        gpu_info = self.gpu_collector.get_hardware_info() if self.system_info_config.collect_gpu else None
        ram_info = self.ram_collector.get_hardware_info()
        os_info = self.os_collector.get_hardware_info()

        temp_capabilities = None
        if self.system_info_config.collect_temperature:
            temp_capabilities = collect_temperature()

        return SystemInfo(platform=self.gpu_collector._detect_platform(),
                          device_name=socket.gethostname(),
                          cpu=cpu_info,
                          gpu=gpu_info,
                          npu=None,
                          tpu=None,
                          ram=ram_info,
                          os=os_info,
                          temperature=temp_capabilities)