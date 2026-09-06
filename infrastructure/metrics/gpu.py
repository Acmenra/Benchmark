# infrastructure/metrics/gpu.py

import logging
import threading
from typing import Optional

from core.domain.config.system import SystemInfoConfig
from core.domain.metrics import MetricStatistics, GPUMetrics
from application.benchmark.metrics.base import BaseMetricsCollector
from infrastructure.hardware.collectors.gpu.collector import GPUCollector


logger = logging.getLogger(__name__)


class GPUMetricsCollector(BaseMetricsCollector):
    """
    Background thread-based collector for GPU runtime metrics.

    This class orchestrates the periodic polling of GPU metrics delegated from
    the underlying `GPUCollector`. It mirrors the design of `CPUMetricsCollector`
    to ensure consistent hardware telemetry gathering across the suite.

    Key design decisions:
    - Thread-safety: Uses `threading.Lock` to protect history extension.
    - Graceful degradation: Safely handles `None` returns from the underlying
      `GPUCollector` (e.g., if no GPU is present) by skipping the snapshot.
    """

    def __init__(self,
                 gpu_collector: GPUCollector,
                 interval_seconds: float = 1.0) -> None:
        """
        Initializes the GPU metrics collector.

        Args:
            gpu_collector: The underlying hardware collector for GPU metrics.
            interval_seconds: The polling interval in seconds. Must be > 0.

        Raises:
            ValueError: If `interval_seconds` is less than or equal to 0.
        """
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
        """
        Initiates the background GPU metrics collection process.

        Resets internal metric buffers, clears the stop event, and spawns a
        new daemon thread to execute the `_collect_loop`.
        """
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
        """
        Terminates the background GPU metrics collection process.

        Signals the polling thread to stop and waits for it to join.
        """
        self._stop_event.set()

        thread = self._thread
        if thread is None:
            return

        thread.join()
        self._thread = None
        logger.debug("GPUMetricsCollector остановлен")

    def get(self) -> GPUMetrics:
        """
        Retrieves the aggregated GPU metrics collected during the run.

        Returns:
            GPUMetrics: An immutable domain object containing the aggregated
                        statistics for VRAM, power, utilization, and temperature.
        """
        with self._lock:
            return GPUMetrics(
                vram_usage=_copy_metric_or_none(self._vram_usage),
                gpu_power=_copy_metric_or_none(self._gpu_power),
                gpu_utilization=_copy_metric_or_none(self._gpu_utilization),
                gpu_temperature=_copy_metric_or_none(self._gpu_temperature),
            )

    def _reset_metrics(self) -> None:
        """
        Clears the accumulated metric history before a new benchmark run.

        Note:
            This method must be called while holding `self._lock`.
        """
        self._vram_usage = MetricStatistics(unit="megabyte")
        self._gpu_power = MetricStatistics(unit="watt")
        self._gpu_utilization = MetricStatistics(unit="percent")
        self._gpu_temperature = MetricStatistics(unit="celsius")

    def _collect_loop(self) -> None:
        """
        Internal method running the continuous polling loop.

        Executes `_collect_once()` at the specified interval until the
        `_stop_event` is set. Exceptions are caught and logged to prevent
        a single sensor failure from crashing the benchmark thread.
        """
        while not self._stop_event.is_set():
            try:
                self._collect_once()
            except Exception:
                logger.exception("Ошибка при сборе метрик GPU, снимок пропущен")

            self._stop_event.wait(self.interval_seconds)

    def _collect_once(self) -> None:
        """
        Fetches a single snapshot of GPU metrics and extends the history.

        Delegates the actual hardware querying to the injected `GPUCollector`.
        If the collector returns `None` (e.g., no GPU detected), the snapshot
        is safely skipped.
        """
        gpu_metrics = self.gpu_collector.get_metrics()

        if gpu_metrics is None:
            return

        with self._lock:
            _extend_metric(self._vram_usage, gpu_metrics.vram_usage)
            _extend_metric(self._gpu_power, gpu_metrics.gpu_power)
            _extend_metric(self._gpu_utilization, gpu_metrics.gpu_utilization)
            _extend_metric(self._gpu_temperature, gpu_metrics.gpu_temperature)


def _extend_metric(target: MetricStatistics,
                   source: Optional[MetricStatistics]) -> None:
    """
    Safely extends the target metric history with the source history.

    Args:
        target: The MetricStatistics container to extend.
        source: The source MetricStatistics container. Ignored if `None`.
    """
    if source is None:
        return
    target.history.extend(source.history)


def _copy_metric_or_none(metric: MetricStatistics) -> Optional[MetricStatistics]:
    """
    Creates a thread-safe copy of a MetricStatistics object.

    Returns:
        MetricStatistics | None: A new instance with the copied history,
                                 or `None` if the source history is empty.
    """
    if not metric.history:
        return None

    copied_metric = MetricStatistics(unit=metric.unit)
    copied_metric.history.extend(metric.history)
    return copied_metric
