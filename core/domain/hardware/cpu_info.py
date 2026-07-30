# core/domain/hardware/cpu_info.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class CPUInfo:
    """
    Represents static Central Processing Unit (CPU) information.

    This dataclass captures the fundamental characteristics of the host processor,
    used for benchmark reporting and platform-specific optimization routing.

    Attributes:
        name (str | None): Full commercial name of the processor (e.g., "Apple M4 Pro", "Intel Core i7-13700K").
        architecture (str | None): Instruction set architecture (e.g., "x86_64", "ARM64", "aarch64").
        physical_cores (int | None): Number of physical CPU cores.
        logical_cores (int | None): Number of logical CPU cores (may equal physical_cores if no hyperthreading/SMT).
        max_frequency_mhz (float | None): Maximum clock frequency of the CPU in Megahertz (MHz).

    Note:
        - On Apple Silicon, `physical_cores` and `logical_cores` are typically identical.
        - `max_frequency_mhz` may be `None` on some operating systems due to privilege restrictions.
    """

    name: str | None
    architecture: str | None
    physical_cores: int | None
    logical_cores: int | None
    max_frequency_mhz: float | None