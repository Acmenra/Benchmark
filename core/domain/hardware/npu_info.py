# core/domain/hardware/npu_info.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class NPUInfo:
    """
    Represents static Neural Processing Unit (NPU) information.

    Captures details about dedicated AI accelerators (e.g., Rockchip RKNN, Intel NPU, Hailo)
    used for edge inference.

    Attributes:
        name (str | None): Commercial name or codename of the NPU (e.g., "Hailo-8", "Intel AI Boost").
        operations_per_second (str | None): Peak performance metric (e.g., "26 TOPS").
        driver_version (str | None): Version of the NPU driver or firmware.

    Note:
        - Highly platform-dependent. May be `None` on systems without dedicated NPUs.
        - `operations_per_second` is a string to accommodate varying vendor formats (e.g., "10 TOPS", "5000 GOPS").
    """
    name: str | None = None
    operations_per_second: str | None = None
    driver_version: str | None = None