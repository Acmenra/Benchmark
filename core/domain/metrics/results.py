# core/domain/metrics/results.py

import logging
from typing import Any
from dataclasses import dataclass

from core.domain.config import BenchmarkCase
from core.domain.metrics import QualityMetrics
from core.domain.metrics.latency import LatencyStats
from core.domain.metrics.hardware.cpu import CPUMetrics
from core.domain.metrics.hardware.gpu import GPUMetrics


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class BenchmarkResult:
    """
    Aggregated result for a single benchmark case.

    Represents the high-level outcome of a benchmark run, potentially aggregating
    data across multiple models or devices within a single test scenario.

    Attributes:
        case (BenchmarkCase): The configuration scenario that was executed.
        performance (LatencyStats | None): Aggregated inference performance metrics.
        cpu (CPUMetrics | None): Aggregated CPU telemetry.
        gpu (GPUMetrics | None): Aggregated GPU telemetry.
    """
    case: BenchmarkCase
    performance: LatencyStats | None = None
    cpu: CPUMetrics | None = None
    gpu: GPUMetrics | None = None


@dataclass(slots=True, frozen=True)
class ModelBenchmarkResult:
    """
    Detailed benchmark result for a single, specific model configuration.

    This is the primary data structure used for generating granular reports
    (e.g., CSV rows, JSON objects), mapping a specific model/format/quantization
    combination to its observed performance and quality metrics.

    Attributes:
        model (dict[str, Any]): Metadata dictionary containing `family`, `size`, `device`,
                                `task_type`, `format`, and `quantization`.
        status (str): Execution outcome (`'success'`, `'failed'`, or `'skipped'`).
        error (str | None): Descriptive error message if status is `'failed'` or `'skipped'`.
        performance (LatencyStats | None): Inference performance metrics.
        cpu (CPUMetrics | None): CPU telemetry during this specific model's run.
        gpu (GPUMetrics | None): GPU telemetry during this specific model's run.
        quality (QualityMetrics | None): Model accuracy metrics (if validation was enabled).

    Note:
        - Immutability ensures that once a result is yielded by the runner,
          it cannot be tampered with by downstream reporting pipelines.
    """
    model: dict[str, Any]
    status: str = "success"
    error: str | None = None
    performance: LatencyStats | None = None
    cpu: CPUMetrics | None = None
    gpu: GPUMetrics | None = None
    quality: QualityMetrics | None = None