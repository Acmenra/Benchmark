# infrastructure/hardware/collectors/base.py

import logging
from abc import ABC, abstractmethod
from typing import Union, Optional

from core.domain.hardware import CPUInfo, GPUInfo, NPUInfo, TPUInfo, RAMInfo
from core.domain.operating_system import OSInfo
from core.domain.config.system import SystemInfoConfig
from core.domain.metrics import MetricStatistics

logger = logging.getLogger(__name__)


HardwareInfoType = Union[CPUInfo, GPUInfo, NPUInfo, TPUInfo, RAMInfo, OSInfo, None]


class BaseHardwareCollector(ABC):
    """
    Abstract base class defining the contract for all system component collectors.

    This class establishes the minimal interface that concrete implementations
    (CPU, GPU, RAM, OS, etc.) must fulfill. It separates the concerns of static
    hardware characterization from dynamic runtime telemetry.

    Key design decisions:
    - Static info (`get_hardware_info`) is gathered once and cached.
    - Dynamic metrics (`get_metrics`) are polled periodically and must be fast.
    - Graceful degradation: Collectors should never crash the suite if hardware
      is missing; they should return `None` or empty dataclasses.
    """

    def __init__(self,
                 system_info_config: Optional[SystemInfoConfig] = None) -> None:
        """
        Initializes the base collector with optional telemetry configuration.

        Args:
            system_info_config: Configuration flags controlling which metrics to collect.
                                Can be `None` for collectors that always run (e.g., OS).
        """
        self.system_info_config = system_info_config

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

    @abstractmethod
    def get_hardware_info(self) -> HardwareInfoType:
        """
        Retrieves the STATIC hardware specifications for the component.

        This method is called exactly once at the start of the benchmark suite.
        Implementations should perform any heavy OS-level probing here and cache
        the result, ensuring subsequent calls are O(1) and non-blocking.

        Returns:
            HardwareInfoType: An immutable domain dataclass (e.g., `CPUInfo`, `GPUInfo`)
                              populated with static specs, or `None` if the component
                              is not detected.
        """
        pass

    def get_metrics(self) -> MetricStatistics | dict[str, MetricStatistics] | None:
        """
        Captures a snapshot of DYNAMIC (runtime) metrics for the component.

        This method is invoked periodically from a background thread during the
        inference loop. It must be extremely fast and non-blocking (< 50ms).

        Returns:
            - `MetricStatistics`: If the collector measures a single metric (e.g., CPU utilization).
            - `dict[str, MetricStatistics]`: If it measures multiple metrics (e.g., GPU temp, VRAM).
            - `None`: If the component does not support dynamic metrics (e.g., OS, static RAM).

        Note:
            The default implementation returns `None`. Subclasses should override
            this only if they have dynamic telemetry to report.
        """
        return None

    def is_available(self) -> bool:
        """
        Heuristically checks if the component is accessible on the current machine.

        This method is used by the orchestrator to determine if a collector should
        be included in the telemetry pipeline. It safely catches exceptions to
        prevent missing drivers or libraries from crashing the initialization.

        Returns:
            bool: `True` if the component is detected and ready, `False` otherwise.
        """
        try:
            return self.get_hardware_info() is not None
        except Exception as e:
            logger.debug("Компонент %s недоступен: %s", self.__class__.__name__, e)
            return False
