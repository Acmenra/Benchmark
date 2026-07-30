# core/domain/operating_system/operating_system.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class OSInfo:
    """
    Represents static information about the host Operating System.

    This dataclass captures the fundamental characteristics of the OS environment
    in which the benchmark is executed. This data is primarily used for
    diagnostic reporting, platform-specific logic routing, and ensuring
    reproducibility of benchmark results across different environments.

    Attributes:
        system (str | None): The name of the operating system (e.g., "Darwin", "Linux", "Windows").
        release (str | None): The release version of the operating system (e.g., "23.4.0", "22.04").
        kernel (str | None): The specific version of the OS kernel (e.g., "23.4.0", "5.15.0-100-generic").
        architecture (str | None): The machine hardware architecture (e.g., "x86_64", "arm64", "aarch64").

    Note:
        - All fields are optional (`None`) to gracefully handle environments where
          certain system information is restricted or unavailable (e.g., heavily
          containerized or sandboxed environments).
        - The `frozen=True` flag ensures the OS information remains immutable after
          initial detection, guaranteeing consistency throughout the benchmark run.
    """
    system: str | None
    release: str | None
    kernel: str | None
    architecture: str | None