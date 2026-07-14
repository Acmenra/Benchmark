# application/benchmark/metrics/cpu.py

import logging
import threading

from application.benchmark.metrics.base import MetricCollector
from core.entities.config import SystemInfoConfig
from core.entities.metrics import CPUMetrics, MetricStatistics
from infrastructure.hardware.collectors.cpu import CPUCollector

logger = logging.getLogger(__name__)


class CPUMetricsCollector(MetricCollector):
    """Фоновый сборщик runtime-метрик CPU для одного benchmark-прогона."""

    def __init__(
        self,
        interval_seconds: float = 1.0,
        cpu_collector: CPUCollector | None = None,
    ) -> None:
        super().__init__()
        if interval_seconds <= 0:
            raise ValueError("interval_seconds должен быть больше 0")

        self.interval_seconds = interval_seconds
        self.cpu_collector = cpu_collector or CPUCollector(
            SystemInfoConfig(
                collect_gpu=False,
                collect_power=False,
                collect_temperature=False,
            )
        )
        self._cpu_utilization = MetricStatistics(unit="percent")
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        with self._lock:
            self._cpu_utilization = MetricStatistics(unit="percent")

        self.cpu_collector.prepare_metrics_collection()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._collect_loop,
            name="CPUMetricsCollector",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is None:
            return

        self._thread.join()
        self._thread = None
    
    def get(self) -> CPUMetrics:
        cpu_utilization = MetricStatistics(unit=self._cpu_utilization.unit)
        with self._lock:
            cpu_utilization.history.extend(self._cpu_utilization.history)

        return CPUMetrics(cpu_utilization=cpu_utilization)

    def _collect_loop(self) -> None:
        while not self._stop_event.is_set():
            self._collect_once()
            self._stop_event.wait(self.interval_seconds)

    def _collect_once(self) -> None:
        cpu_utilization = self.cpu_collector.get_metrics()

        # CPUCollector возвращает один снимок,
        # а здесь мы накапливаем историю за весь benchmark-прогон.
        with self._lock:
            self._cpu_utilization.history.extend(cpu_utilization.history)

    # Сейчас collector собирает только cpu_utilization.
    # cpu_power и cpu_temperature будут подключены позже через отдельные collectors.
