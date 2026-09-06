# infrastructure/hardware/collectors/ram/collector.py

import logging
import platform
import subprocess
from typing import Optional

from core.domain.hardware.ram_info import RAMInfo
from core.domain.config.system import SystemInfoConfig
from infrastructure.hardware.collectors.base import BaseHardwareCollector


logger = logging.getLogger(__name__)


class RAMCollector(BaseHardwareCollector):
    """
    Concrete implementation for static RAM data gathering.

    This collector focuses exclusively on static characterization. It caches
    the total memory capacity and attempts to identify the memory type
    (e.g., Unified Memory, LPDDR) using OS-specific heuristics.
    """

    def __init__(self,
                 system_info_config: Optional[SystemInfoConfig] = None) -> None:
        """
        Initializes the RAM collector and pre-computes static hardware info.

        Args:
            system_info_config: Configuration flags for telemetry collection.
        """
        super().__init__(system_info_config)
        self._hardware_info = self._gather_static_info()

    def get_hardware_info(self) -> RAMInfo:
        """
        Returns the pre-computed, cached static RAM specifications.

        Returns:
            RAMInfo: An immutable dataclass containing total MB and memory type.
        """
        return self._hardware_info

    def _gather_static_info(self) -> RAMInfo:
        """
        Orchestrates the collection of static RAM metadata.

        Uses `psutil` for total capacity and delegates memory type detection
        to the `_get_ram_type()` heuristic method.

        Returns:
            RAMInfo: A fully populated RAM information dataclass.
        """
        total_mb = None
        ram_type = None

        try:
            import psutil
            mem = psutil.virtual_memory()
            total_mb = int(mem.total / (1024 ** 2))
        except ImportError:
            logger.warning("Модуль psutil не установлен, объем RAM определить не удалось.")

        ram_type = self._get_ram_type()

        return RAMInfo(total_mb=total_mb,
                       type=ram_type,
                       speed_mhz=None)

    def _get_ram_type(self) -> Optional[str]:
        """
        Attempts to identify the RAM type using OS-specific heuristics.

        Resolution order:
        1. macOS: Explicitly returns "Unified Memory" (Apple Silicon).
        2. Linux (Edge): Parses `/proc/device-tree/model` to detect Raspberry Pi
           or NVIDIA Jetson, returning "LPDDR" for these architectures.
        3. Fallback: Returns `None` for standard desktop Linux/Windows where
           generic DDR type detection requires privileged access.

        Returns:
            str | None: The identified memory type, or `None` if undetermined.
        """
        system = platform.system()

        if system == "Darwin":
            return "Unified Memory"

        elif system == "Linux":
            try:
                model = subprocess.run(
                    ["cat", "/proc/device-tree/model"],
                    capture_output=True, text=True, timeout=2
                ).stdout.strip().lower()

                if "raspberry" in model:
                    return "LPDDR"
                elif "jetson" in model or "orin" in model:
                    return "LPDDR"
            except Exception:
                pass

        return None

    def get_metrics(self) -> None:
        """
        Returns `None` as dynamic RAM usage is handled separately.

        Note:
            In the current benchmark context, this collector is strictly
            responsible for static hardware characterization. Dynamic memory
            polling (if required) is managed by a separate utility.
        """
        return None