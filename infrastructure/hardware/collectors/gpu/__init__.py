# infrastructure/hardware/collectors/gpu/__init__.py

import logging

from infrastructure.hardware.collectors.gpu.collector import GPUCollector


logger = logging.getLogger(__name__)


__all__ = [
    'GPUCollector'
]


__version__ = "0.0.0.1"