# core/domain/metrics/data_point.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class DataPoint:
    """
    Represents a single, timestamped metric measurement.

    This is the fundamental building block for time-series metric collection,
    pairing a precise timestamp with a numeric value.

    Attributes:
        time_in_ms (float): The absolute or relative timestamp of the measurement in milliseconds.
        value (float | int): The numeric value of the metric (e.g., latency in ms, utilization in %).

    Note:
        - Immutability (`frozen=True`) is critical to ensure thread-safety
          when appending to shared history lists in concurrent collectors.
    """
    time_in_ms: float
    value: float | int