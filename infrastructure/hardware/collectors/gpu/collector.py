# infrastructure/hardware/collectors/gpu/collector.py

import time
import logging
import platform
from pathlib import Path
from typing import Optional

from core.domain.hardware import GPUInfo
from core.domain.hardware.enums import PlatformType
from core.domain.config.system import SystemInfoConfig
from core.domain.metrics import MetricStatistics, DataPoint
from infrastructure.hardware.collectors.base import BaseHardwareCollector
from infrastructure.hardware.collectors.gpu.mps_worker import MPSWorker
from infrastructure.hardware.collectors.gpu.nvml_worker import NVMLWorker
from infrastructure.hardware.collectors.gpu.smi_worker import SMIWorker
from infrastructure.utils.utils import read_text

logger = logging.getLogger(__name__)


class GPUCollector(BaseHardwareCollector):
    """
    Concrete implementation of the GPU data and telemetry gathering contract.

    This collector orchestrates a prioritized chain of specialized workers to
    extract GPU metadata and runtime metrics. It guarantees graceful degradation
    across Windows, Linux, and macOS by falling back from high-performance APIs
    to CLI tools, and finally to platform-specific adapters.

    Key design decisions:
    - Workers (NVML, SMI, MPS) are initialized eagerly but self-determine their
      availability, keeping the overhead of `is_available()` checks minimal.
    - The fallback chain (NVML -> SMI -> MPS) is evaluated identically for both
      static info and dynamic metrics, ensuring consistency.
    """

    def __init__(self,
                 system_info_config: SystemInfoConfig) -> None:
        """
        Initializes the GPU collector and instantiates all potential hardware workers.

        The workers are lightweight and will silently fail to initialize if their
        underlying dependencies (e.g., `pynvml`, `nvidia-smi`) are missing.

        Args:
            system_info_config: Configuration flags for telemetry collection.
        """
        super().__init__(system_info_config)

        self._nvml = NVMLWorker()
        self._smi = SMIWorker()
        self._mps = MPSWorker()

        self._platform_type = self._detect_platform()

    def get_hardware_info(self) -> GPUInfo:
        """
        Returns the static hardware specifications of the GPU.

        Executes a prioritized fallback chain to retrieve GPU metadata:
        1. NVMLWorker (high-performance Python bindings for NVIDIA).
        2. SMIWorker (CLI fallback via `nvidia-smi`).
        3. MPSWorker (Apple Silicon adapter).

        Returns:
            GPUInfo: An immutable dataclass containing GPU name, VRAM, and driver info.
                     Returns an empty `GPUInfo` (all fields `None`) if no GPU is detected.
        """
        if self._nvml.is_available():
            return self._nvml.get_info()
        if self._smi.is_available():
            return self._smi.get_info()
        if self._mps.is_available():
            return self._mps.get_info()

        return GPUInfo(name=None,
                       memory_mb=None,
                       driver_version=None,
                       cuda_version=None)

    # def get_metrics(self) -> GPUMetrics:
    #     """
    #     РЕАЛИЗАЦИЯ АБСТРАКТНОГО МЕТОДА.
    #     Возвращает снимок runtime-метрик GPU.
    #     """
    #     # Выбираем активный воркер по тому же приоритету
    #     active_worker = None
    #     if self._nvml.is_available():
    #         active_worker = self._nvml
    #     elif self._smi.is_available():
    #         active_worker = self._smi
    #     elif self._mps.is_available():
    #         active_worker = self._mps
    #
    #     if active_worker:
    #         return GPUMetrics(
    #             vram_usage=self._build_metric(active_worker.get_memory_used_mb(), "megabyte"),
    #             gpu_power=self._build_metric(active_worker.get_power_watts(), "watt"),
    #             gpu_utilization=self._build_metric(active_worker.get_utilization(), "percent"),
    #             gpu_temperature=self._build_metric(active_worker.get_temperature(), "celsius"),
    #         )
    #
    #     # Если GPU не найден или не поддерживается, возвращаем пустые метрики
    #     return GPUMetrics(
    #         vram_usage=None,
    #         gpu_power=None,
    #         gpu_utilization=None,
    #         gpu_temperature=None,
    #     )

    def _build_metric(self,
                      value: float | int | None,
                      unit: str) -> Optional[MetricStatistics]:
        """
        Wraps a raw numeric value into a MetricStatistics container.

        Uses `time.perf_counter()` for the timestamp to ensure high-resolution,
        monotonic timing that is immune to system clock adjustments.

        Args:
            value: The raw metric value (e.g., temperature in Celsius).
            unit: The unit of measurement (e.g., 'celsius', 'percent').

        Returns:
            MetricStatistics | None: A populated metric container, or `None` if the
                                     input value is `None`.
        """
        if value is None:
            return None

        metric = MetricStatistics(unit=unit)
        metric.history.append(DataPoint(time_in_ms=time.perf_counter() * 1000.0,
                                        value=float(value)
                                        )
                              )
        return metric

    def _detect_platform(self) -> PlatformType:
        """
        Heuristically determines the underlying hardware platform.

        Inspects OS-specific markers (e.g., `/proc/device-tree/model` on Linux,
        `/etc/nv_tegra_release` for Jetson) to classify the device. This classification
        is used by the root `HardwareCollector` to populate the `SystemInfo` aggregate.

        Returns:
            PlatformType: The identified platform (e.g., DESKTOP, JETSON, RASPBERRY_PI).
                          Defaults to `UNKNOWN` if no specific markers are found.
        """
        if platform.system() == "Darwin":
            return PlatformType.DESKTOP

        device_model = read_text(Path("/proc/device-tree/model")).lower()

        if "raspberry pi" in device_model:
            return PlatformType.RASPBERRY_PI
        if "jetson" in device_model or "orin" in device_model or Path("/etc/nv_tegra_release").exists():
            return PlatformType.JETSON
        if "intel nuc" in device_model:
            return PlatformType.INTEL_NUC
        if "hailo" in device_model:
            return PlatformType.HAILO
        if "orange pi" in device_model:
            return PlatformType.UNKNOWN

        system = platform.system()
        if system in {"Windows", "Linux"}:
            return PlatformType.DESKTOP

        return PlatformType.UNKNOWN