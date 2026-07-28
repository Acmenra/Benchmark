"""
Сборщик метрик GPU. Реализует контракт BaseHardwareCollector.
Делегирует работу конкретным воркерам (NVML, SMI, MPS).
"""

import time
import logging
import platform
from pathlib import Path

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
    Сборщик метрик GPU. Реализует контракт BaseHardwareCollector.

    Использует цепочку fallback: NVML -> SMI -> MPS.
    Первый доступный воркер предоставляет данные.
    """

    def __init__(self, system_info_config: SystemInfoConfig) -> None:
        super().__init__(system_info_config)

        # Инициализируем всех возможных воркеров.
        # Они легкие и сами определят свою доступность.
        self._nvml = NVMLWorker()
        self._smi = SMIWorker()
        self._mps = MPSWorker()

        self._platform_type = self._detect_platform()

    def get_hardware_info(self) -> GPUInfo:
        """
        РЕАЛИЗАЦИЯ АБСТРАКТНОГО МЕТОДА.
        Возвращает статическую информацию о GPU (цепочка fallback: NVML -> SMI -> MPS).
        """
        if self._nvml.is_available():
            return self._nvml.get_info()
        if self._smi.is_available():
            return self._smi.get_info()
        if self._mps.is_available():
            return self._mps.get_info()

        # Если ничего не найдено
        return GPUInfo(name=None, memory_mb=None, driver_version=None, cuda_version=None)

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

    def _build_metric(self, value: float | int | None, unit: str) -> MetricStatistics | None:
        """Оборачивает сырое значение в MetricStatistics с DataPoint."""
        if value is None:
            return None

        metric = MetricStatistics(unit=unit)
        metric.history.append(
            DataPoint(
                time_in_ms=time.perf_counter() * 1000.0,
                value=float(value),
            )
        )
        return metric

    def _detect_platform(self) -> PlatformType:
        """Определить аппаратную платформу по доступным локальным признакам."""
        # Сначала проверяем macOS, так как /proc/device-tree/model там не существует
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