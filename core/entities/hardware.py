# core/entities/hardware.py

import logging

logger = logging.getLogger(__name__)

from dataclasses import dataclass

from core.enums.hardware import PlatformType


@dataclass(slots=True, frozen=True)
class CPUInfo:  
    """Информация о ЦП.

    Attributes:
        name (str | None): Полное название модели процессора.
        architecture (str | None): Архитектура процессора (например, x86_64, ARM64).
        physical_cores (int | None): Количество физических ядер процессора.
        logical_cores (int | None): Количество логических ядер.
        max_frequency (flaot | None): Максимальная частота процессора в МГц.
        temperature_sensor_available (bool): True, если доступен датчик температуры CPU.
    """

    name: str | None
    architecture: str | None
    physical_cores: int | None
    logical_cores: int | None
    max_frequency_mhz: float | None
    temperature_sensor_available: bool = False


@dataclass(slots=True, frozen=True)
class GPUInfo:
    """Информация о графическом процессоре.

    Attributes:
        name (str | None): Название модели GPU.
        memory_mb (int | None): Объем видеопамяти в мегабайтах.
        driver_version (str | None): Версия установленного драйвера GPU.
        cuda_version (str | None): Версия CUDA, если доступна.
        temperature_sensor_available (bool): True, если доступен датчик температуры GPU.
    """

    name: str | None = None
    memory_mb: int | None = None
    driver_version: str | None = None

    has_cuda: bool = False
    cuda_version: str | None = None
    temperature_sensor_available: bool = False


@dataclass(slots=True, frozen=True)
class OSInfo:
    """Информация об операционной системе.

    Attributes:
        system (str | None): Название операционной системы.
        release (str | None): Версия выпуска операционной системы.
        kernel (str | None): Версия ядра операционной системы.
        architecture (str | None): Архитектура системы.
    """

    system: str | None   
    release: str | None     
    kernel: str | None
    architecture: str | None


@dataclass(slots=True, frozen=True)
class SystemInfo:
    """Полная информация о тестовой системе.

    Используется для сохранения характеристик устройства,
    на котором выполняется бенчмарк.

    Attributes:
        platform (HardwarePlatform | None): Тип аппаратной платформы.
        device_name (str | None): Название устройства.
        cpu (CPUInfo | None): Информация о центральном процессоре.
        gpu (GPUInfo | None): Информация о графическом процессоре.
        os (OSInfo | None): Информация об операционной системе.
    """
        
    platform: PlatformType | None
    device_name: str | None
    
    cpu: CPUInfo | None
    gpu: GPUInfo | None 
    os: OSInfo | None
    
    ...