# core/domain/metrics/hardware/cpu.py

import logging
from dataclasses import dataclass
from core.domain.metrics.statistics import MetricStatistics


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class CPUMetrics:
    """
    Aggregated performance metrics for the Central Processing Unit (CPU).

    This immutable dataclass serves as a container for statistical summaries
    of CPU-related telemetry collected during a benchmark run.

    Attributes:
        cpu_power (MetricStatistics | None): Statistical summary of CPU power draw (in Watts).
        cpu_utilization (MetricStatistics | None): Statistical summary of CPU usage (in percent).
        cpu_temperature (MetricStatistics | None): Statistical summary of CPU thermal readings (in Celsius).

    Note:
        - All fields are optional (`None`) if the respective sensor or collector
          is unavailable or disabled in the configuration.
        - The `frozen=True` flag ensures the metrics cannot be accidentally
          mutated after aggregation.
    """
    cpu_power: MetricStatistics | None = None
    cpu_utilization: MetricStatistics | None = None
    cpu_temperature: MetricStatistics | None = None
