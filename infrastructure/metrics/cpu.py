# infrastructure/metrics/cpu.py

import time
import logging
import threading

from core.domain.config.system import SystemInfoConfig
from core.domain.metrics import MetricStatistics, CPUMetrics, DataPoint

from infrastructure.hardware.collectors.cpu import CPUCollector
from infrastructure.hardware.collectors.power import collect_cpu_power_watts
from infrastructure.hardware.collectors.temperature import collect_cpu_temperature_celsius

from application.benchmark.metrics import BaseMetricsCollector


logger = logging.getLogger(__name__)


class CPUMetricsCollector(BaseMetricsCollector):
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
        self._cpu_power = MetricStatistics(unit="watt")
        self._cpu_temperature = MetricStatistics(unit="celsius")
        self._collect_cpu_power = True
        self._collect_cpu_temperature = True
        self._cpu_temperature_failures = 0
        self._max_cpu_temperature_failures = 3
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
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
        self._stop_event.set()

        thread = self._thread
        if thread is None:
            return

        thread.join()
        self._thread = None

    def get(self) -> CPUMetrics:
        cpu_utilization = MetricStatistics(unit=self._cpu_utilization.unit)
        with self._lock:
            cpu_utilization.history.extend(self._cpu_utilization.history)
            cpu_power = _copy_metric_or_none(self._cpu_power)
            cpu_temperature = _copy_metric_or_none(self._cpu_temperature)

        return CPUMetrics(
            cpu_power=cpu_power,
            cpu_utilization=cpu_utilization,
            cpu_temperature=cpu_temperature,
        )

    def _collect_loop(self) -> None:
        self.cpu_collector.prepare_metrics_collection()

        while not self._stop_event.is_set():
            # Чтобы из-за одного сбоя не рушился весь сбор метрик, ловим
            # исключения и логируем их (аналогично GPUMetricsCollector).
            try:
                self._collect_once()
            except Exception:
                logger.exception("Ошибка при сборе метрик CPU, снимок пропущен")

            self._stop_event.wait(self.interval_seconds)

    def _collect_once(self) -> None:
        cpu_utilization = self.cpu_collector.get_metrics()
        cpu_power = collect_cpu_power_watts() if self._collect_cpu_power else None
        cpu_temperature = (
            collect_cpu_temperature_celsius()
            if self._collect_cpu_temperature
            else None
        )

        if cpu_power is None:
            self._collect_cpu_power = False
        if cpu_temperature is None:
            self._cpu_temperature_failures += 1
            if self._cpu_temperature_failures >= self._max_cpu_temperature_failures:
                self._collect_cpu_temperature = False
        else:
            self._cpu_temperature_failures = 0

        # Низкоуровневые collectors возвращают один снимок,
        # а здесь мы накапливаем историю за весь benchmark-прогон.
        with self._lock:
            self._cpu_utilization.history.extend(cpu_utilization.history)
            _append_metric_sample(self._cpu_power, cpu_power)
            _append_metric_sample(self._cpu_temperature, cpu_temperature)


def _append_metric_sample(metric: MetricStatistics, value: float | int | None) -> None:
    if value is None:
        return

    metric.history.append(
        DataPoint(
            time_in_ms=time.time_ns() // 1_000_000,
            value=value,
        )
    )


def _copy_metric_or_none(metric: MetricStatistics) -> MetricStatistics | None:
    if not metric.history:
        return None

    copied_metric = MetricStatistics(unit=metric.unit)
    copied_metric.history.extend(metric.history)
    return copied_metric
