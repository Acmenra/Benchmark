# infrastructure/hardware/collectors/npu/collector.py

import time
import logging

from core.domain.hardware import NPUInfo
from core.domain.config.system import SystemInfoConfig
from core.domain.metrics import MetricStatistics, DataPoint
from infrastructure.hardware.collectors.base import BaseHardwareCollector
from .hailo_worker import HailoWorker

logger = logging.getLogger(__name__)


class NPUCollector(BaseHardwareCollector):
    """Сборщик метрик NPU. Реализует контракт BaseHardwareCollector."""

    def __init__(self, system_info_config: SystemInfoConfig | None = None) -> None:
        super().__init__(system_info_config)
        self._hailo = HailoWorker()
        self._hardware_info = self._gather_static_info()

    def get_hardware_info(self) -> NPUInfo:
        """РЕАЛИЗАЦИЯ АБСТРАКТНОГО МЕТОДА. Возвращает статику."""
        return self._hardware_info

    def get_metrics(self) -> dict[str, MetricStatistics] | None:
        """РЕАЛИЗАЦИЯ АБСТРАКТНОГО МЕТОДА. Возвращает снимок runtime-метрик."""
        if not self._hailo.is_available():
            return None

        metrics = {}
        temp = self._hailo.get_temperature()

        if temp is not None:
            metric = MetricStatistics(unit="celsius")
            metric.history.append(
                DataPoint(
                    time_in_ms=time.perf_counter() * 1000.0,
                    value=temp,
                )
            )
            metrics["temperature"] = metric

        return metrics if metrics else None

    def _gather_static_info(self) -> NPUInfo:
        """Внутренний метод для первичного сбора характеристик NPU."""
        if self._hailo.is_available():
            return self._hailo.get_info()

        return NPUInfo(name=None, architecture=None)