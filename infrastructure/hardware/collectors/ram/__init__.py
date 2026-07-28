# infrastructure/hardware/collectors/ram/__init__.py

import logging

from infrastructure.hardware.collectors.ram.collector import RAMCollector


logger = logging.getLogger(__name__)


__all__ = [
    'RAMCollector'
]


__version__ = "0.0.0.1"