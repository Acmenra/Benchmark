# core/domain/hardware/enums.py

import logging
from enum import Enum


logger = logging.getLogger(__name__)


class PlatformType(Enum):
    """
    Enumeration of supported hardware deployment platforms.

    Defines the target environment to allow the benchmark suite to apply
    platform-specific hardware collection logic and optimizations.

    Attributes:
        DESKTOP: Standard desktop or laptop computers (Windows, macOS, Linux).
        JETSON: NVIDIA Jetson embedded AI computers (e.g., Orin, Nano).
        RASPBERRY_PI: Raspberry Pi single-board computers.
        INTEL_NUC: Intel NUC or similar mini-PCs with integrated/openvino NPUs.
        HAILO: Systems equipped with Hailo AI accelerators (e.g., Hailo-8).
        UNKNOWN: Fallback value for unrecognized or unsupported systems.

    Note:
        - Platform detection is usually performed automatically at startup.
        - Adding new platforms requires updating the hardware collector factory.
    """
    DESKTOP = 'desktop'
    JETSON = 'jetson'
    RASPBERRY_PI = 'raspberry_pi'
    INTEL_NUC = 'intel_nuc'
    HAILO = 'hailo'
    UNKNOWN = 'unknown'  # fallback для неопознанных систем