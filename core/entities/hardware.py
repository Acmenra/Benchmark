# hardware/entities.py

from dataclasses import dataclass

from core.enums.hardware import HardwarePlatform


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


@dataclass(slots=True, frozen=True)
class GPUInfo:
    """Информация о графическом процессоре.

    Attributes:
        name (str | None): Название модели GPU.
        memory_mb (int | None): Объем видеопамяти в мегабайтах.
        driver_version (str | None): Версия установленного драйвера GPU.
        cuda_version (str | None): Версия CUDA, если доступна.
    """

    name: str | None
    memory_mb: int | None
    driver_version: str | None
    cuda_version: str | None


@dataclass(slots=True, frozen=True)
class TemperatureCapabilitiesInfo:
    """Информация о доступности датчиков температуры на системе.
    
    Attributes:
        cpu_sensor_available (bool): True, если система может снимать показания температуры процессора. 
        gpu_sensor_available (bool): True, если система может снимать показания температуры видеокарты.
    """
    cpu_sensor_available: bool
    gpu_sensor_available: bool


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
        temperature (TemperatureCapabilitiesInfo | None): Информация о доступности датчиков температуры.
    """
        
    platform: HardwarePlatform | None
    device_name: str | None
    
    cpu: CPUInfo | None
    gpu: GPUInfo | None 
    os: OSInfo | None
    temperature: TemperatureCapabilitiesInfo | None
    
    ...