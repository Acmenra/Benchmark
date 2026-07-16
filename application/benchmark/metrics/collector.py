# application/benchmark/metrics/collector.py

import logging
import time

from application.benchmark.metrics.cpu import CPUMetricsCollector
from application.benchmark.metrics.gpu import GPUMetricsCollector
from core.entities.config import BenchmarkRun
from core.entities.metrics import BenchmarkResult, DataPoint, MetricStatistics, PerformanceMetrics

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Собирает метрики за один benchmark-прогон."""

    def __init__(
        self,
        benchmark_run: BenchmarkRun,
        interval_seconds: float = 1.0,
        cpu_collector: CPUMetricsCollector | None = None,
        gpu_collector: GPUMetricsCollector | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds должен быть больше 0")

        self.benchmark_run = benchmark_run
        self.cpu_collector = cpu_collector or CPUMetricsCollector(interval_seconds=interval_seconds)
        self.gpu_collector = gpu_collector or GPUMetricsCollector(interval_seconds=interval_seconds)
        self.performance = PerformanceMetrics(
            fps=MetricStatistics(unit="fps"),
            latency=MetricStatistics(unit="millisecond"),
        )
        self._started_at: float | None = None

    def start(self) -> None:
        """Начать сбор метрик одного benchmark-прогона."""
        if self._started_at is not None:
            return

        self._started_at = time.perf_counter()
        self.cpu_collector.start()
        self.gpu_collector.start()

    def stop(self) -> None:
        """Остановить сбор метрик одного benchmark-прогона."""
        if self._started_at is None:
            return

        # Сначала останавливаем фоновые collectors, чтобы потоки не жили после прогона.
        self.cpu_collector.stop()
        self.gpu_collector.stop()

        self._started_at = None

    def record_latency(self, latency_ms: float) -> None:
        """Добавить замеры latency и FPS для одного inference."""
        time_in_ms = int(time.time() * 1000)
        self.performance.latency.history.append(
            DataPoint(
                time_in_ms=time_in_ms,
                value=latency_ms,
            )
        )

        if latency_ms > 0:
            self.performance.fps.history.append(
                DataPoint(
                    time_in_ms=time_in_ms,
                    value=1000 / latency_ms,
                )
            )

    def get(self) -> BenchmarkResult: # TODO Добавить расчет среднее медиан и тп
        """Вернуть итоговый результат одного benchmark-прогона."""
        return BenchmarkResult(
            case=self.benchmark_run,
            performance=self.performance,
            cpu=self.cpu_collector.get(),
            gpu=self.gpu_collector.get(),
        )
