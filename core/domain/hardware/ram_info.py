# core/domain/hardware/ram_info.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class RAMInfo:
    """
    Статическая информация об оперативной памяти (RAM).

    Attributes:
        total_mb: Общий объем оперативной памяти в мегабайтах.
        type: Тип памяти (например, "DDR4", "LPDDR5", "Unified Memory" для Apple).
        speed_mhz: Тактовая частота памяти в МГц (опционально, сложно получить кроссплатформенно).
    """
    total_mb: int | None = None
    type: str | None = None
    speed_mhz: float | None = None