# infrastructure/metrics/cpu.py

import time
import logging
import threading
from typing import List, Optional

from core.domain.metrics import MetricStatistics, CPUMetrics, DataPoint

from infrastructure.hardware.collectors.cpu.collector import CPUCollector
from infrastructure.hardware.collectors.pwr.power import collect_cpu_power_watts
from infrastructure.hardware.collectors.tmp.collector import collect_cpu_temperature_celsius

from application.benchmark.metrics import BaseMetricsCollector


logger = logging.getLogger(__name__)


class CPUMetricsCollector(BaseMetricsCollector):
    """
    Background thread-based collector for CPU runtime metrics.

    This class orchestrates the periodic polling of CPU utilization (via the
    injected CPUCollector), system power draw, and thermal readings. It is
    designed to be thread-safe and resilient to transient sensor failures.

    Key design decisions:
    - Thread-safety: Uses `threading.Lock` to protect history extension and
      metric retrieval from race conditions.
    - Graceful degradation: If power or temperature readings fail consecutively,
      the collector automatically disables polling for those specific metrics
      to prevent log spam and wasted CPU cycles.
    - Monotonic timing: Uses `time.time_ns()` for precise millisecond timestamps.
    """

    def __init__(self,
                 cpu_collector: CPUCollector,
                 interval_seconds: float = 1.0) -> None:
        """
        Initializes the CPU metrics collector.

        Args:
            cpu_collector: The underlying hardware collector for CPU utilization.
            interval_seconds: The polling interval in seconds. Must be > 0.

        Raises:
            ValueError: If `interval_seconds` is less than or equal to 0.
        """
        super().__init__()
        if interval_seconds <= 0:
            raise ValueError("interval_seconds должен быть больше 0")

        self._history = []
        self.interval_seconds = interval_seconds
        self.cpu_collector = cpu_collector

        self._cpu_utilization = MetricStatistics(unit="percent") # TODO args
        self._cpu_power = MetricStatistics(unit="watt")
        self._cpu_temperature = MetricStatistics(unit="celsius")
        self._collect_cpu_power = True
        self._collect_cpu_temperature = True
        self._cpu_temperature_failures = 0
        self._max_cpu_temperature_failures = 3

        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    @property
    def history(self) -> List[DataPoint]:
        """Returns the raw history of collected data points."""
        return self._history

    def start(self) -> None:
        """
        Initiates the background CPU metrics collection process.

        Resets internal metric buffers, clears the stop event, and spawns a
        new daemon thread to execute the `_collect_loop`. This method is
        idempotent; consecutive calls without an intervening `stop()` are ignored.
        """
        thread = None
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return

            self._cpu_utilization = MetricStatistics(unit="percent")
            self._cpu_power = MetricStatistics(unit="watt")
            self._cpu_temperature = MetricStatistics(unit="celsius")
            self._collect_cpu_power = True
            self._collect_cpu_temperature = True
            self._cpu_temperature_failures = 0
            self._stop_event.clear()
            thread = threading.Thread(
                target=self._collect_loop,
                name="CPUMetricsCollector",
                daemon=True,
            )
            self._thread = thread

        if thread is not None:
            thread.start()

    def stop(self) -> None:
        """
        Terminates the background CPU metrics collection process.

        Signals the polling thread to stop via the `_stop_event` and waits
        for the thread to join, ensuring a clean shutdown before metrics
        are retrieved via `get()`.
        """
        self._stop_event.set()

        thread = self._thread
        if thread is None:
            return

        thread.join()
        self._thread = None

    def get(self) -> CPUMetrics:
        """
        Retrieves the aggregated CPU metrics collected during the run.

        Returns:
            CPUMetrics: An immutable domain object containing the aggregated
                        statistics for CPU utilization, power, and temperature.
        """
        cpu_utilization = MetricStatistics(unit=self._cpu_utilization.unit)
        with self._lock:
            cpu_utilization.history.extend(self._cpu_utilization.history)
            cpu_power = _copy_metric_or_none(self._cpu_power)
            cpu_temperature = _copy_metric_or_none(self._cpu_temperature)

        return CPUMetrics(cpu_power=cpu_power,
                          cpu_utilization=cpu_utilization,
                          cpu_temperature=cpu_temperature)

    def _collect_loop(self) -> None:
        """
        Internal method running the continuous polling loop.

        Executes `_collect_once()` at the specified interval until the
        `_stop_event` is set. Exceptions are caught and logged to prevent
        a single sensor failure from crashing the entire benchmark thread.
        """

        while not self._stop_event.is_set():
            try:
                self._collect_once()
            except Exception:
                logger.exception("Ошибка при сборе метрик CPU, снимок пропущен")

            self._stop_event.wait(self.interval_seconds)

    def _collect_once(self) -> None:
        """
        Fetches a single snapshot of CPU metrics and appends them to history.

        Implements graceful degradation: if power or temperature readings
        return `None`, failure counters are incremented. If temperature fails
        consecutively `_max_cpu_temperature_failures` times, its collection
        is permanently disabled for the remainder of the run.
        """
        cpu_utilization = self.cpu_collector.get_metrics()
        cpu_power = collect_cpu_power_watts() if self._collect_cpu_power else None
        cpu_temperature = (collect_cpu_temperature_celsius()
                           if self._collect_cpu_temperature
                           else None)

        if cpu_power is None:
            self._collect_cpu_power = False
        if cpu_temperature is None:
            self._cpu_temperature_failures += 1
            if self._cpu_temperature_failures >= self._max_cpu_temperature_failures:
                self._collect_cpu_temperature = False
        else:
            self._cpu_temperature_failures = 0

        with self._lock:
            self._cpu_utilization.history.extend(cpu_utilization.history)
            _append_metric_sample(self._cpu_power, cpu_power)
            _append_metric_sample(self._cpu_temperature, cpu_temperature)


def _append_metric_sample(metric: MetricStatistics,
                          value: float | int | None) -> None:
    """
    Appends a single metric value to the history with a monotonic timestamp.

    Args:
        metric: The MetricStatistics container to append to.
        value: The numeric value to record. Ignored if `None`.
    """
    if value is None:
        return

    metric.history.append(DataPoint(time_in_ms=time.time_ns() // 1_000_000,
                                    value=value)
                          )


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
