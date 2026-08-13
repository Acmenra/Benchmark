# application/__init__.py

import logging

from application.benchmark import BaseReporter, Reporter, BaseMetricsCollector, MetricsCollector

logger = logging.getLogger(__name__)


__all__ = [
    "BaseReporter",
    "Reporter",
    'BaseMetricsCollector',
    'MetricsCollector'
]


__version__ = "0.0.0.1"