# application/benchmark/metrics/base.py

import logging
from abc import ABC, abstractmethod

from core.domain.metrics import MetricStatistics

logger = logging.getLogger(__name__)


class BaseMetricsCollector(ABC):
    """
    Abstract base class for all metrics collectors in the benchmark suite.

    Defines the strict lifecycle contract that any metrics collector (e.g., CPU, GPU,
    latency, power) must implement to integrate with the BenchmarkRunner. Provides
    a unified interface for starting, stopping, and retrieving aggregated metric data,
    ensuring a consistent and backend-agnostic benchmarking architecture.

    Key design decisions (contracts):
    - All collectors must implement a strict lifecycle: `start()`, `stop()`, and `get()`.
    - `start()` initializes the collection state (e.g., clearing history, starting threads).
    - `stop()` finalizes the collection (e.g., stopping threads, calculating final aggregates).
    - `get()` returns the aggregated, structured metric data (e.g., `MetricStatistics`).
    - Designed to be thread-safe if background polling is used by subclasses.

    Designed for seamless integration with the benchmarking pipeline:
    - Performance profiling (latency, FPS).
    - Hardware resource monitoring (CPU/GPU utilization, power, temperature).
    - Consistent data aggregation for JSON/CSV reporting.

    Note:
        - Subclasses must implement all abstract methods.
        - The `get()` method should return a fully populated, immutable data structure
          ready for serialization.
    """

    @abstractmethod
    def start(self) -> None:
        """
        Initiates the metrics collection process.

        This method should be called immediately before the benchmark workload begins.
        It is responsible for resetting internal state, clearing historical data buffers,
        and starting any background polling threads if applicable.

        Raises:
            RuntimeError: If the collector is already in a 'started' state.

        Note:
            - Subclasses must ensure this method is idempotent or raises an error
              if called consecutively without an intervening `stop()`.
            - For polling-based collectors, this is where the background thread starts.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Terminates the metrics collection process and finalizes aggregation.

        This method should be called immediately after the benchmark workload completes.
        It is responsible for stopping background threads, calculating final statistical
        aggregates (e.g., mean, percentiles, min/max), and sealing the data for retrieval.

        Raises:
            RuntimeError: If the collector is not currently in a 'started' state.

        Note:
            - Must be called before `get()` to ensure all metrics are fully processed.
            - Subclasses should handle graceful shutdown of any background resources.
        """
        pass

    @abstractmethod
    def get(self) -> MetricStatistics:
        """
        Retrieves the aggregated metrics collected during the benchmark run.

        This method returns the final, processed statistical data (e.g., mean,
        percentiles, min/max, and raw history) gathered between the `start()`
        and `stop()` calls.

        Returns:
            MetricStatistics: An immutable container holding the aggregated
                              performance or hardware metrics.

        Raises:
            RuntimeError: If `get()` is called before `stop()` has finalized the collection.

        Note:
            - The returned object should be treated as immutable (frozen dataclass).
            - Subclasses must ensure all calculations (e.g., percentile sorting)
              are completed before returning the result.
        """
        pass