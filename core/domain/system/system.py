# core/domain/system/__init__.py

import logging
from dataclasses import dataclass

from core.domain.hardware.enums import PlatformType
from core.domain.operating_system.operating_system import OSInfo
from core.domain.hardware import CPUInfo, GPUInfo, NPUInfo, TPUInfo


logger = logging.getLogger(__name__)


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

    platform: PlatformType | None
    device_name: str | None

    cpu: CPUInfo | None
    gpu: GPUInfo | None
    npu: NPUInfo | None
    tpu: TPUInfo | None
    os: OSInfo | None
    temperature: TemperatureCapabilitiesInfo | None
    ...