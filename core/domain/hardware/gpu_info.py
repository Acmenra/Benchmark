# core/domain/hardware/gpu_info.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class GPUInfo:
    """
    Represents static Graphics Processing Unit (GPU) information.

    Captures the capabilities and configuration of the primary or dedicated
    graphics accelerator, crucial for determining CUDA/OpenCL compatibility.

    Attributes:
        name (str | None): Commercial name of the GPU (e.g., "NVIDIA GeForce RTX 4090").
        memory_mb (int | None): Total dedicated video memory (VRAM) in Megabytes.
        driver_version (str | None): Version string of the installed GPU driver.
        has_cuda (bool): Flag indicating if the GPU supports NVIDIA CUDA.
        cuda_version (str | None): Installed CUDA toolkit version (e.g., "12.1"), if applicable.

    Note:
        - For Apple Silicon, this may represent the integrated GPU, but `MPSInfo` is preferred.
        - `memory_mb` does not include system RAM shared with integrated graphics on some architectures.
    """

    name: str | None = None
    memory_mb: int | None = None
    driver_version: str | None = None

    has_cuda: bool = False
    cuda_version: str | None = None