# core/domain/system/system.py

import logging
from dataclasses import dataclass

from core.domain.hardware.enums import PlatformType
from core.domain.operating_system.operating_system import OSInfo
from core.domain.hardware import CPUInfo, GPUInfo, NPUInfo, TPUInfo, RAMInfo

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class TemperatureCapabilitiesInfo:
    """
    Represents the availability of thermal sensors on the host system.

    This dataclass acts as a capability flag container, indicating whether
    the benchmark runner can successfully query temperature metrics for
    specific hardware components during execution.

    Attributes:
        cpu_sensor_available (bool): True if CPU temperature telemetry can be read.
        gpu_sensor_available (bool): True if GPU temperature telemetry can be read.

    Note:
        - Sensor availability is highly dependent on the host operating system,
          driver support, and execution privileges (e.g., root/admin access).
        - A value of `False` does not necessarily mean the hardware lacks sensors,
          but rather that the current execution environment cannot access them.
    """
    cpu_sensor_available: bool
    gpu_sensor_available: bool


@dataclass(slots=True, frozen=True)
class SystemInfo:
    """
    Comprehensive snapshot of the host system's hardware and software environment.

    This immutable dataclass aggregates all relevant system characteristics
    detected at the start of a benchmark run. It is primarily used for
    diagnostic reporting, environment validation, and ensuring the
    reproducibility of benchmark results across different machines.

    Attributes:
        platform (PlatformType | None): The identified hardware platform category
                                        (e.g., DESKTOP, JETSON, RASPBERRY_PI).
        device_name (str | None): The commercial or system-reported name of the device.
        cpu (CPUInfo | None): Detailed static information about the central processor.
        gpu (GPUInfo | None): Detailed static information about the primary graphics accelerator.
        npu (NPUInfo | None): Information about dedicated Neural Processing Units, if present.
        tpu (TPUInfo | None): Information about Tensor Processing Units, if present.
        ram (RAMInfo | None): Static information about the system's main memory.
        os (OSInfo | None): Details about the host operating system and kernel.
        temperature (TemperatureCapabilitiesInfo | None): Flags indicating thermal sensor accessibility.

    Note:
        - All fields are optional (`None`) to gracefully handle environments where
          specific hardware or telemetry is unavailable or restricted.
        - The `frozen=True` flag ensures the system profile remains immutable
          throughout the benchmark lifecycle, guaranteeing data integrity for reports.
    """
    platform: PlatformType | None
    device_name: str | None

    cpu: CPUInfo | None
    gpu: GPUInfo | None
    npu: NPUInfo | None
    tpu: TPUInfo | None
    ram: RAMInfo | None
    os: OSInfo | None
    temperature: TemperatureCapabilitiesInfo | None

