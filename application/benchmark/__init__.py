# application/benchmark/__init__.py

import logging


logger = logging.getLogger(__name__)


__all__ = [
    "BaseReporter",
    "Reporter",
    'BaseMetricsCollector',
    'MetricsCollector'
]


__version__ = "0.0.0.1"