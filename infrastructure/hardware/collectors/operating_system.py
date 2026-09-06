# infrastructure/hardware/collectors/operating_system.py

import logging
import platform
from typing import Optional

from core.domain.operating_system import OSInfo
from core.domain.config.system import SystemInfoConfig
from infrastructure.hardware.collectors.base import BaseHardwareCollector
from infrastructure.utils.utils import empty_to_none

logger = logging.getLogger(__name__)


class OSCollector(BaseHardwareCollector):
    """
    Concrete implementation for Operating System metadata extraction.

    This collector implements the `BaseHardwareCollector` contract but ignores
    the `system_info_config` because OS data is unconditionally required for
    the benchmark report header.
    """

    def __init__(self, system_info_config: Optional[SystemInfoConfig] = None) -> None:
        """
        Initializes the OS collector.

        Args:
            system_info_config: Accepted for interface compatibility but ignored,
                                as OS data is always collected.
        """
        super().__init__(system_info_config)

    def get_hardware_info(self) -> OSInfo:
        """
        Retrieves static information about the host Operating System.

        Uses Python's built-in `platform` module to extract OS name, release,
        kernel version, and architecture. Sanitizes empty strings to `None`
        to ensure clean domain data.

        Returns:
            OSInfo: An immutable dataclass populated with OS metadata.
        """
        return OSInfo(system=empty_to_none(platform.system()),
                      release=empty_to_none(platform.release()),
                      kernel=empty_to_none(platform.version()),
                      architecture=empty_to_none(platform.machine()))

    def get_metrics(self) -> None:
        """
        Returns `None` as the OS does not have runtime inference metrics.

        In the context of the benchmark suite, we do not poll OS-level dynamic
        metrics during the inference loop.
        """
        return None