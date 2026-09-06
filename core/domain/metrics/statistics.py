# core/domain/metrics/statistics.py

import logging
from typing import Optional

from core.domain.metrics.data_point import DataPoint


logger = logging.getLogger(__name__)


def _percentile(sorted_values: list[float],
                coeff: float) -> float:
    """
    Computes the value at a given percentile using the nearest-rank method.

    Args:
        sorted_values: A pre-sorted list of numeric values.
        coeff: The target percentile coefficient (e.g., 0.95 for 95th percentile).

    Returns:
        float: The value at the specified percentile. Returns 0.0 if the list is empty.

    Note:
        - This function assumes the input list is already sorted in ascending order
          to avoid redundant O(N log N) sorting operations during repeated calls.
    """
    if not sorted_values:
        return 0.0
    idx = int(coeff * (len(sorted_values) - 1))
    return sorted_values[min(idx, len(sorted_values) - 1)]


class MetricStatistics:
    """
    Aggregated statistical summary for a series of metric measurements.

    This class lazily computes and caches statistical properties (min, max, mean,
    percentiles) from a history of `DataPoint` objects, optimizing performance
    when multiple properties are accessed sequentially.

    Attributes:
        history (list[DataPoint]): The raw, append-only sequence of measurements.
        unit (str | None): The unit of measurement (e.g., 'ms', 'percent', 'W').

    Note:
        - The `_sorted_values` cache is built on first access to any sorted-dependent
          property (e.g., `p95`, `median`) to ensure O(N log N) sorting happens at most once.
        - This class is designed to be mutated (via `history.append`) during collection,
          but the computed properties are idempotent for a given history state.
    """

    def __init__(self,
                 unit: Optional[str] = None) -> None:
        """
        Initializes an empty statistics container.

        Args:
            unit: Optional string representing the unit of the metric values.
        """
        self.history: list[DataPoint] = []
        self.unit: str | None = unit
        self._sorted_values: list[float] | None = None

    def __str__(self) -> str:
        """
        Returns a human-readable summary of the statistics.

        Returns:
            str: A formatted string containing N, min, mean, p95, and max.
        """
        if not self.history:
            return f"MetricStatistics[{self.unit or 'unknown'}]: empty"
        return (f"Stats[{self.unit}]: n={len(self.history)}, "
                f"min={self.minimum:.2f}, mean={self.mean:.2f}, "
                f"p95={self.p95:.2f}, max={self.maximum:.2f}")

    def __repr__(self) -> str:
        """
        Returns a detailed, unambiguous string representation for debugging.

        Returns:
            str: A representation showing the unit, sample count, and mean.
        """
        count = len(self.history)
        mean_val = f"{self.mean:.2f}" if self.mean is not None else "N/A"
        return f"MetricStatistics(unit='{self.unit}', samples={count}, mean={mean_val})"

    @property
    def minimum(self) -> Optional[float]:
        """
        float | None: The lowest recorded value in the history.
        """
        if not self.history:
            return None
        self._ensure_sorted()
        return self._sorted_values[0] if self._sorted_values else None

    @property
    def maximum(self) -> Optional[float]:
        """
        float | None: The highest recorded value in the history.
        """
        if not self.history:
            return None
        self._ensure_sorted()
        return self._sorted_values[-1] if self._sorted_values else None

    @property
    def mean(self) -> Optional[float]:
        """
        float | None: The arithmetic average of all recorded values.
        """
        if not self.history:
            return None
        values = [i.value for i in self.history]
        return sum(values) / len(values)

    @property
    def median(self) -> Optional[float]:
        """
        float | None: The 50th percentile (middle value) of the recorded data.
        """
        if not self.history:
            return None
        self._ensure_sorted()
        if not self._sorted_values:
            return None
        n = len(self._sorted_values)
        if n % 2 == 0:
            return (self._sorted_values[n // 2] + self._sorted_values[n // 2 - 1]) / 2
        return self._sorted_values[n // 2]

    @property
    def p95(self) -> Optional[float]:
        """
        float | None: The 95th percentile, representing the threshold below which 95% of observations fall.
        """
        if not self.history:
            return None
        self._ensure_sorted()
        if not self._sorted_values:
            return None
        return _percentile(self._sorted_values, 0.95)

    @property
    def p99(self) -> Optional[float]:
        """
        float | None: The 99th percentile, representing the threshold below which 99% of observations fall.
        """
        if not self.history:
            return None
        self._ensure_sorted()
        if not self._sorted_values:
            return None
        return _percentile(self._sorted_values, 0.99)

    def _ensure_sorted(self) -> None:
        """
        Ensures the internal cache of sorted values is populated.

        Note:
            - This is an internal method called by properties that require sorted data.
            - It is idempotent; subsequent calls have O(1) complexity after the first sort.
        """
        if self._sorted_values is None:
            self._sorted_values = sorted(point.value for point in self.history)