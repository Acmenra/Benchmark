# core/domain/hardware/__init__.py

import logging

from core.domain.metrics.hardware.cpu import CPUMetrics
from core.domain.metrics.hardware.gpu import GPUMetrics


logger = logging.getLogger(__name__)


__all__ = [
    'CPUMetrics',
    'GPUMetrics'
]


__version__ = "0.0.0.1"