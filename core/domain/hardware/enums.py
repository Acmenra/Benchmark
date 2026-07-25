# core/enums/hardware.py

import logging
from enum import Enum


logger = logging.getLogger(__name__)


class PlatformType(Enum):
    DESKTOP = 'desktop'
    JETSON = 'jetson'
    RASPBERRY_PI = 'raspberry_pi'
    INTEL_NUC = 'intel_nuc'
    HAILO = 'hailo'
    UNKNOWN = 'unknown'  # fallback для неопознанных систем