# core/domain/hardware/ram_info.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class RAMInfo:
    """
    Represents static system memory (RAM) information.

    Provides details about the main system memory, which is critical for
    determining if large models can be loaded without swapping.

    Attributes:
        total_mb (int | None): Total physical memory installed in Megabytes.
        type (str | None): Memory technology type (e.g., "DDR4", "LPDDR5", "Unified Memory").
        speed_mhz (float | None): Effective clock speed of the memory in Megahertz (MHz).

    Note:
        - `speed_mhz` might be `None` on some operating systems (like macOS or restricted Linux containers)
          due to lack of low-level hardware access permissions.
    """
    total_mb: int | None = None
    type: str | None = None
    speed_mhz: float | None = None