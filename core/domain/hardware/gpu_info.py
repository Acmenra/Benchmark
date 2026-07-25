# core/domain/hardware/gpu_info.py

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class GPUInfo:
    """Информация о графическом процессоре.

    Attributes:
        name (str | None): Название модели GPU.
        memory_mb (int | None): Объем видеопамяти в мегабайтах.
        driver_version (str | None): Версия установленного драйвера GPU.
        cuda_version (str | None): Версия CUDA, если доступна.
    """

    name: str | None = None
    memory_mb: int | None = None
    driver_version: str | None = None

    has_cuda: bool = False
    cuda_version: str | None = None