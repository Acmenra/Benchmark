# core/domain/metrics/latency.py

import logging
from dataclasses import dataclass

from core.domain.metrics.data_point import DataPoint
from core.domain.metrics.statistics import _percentile


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class LatencyStats:
    """
    Aggregated statistical summary of inference latency.

    Provides a comprehensive view of model execution time, including central
    tendency (mean, median) and tail latency (p95, p99), which are critical
    for real-time applications.

    Attributes:
        fps (float | None): Frames processed per second.
        mean_ms (float | None): Arithmetic mean of inference time in milliseconds.
        p50_ms (float | None): 50th percentile (median) inference time in milliseconds.
        p95_ms (float | None): 95th percentile inference time in milliseconds.
        p99_ms (float | None): 99th percentile inference time in milliseconds.
        min_ms (float | None): Minimum observed inference time in milliseconds.
        max_ms (float | None): Maximum observed inference time in milliseconds.
    """
    fps: float | None
    mean_ms: float | None
    p50_ms: float | None
    p95_ms: float | None
    p99_ms: float | None
    min_ms: float | None
    max_ms: float | None

    @classmethod
    def from_history(cls, history: list[DataPoint]) -> "LatencyStats | None":
        """
        Constructs a LatencyStats instance from a list of raw DataPoints.

        Args:
            history: A list of `DataPoint` objects representing latency measurements in milliseconds.

        Returns:
            LatencyStats | None: A fully populated statistics object, or `None` if the history is empty.

        Note:
            - The input list is sorted internally to compute percentiles efficiently.
            - FPS is calculated as `1000.0 / mean_ms`. If mean is 0 or history is empty, FPS is `None`.
        """
        if not history:
            return None

        values = sorted(point.value for point in history)
        mean = sum(values) / len(values)

        return cls(fps=1000.0 / mean if mean > 0 else None,
                   mean_ms=mean,
                   p50_ms=_percentile(values, 0.50),
                   p95_ms=_percentile(values, 0.95),
                   p99_ms=_percentile(values, 0.99),
                   min_ms=values[0],
                   max_ms=values[-1])