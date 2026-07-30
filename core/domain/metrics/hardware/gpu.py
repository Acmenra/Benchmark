# core/domain/metrics/hardware/gpu.py

import logging
from dataclasses import dataclass

from core.domain.metrics.statistics import MetricStatistics


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class GPUMetrics:
    """
    Aggregated performance metrics for the Graphics Processing Unit (GPU).

    This immutable dataclass serves as a container for statistical summaries
    of GPU-related telemetry collected during a benchmark run.

    Attributes:
        vram_usage (MetricStatistics | None): Statistical summary of Video RAM usage (in MB or percent).
        gpu_power (MetricStatistics | None): Statistical summary of GPU power draw (in Watts).
        gpu_utilization (MetricStatistics | None): Statistical summary of GPU compute usage (in percent).
        gpu_temperature (MetricStatistics | None): Statistical summary of GPU thermal readings (in Celsius).

    Note:
        - All fields are optional (`None`) if the respective sensor or collector
          is unavailable or disabled in the configuration.
        - The `frozen=True` flag ensures the metrics cannot be accidentally
          mutated after aggregation.
    """
    vram_usage: MetricStatistics | None = None
    gpu_power: MetricStatistics | None = None
    gpu_utilization: MetricStatistics | None = None
    gpu_temperature: MetricStatistics | None = None