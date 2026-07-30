# core/domain/hardware/tpu_info.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class TPUInfo:
    """
    Represents static Tensor Processing Unit (TPU) information.

    Captures details about Google Coral Edge TPU or similar dedicated tensor accelerators
    connected via USB or PCIe.

    Attributes:
        name (str | None): Commercial name of the TPU (e.g., "Google Coral USB Accelerator").
        device_path (str | None): System device path (e.g., "/dev/apex_0" or USB bus ID).
        driver_version (str | None): Version of the Edge TPU runtime library.
        max_temperature_c (float | None): Maximum safe operating temperature in Celsius.

    Note:
        - Primarily used for edge devices running Edge TPU runtime.
        - `device_path` is useful for multi-TPU setups to ensure correct device binding.
    """
    name: str | None = None
    device_path: str | None = None
    driver_version: str | None = None
    max_temperature_c: float | None = None