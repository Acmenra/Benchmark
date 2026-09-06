# infrastructure/hardware/collectors/npu/collector.py

import time
import logging
from typing import Optional

from core.domain.hardware import NPUInfo
from core.domain.config.system import SystemInfoConfig
from core.domain.metrics import MetricStatistics, DataPoint
from infrastructure.hardware.collectors.base import BaseHardwareCollector
from .hailo_worker import HailoWorker


logger = logging.getLogger(__name__)


class NPUCollector(BaseHardwareCollector):
    """
    Concrete implementation of the NPU data and telemetry gathering contract.

    This collector orchestrates specialized workers to extract NPU metadata
    and runtime metrics. It guarantees graceful degradation by returning empty
    or `None` values if the specific hardware is not detected.

    Key design decisions:
    - Static info is gathered exactly once during initialization.
    - Dynamic metrics use `time.perf_counter()` for monotonic, high-precision timestamping.
    - Delegates OS-specific logic to self-contained Worker classes.
    """

    def __init__(self, system_info_config: Optional[SystemInfoConfig] = None) -> None:
        """
        Initializes the NPU collector and pre-computes static hardware info.

        Args:
            system_info_config: Configuration flags for telemetry collection.
        """
        super().__init__(system_info_config)
        self._hailo = HailoWorker()
        self._hardware_info = self._gather_static_info()

    def get_hardware_info(self) -> NPUInfo:
        """
        Returns the pre-computed, cached static NPU specifications.

        Returns:
            NPUInfo: An immutable dataclass containing the NPU name and host architecture,
                     or an empty NPUInfo if no compatible accelerator is detected.
        """
        return self._hardware_info

    def get_metrics(self) -> dict[str, MetricStatistics] | None:
        """
        Captures a single snapshot of the current NPU runtime metrics.

        Queries the active worker for available telemetry (currently limited to temperature).

        Returns:
            dict[str, MetricStatistics] | None: A dictionary containing the NPU metrics
                                                (e.g., 'temperature'), or `None` if the
                                                NPU is not available or no metrics can be read.
        """
        if not self._hailo.is_available():
            return None

        metrics = {}
        temp = self._hailo.get_temperature()

        if temp is not None:
            metric = MetricStatistics(unit="celsius")
            metric.history.append(DataPoint(time_in_ms=time.perf_counter() * 1000.0,
                                            value=temp)
                                  )
            metrics["temperature"] = metric

        return metrics if metrics else None

    def _gather_static_info(self) -> NPUInfo:
        """
        Internal method for initial NPU characteristic gathering.

        Returns:
            NPUInfo: Populated static info from the worker, or an empty NPUInfo fallback.
        """
        if self._hailo.is_available():
            return self._hailo.get_info()

        return NPUInfo(name=None,
                       architecture=None)