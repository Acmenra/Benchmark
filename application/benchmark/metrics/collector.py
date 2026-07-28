# application/benchmark/metrics/collector.py

import time
import logging

from core.domain.config import BenchmarkCase
from infrastructure.metrics.cpu import CPUMetricsCollector
from infrastructure.metrics.gpu import GPUMetricsCollector
from core.domain.metrics import MetricStatistics, DataPoint, BenchmarkResult, LatencyStats


logger = logging.getLogger(__name__)


class MetricsCollector:
    """Собирает метрики за один benchmark-прогон модели."""

    def __init__(self,
                 benchmark_case: BenchmarkCase,
                 cpu_collector: CPUMetricsCollector,
                 gpu_collector: GPUMetricsCollector,
                 interval_seconds: float = 1.0) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds должен быть больше 0")

        self.benchmark_case = benchmark_case
        self.cpu_collector = cpu_collector
        self.gpu_collector = gpu_collector
        self._latency = MetricStatistics(unit="millisecond")
        self._mark_started_at: float | None = None

    def start_run(self) -> None:
        """Запускает фоновый сбор CPU/GPU-метрик на весь прогон модели."""
        self._latency = MetricStatistics(unit="millisecond")
        self._mark_started_at = None
        self.cpu_collector.start()
        self.gpu_collector.start()

    def stop_run(self) -> None:
        """Останавливает фоновый сбор CPU/GPU-метрик."""
        self.cpu_collector.stop()
        self.gpu_collector.stop()
        self._mark_started_at = None

    def mark_start(self) -> None:
        """Фиксирует старт одного инференса для замера latency."""
        self._mark_started_at = time.perf_counter()

    def mark_stop(self) -> None:
        """Фиксирует окончание инференса и добавляет замер latency."""
        if self._mark_started_at is None:
            logger.warning("mark_stop вызван без парного mark_start, замер пропущен")
            return

        latency_ms = (time.perf_counter() - self._mark_started_at) * 1000
        self._latency.history.append(
            DataPoint(
                time_in_ms=int(time.time() * 1000),
                value=latency_ms,
            )
        )
        self._mark_started_at = None

    def get(self) -> BenchmarkResult:
        """Возвращает итоговый результат прогона."""
        return BenchmarkResult(case=self.benchmark_case,
                               performance=LatencyStats.from_history(self._latency.history),
                               cpu=self.cpu_collector.get(),
                               gpu=self.gpu_collector.get())
