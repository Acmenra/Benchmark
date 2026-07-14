# application/benchmark/metrics/gpu.py

import logging
import threading

from application.benchmark.metrics.base import MetricCollector
from core.entities.config import SystemInfoConfig
from core.entities.metrics import GPUMetrics, MetricStatistics
from infrastructure.hardware.collectors.gpu import GPUCollector

logger = logging.getLogger(__name__)


class GPUMetricsCollector(MetricCollector):
    """Фоновый сборщик runtime-метрик GPU для одного benchmark-прогона."""

    def __init__(
        self,
        interval_seconds: float = 1.0,
        gpu_collector: GPUCollector | None = None,
    ) -> None:
        super().__init__()
        if interval_seconds <= 0:
            raise ValueError("interval_seconds должен быть больше 0")

        self.interval_seconds = interval_seconds
        self.gpu_collector = gpu_collector or GPUCollector(
            SystemInfoConfig(
                collect_gpu=True,
                collect_power=True,
                collect_temperature=True,
            )
        )
        self._vram_usage = MetricStatistics(unit="megabyte")
        self._gpu_power = MetricStatistics(unit="watt")
        self._gpu_utilization = MetricStatistics(unit="percent")
        self._gpu_temperature = MetricStatistics(unit="celsius")
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        with self._lock:
            self._vram_usage = MetricStatistics(unit="megabyte")
            self._gpu_power = MetricStatistics(unit="watt")
            self._gpu_utilization = MetricStatistics(unit="percent")
            self._gpu_temperature = MetricStatistics(unit="celsius")

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._collect_loop,
            name="GPUMetricsCollector",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is None:
            return

        self._thread.join()
        self._thread = None

    def get(self) -> GPUMetrics:
        with self._lock:
            return GPUMetrics(
                vram_usage=_copy_metric_or_none(self._vram_usage),
                gpu_power=_copy_metric_or_none(self._gpu_power),
                gpu_utilization=_copy_metric_or_none(self._gpu_utilization),
                gpu_temperature=_copy_metric_or_none(self._gpu_temperature),
            )

    def _collect_loop(self) -> None:
        while not self._stop_event.is_set():
            self._collect_once()
            self._stop_event.wait(self.interval_seconds)

    def _collect_once(self) -> None:
        gpu_metrics = self.gpu_collector.get_metrics()

        # Низкоуровневый GPUCollector возвращает один снимок доступных метрик,
        # а здесь мы накапливаем историю за весь benchmark-прогон.
        with self._lock:
            _extend_metric(self._vram_usage, gpu_metrics.vram_usage)
            _extend_metric(self._gpu_power, gpu_metrics.gpu_power)
            _extend_metric(self._gpu_utilization, gpu_metrics.gpu_utilization)
            _extend_metric(self._gpu_temperature, gpu_metrics.gpu_temperature)


def _extend_metric(target: MetricStatistics, source: MetricStatistics | None) -> None:
    if source is None:
        return
    target.history.extend(source.history)


def _copy_metric_or_none(metric: MetricStatistics) -> MetricStatistics | None:
    if not metric.history:
        return None

    copied_metric = MetricStatistics(unit=metric.unit)
    copied_metric.history.extend(metric.history)
    return copied_metric
