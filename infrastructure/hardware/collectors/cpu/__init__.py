# infrastructure/hardware/collectors/cpu/__init__.py

import logging

from infrastructure.hardware.collectors.cpu.collector import CPUCollector


logger = logging.getLogger(__name__)


__all__ = [
    'CPUCollector'
]


__version__ = "0.0.0.1"