# core/domain/config/system.py

import logging
from dataclasses import dataclass

from core.domain.config.base import BaseConfig


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class SystemInfoConfig(BaseConfig):
    """
    Configuration for hardware telemetry collection during benchmarking.

    Controls which system-level metrics (CPU, GPU, power, temperature)
    should be sampled and aggregated alongside inference performance metrics.

    Attributes:
        collect_cpu (bool): Enable CPU utilization and frequency monitoring.
        collect_gpu (bool): Enable GPU utilization and VRAM monitoring.
        collect_power (bool): Enable power consumption tracking (if hardware supports it).
        collect_temperature (bool): Enable thermal sensor reading (if hardware supports it).

    Note:
        - Some metrics (like power and temperature) depend on specific hardware
          capabilities and OS-level permissions. The collector will gracefully
          degrade if a sensor is unavailable.
        - High-frequency sampling may introduce minor overhead; enable only
          when detailed hardware profiling is required.
    """
    collect_cpu: bool
    collect_gpu: bool
    collect_power: bool
    collect_temperature: bool