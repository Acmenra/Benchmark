# core/domain/hardware/mps_info.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class MPSInfo:
    """
    Represents static Apple Silicon (M-series) specific hardware information.

    Used exclusively on macOS to capture details about the Neural Engine and
    Unified Memory Architecture, which are critical for Metal Performance Shaders optimization.

    Attributes:
        unified_memory_gb (float | None): Total unified memory (RAM + VRAM) in Gigabytes.
        neural_engine_cores (int | None): Number of dedicated Neural Engine cores.

    Note:
        - This class is only populated on macOS with Apple Silicon (ARM64).
        - On non-Apple systems, these fields will remain `None`.
    """
    unified_memory_gb: float | None = None
    neural_engine_cores: int | None = None