# core/domain/hardware/__init__.py

import logging


from core.domain.hardware.cpu_info import CPUInfo
from core.domain.hardware.gpu_info import GPUInfo
from core.domain.hardware.mps_info import MPSInfo
from core.domain.hardware.npu_info import NPUInfo
from core.domain.hardware.tpu_info import TPUInfo
from core.domain.hardware.ram_info import RAMInfo
from core.domain.hardware.enums import PlatformType

logger = logging.getLogger(__name__)


__all__ = [
    'CPUInfo',
    'GPUInfo',
    'MPSInfo',
    'NPUInfo',
    'TPUInfo',
    'RAMInfo',
    'PlatformType'
]


__version__ = "0.0.0.1"