# core/domain/hardware/cpu_info.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class CPUInfo:
    """Информация о ЦП.

    Attributes:
        name (str | None): Полное название модели процессора.
        architecture (str | None): Архитектура процессора (например, x86_64, ARM64).
        physical_cores (int | None): Количество физических ядер процессора.
        logical_cores (int | None): Количество логических ядер.
        max_frequency (flaot | None): Максимальная частота процессора в МГц.
    """

    name: str | None
    architecture: str | None
    physical_cores: int | None
    logical_cores: int | None
    max_frequency_mhz: float | None