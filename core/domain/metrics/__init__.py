# core/domain/metrics/__init__.py

import logging

from core.domain.metrics.data_point import DataPoint
from core.domain.metrics.latency import LatencyStats
from core.domain.metrics.quality import QualityMetrics
from core.domain.metrics.statistics import MetricStatistics
from core.domain.metrics.hardware import CPUMetrics, GPUMetrics
from core.domain.metrics.results import BenchmarkResult, ModelBenchmarkResult


logger = logging.getLogger(__name__)


__all__ = [
    'DataPoint',
    'MetricStatistics',
    'LatencyStats',
    'CPUMetrics',
    'GPUMetrics',
    'QualityMetrics',
    'BenchmarkResult',
    'ModelBenchmarkResult',
]

__version__ = "0.0.0.1"