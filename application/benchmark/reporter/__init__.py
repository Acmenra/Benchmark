# application/benchmark/reporter/__init__.py

import logging
from application.benchmark.reporter.base import BaseReporter
from application.benchmark.reporter.reporter import Reporter


logger = logging.getLogger(__name__)


__all__ = [
    "BaseReporter",
    "Reporter",
]

__version__ = "0.0.0.1"