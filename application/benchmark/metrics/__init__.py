# application/benchmark/metrics/__init__.py

import logging

from application.benchmark.metrics.base import BaseMetricsCollector
from application.benchmark.metrics.collector import MetricsCollector


logger = logging.getLogger(__name__)


__all__ = [
    'BaseMetricsCollector',
    'MetricsCollector'
]


__version__ = "0.0.0.1"