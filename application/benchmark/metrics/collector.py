import time
import logging

from core.domain.config import BenchmarkCase
from infrastructure.metrics.cpu import CPUMetricsCollector
from infrastructure.metrics.gpu import GPUMetricsCollector
from core.domain.metrics import MetricStatistics, DataPoint, BenchmarkResult, LatencyStats


logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Aggregates metrics for a single benchmark model run.

    Orchestrates the collection of latency (via mark_start/mark_stop) and
    background hardware metrics (CPU/GPU utilization) for the duration of
    a benchmark case execution.
    """

    def __init__(self,
                 benchmark_case: BenchmarkCase,
                 cpu_collector: CPUMetricsCollector,
                 gpu_collector: GPUMetricsCollector,
                 interval_seconds: float = 1.0) -> None:
        if interval_seconds <= 0:
            raise ValueError("'interval_seconds' must be greater than 0")

        self.benchmark_case = benchmark_case
        self.cpu_collector = cpu_collector
        self.gpu_collector = gpu_collector
        self._latency = MetricStatistics(unit="millisecond")
        self._mark_started_at: float | None = None

    def start_run(self) -> None:
        """
        Initiates background CPU/GPU metrics collection for the entire model run.

        Resets internal latency buffers and starts the background polling threads
        in the underlying CPU and GPU collectors.
        """
        self._latency = MetricStatistics(unit="millisecond")
        self._mark_started_at = None
        self.cpu_collector.start()
        self.gpu_collector.start()

    def stop_run(self) -> None:
        """
        Terminates background CPU/GPU metrics collection.

        Stops the polling threads and finalizes the aggregated hardware metrics
        for retrieval via `get()`.
        """
        self.cpu_collector.stop()
        self.gpu_collector.stop()
        self._mark_started_at = None

    def mark_start(self) -> None:
        """
        Records the start time of a single inference for latency measurement.

        Uses `time.perf_counter()` to ensure high-resolution, monotonic timing
        that is immune to system clock adjustments.
        """
        self._mark_started_at = time.perf_counter()

    def mark_stop(self) -> None:
        """
        Records the end time of an inference and appends the latency measurement.

        Calculates the elapsed time in milliseconds and appends it to the latency
        history buffer.
        """
        if self._mark_started_at is None:
            logger.warning("'mark_stop' called without a preceding 'mark_start', skipping measurement")
            return

        latency_ms = (time.perf_counter() - self._mark_started_at) * 1000.0
        self._latency.history.append(
            DataPoint(time_in_ms=time.perf_counter() * 1000.0,
                      value=latency_ms
                      )
        )
        self._mark_started_at = None

    def get(self) -> BenchmarkResult:
        """
        Retrieves the final aggregated result for the benchmark run.

        Returns:
            BenchmarkResult: A container holding the benchmark case reference,
                             computed latency statistics, and aggregated CPU/GPU metrics.
        """
        return BenchmarkResult(case=self.benchmark_case,
                               performance=LatencyStats.from_history(self._latency.history),
                               cpu=self.cpu_collector.get(),
                               gpu=self.gpu_collector.get())