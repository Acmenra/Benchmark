# infrastructure/metrics/gpu.py

import logging
import threading

from core.domain.config.system import SystemInfoConfig
from core.domain.metrics import MetricStatistics, GPUMetrics
from application.benchmark.metrics.base import BaseMetricsCollector
from infrastructure.hardware.collectors.gpu.collector import GPUCollector


logger = logging.getLogger(__name__)


class GPUMetricsCollector(BaseMetricsCollector):
    """Фоновый сборщик runtime-метрик GPU для одного benchmark-прогона."""

    def __init__(self,
                 gpu_collector: GPUCollector,
                 interval_seconds: float = 1.0) -> None:
        super().__init__()
        if interval_seconds <= 0:
            raise ValueError("interval_seconds должен быть больше 0")

        self.interval_seconds = interval_seconds
        self.gpu_collector = gpu_collector
        self._vram_usage = MetricStatistics(unit="megabyte")
        self._gpu_power = MetricStatistics(unit="watt")
        self._gpu_utilization = MetricStatistics(unit="percent")
        self._gpu_temperature = MetricStatistics(unit="celsius")
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return

            self._reset_metrics()
            self._stop_event.clear()
            thread = threading.Thread(
                target=self._collect_loop,
                name="GPUMetricsCollector",
                daemon=True,
            )
            self._thread = thread

        thread.start()
        logger.debug("GPUMetricsCollector запущен, интервал %.3fs", self.interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()

        thread = self._thread
        if thread is None:
            return

        thread.join()
        self._thread = None
        logger.debug("GPUMetricsCollector остановлен")

    def _reset_metrics(self) -> None:
        """Сбросить накопленную историю метрик перед новым прогоном.

        Вызывается под self._lock.
        """
        self._vram_usage = MetricStatistics(unit="megabyte")
        self._gpu_power = MetricStatistics(unit="watt")
        self._gpu_utilization = MetricStatistics(unit="percent")
        self._gpu_temperature = MetricStatistics(unit="celsius")

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
            # Чтобы из-за одного сбоя не рушился весь сбор метрик, ловим исключения и логируем их.
            try:
                self._collect_once()
            except Exception:
                logger.exception("Ошибка при сборе метрик GPU, снимок пропущен")

            self._stop_event.wait(self.interval_seconds)

    def _collect_once(self) -> None:
        gpu_metrics = self.gpu_collector.get_metrics()

        if gpu_metrics is None:
            return

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
