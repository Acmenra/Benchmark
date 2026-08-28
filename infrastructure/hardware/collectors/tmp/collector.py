# infrastructure/hardware/collectors/tmp/collector.py

import os
import re
import logging
import platform
import subprocess
from pathlib import Path

from core.domain.system.system import TemperatureCapabilitiesInfo


logger = logging.getLogger(__name__)


def collect_temperature() -> TemperatureCapabilitiesInfo:
    """Определение доступности температурных датчиков на текущей системе."""
    cpu_available = _check_cpu_temperature_available()
    gpu_available = _check_gpu_temperature_available()
    
    return TemperatureCapabilitiesInfo(
        cpu_sensor_available=cpu_available,
        gpu_sensor_available=gpu_available
    )


def collect_cpu_temperature_celsius() -> float | None:
    """Вернуть текущую температуру CPU/SoC в градусах Цельсия, если она доступна."""
    system = platform.system()

    if system == "Darwin":
        # На Apple Silicon температура CPU/GPU часто доступна как температура SoC/MPS.
        try:
            from infrastructure.hardware.collectors.gpu.mps_worker import MPSCollector

            temperature = MPSCollector().tmp()
            if temperature is not None:
                return temperature
        except Exception as error:
            logger.debug("Не удалось получить температуру через MPSCollector: %s", error)

    temperature = _get_cpu_temperature_system()
    if temperature is not None:
        return temperature

    temperature = _get_cpu_temperature_thermal_zone()
    if temperature is not None:
        return temperature

    if system == "Linux":
        # На edge-устройствах часть температурных датчиков может быть привязана к NPU.
        try:
            from infrastructure.hardware.collectors.npu import NPUCollector

            return NPUCollector().tmp()
        except Exception as error:
            logger.debug("Не удалось получить температуру через NPUCollector: %s", error)

    return None


def _check_cpu_temperature_available() -> bool:
    """Определение доступности температурных датчиков CPU.
    
    Методы проверки:
    1. WMI на Windows / psutil на Linux/macOS
    2. Чтение из /sys/class/thermal/ (Linux/Jetson/RPi)
    """
    return collect_cpu_temperature_celsius() is not None


def _check_gpu_temperature_available() -> bool:
    """Определение доступности температурных датчиков GPU.

    Методы проверки:
    1. pynvml / nvidia-ml-py (NVIDIA GPU)
    2. nvidia-smi (NVIDIA GPU, fallback без Python-библиотеки)
    3. Платформо-специфичные способы (RPi, Jetson)
    """
    try:
        if _check_nvidia_gpu():
            return True
    except Exception as error:
        logger.debug("Не удалось проверить NVIDIA GPU через pynvml: %s", error)

    try:
        if _check_nvidia_gpu_via_smi():
            return True
    except Exception as error:
        logger.debug("Не удалось проверить NVIDIA GPU через nvidia-smi: %s", error)
    
    try:
        if _check_platform_gpu():
            return True
    except Exception as error:
        logger.debug("Не удалось проверить платформенный GPU-датчик: %s", error)
    
    return False


def _get_cpu_temperature_system() -> float | None:
    """Получение температуры CPU через системные API."""
    try:
        import psutil
        if hasattr(psutil, 'sensors_temperatures'):
            temps = psutil.sensors_temperatures()
            if temps:
                for readings in temps.values():
                    if readings and isinstance(readings, list):
                        for reading in readings:
                            temp = reading.current
                            if _is_valid_temperature(temp):
                                return temp
    except (AttributeError, OSError, ImportError) as error:
        logger.debug("psutil не вернул CPU temperature: %s", error)

    if platform.system() == "Windows":
        return _get_cpu_temperature_windows_wmi()

    return None


def _get_cpu_temperature_windows_wmi() -> float | None:
    """Получение температуры CPU через WMI на Windows."""
    try:
        import wmi
        w = wmi.WMI(namespace="root\\cimv2")
        for item in w.query(
            "SELECT * FROM Win32_PerfFormattedData_Counters_ThermalZoneInformation"
        ):
            if hasattr(item, 'Temperature') and item.Temperature:
                temp_celsius = float(item.Temperature) / 10.0
                if _is_valid_temperature(temp_celsius):
                    return temp_celsius
            if hasattr(item, 'HighPrecisionTemperature') and item.HighPrecisionTemperature:
                temp_celsius = float(item.HighPrecisionTemperature) / 100.0
                if _is_valid_temperature(temp_celsius):
                    return temp_celsius
    except:
        logger.debug("WMI не вернул CPU temperature")

    return None


def _get_cpu_temperature_thermal_zone() -> float | None:
    """Получение температуры CPU из системных тепловых зон Linux."""
    for zone_path in sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp")):
        temperature = _read_temperature_path(zone_path)
        if temperature is not None:
            return temperature

    for zone_path in sorted(Path("/sys/devices/virtual/thermal").glob("thermal_zone*/temp")):
        temperature = _read_temperature_path(zone_path)
        if temperature is not None:
            return temperature

    for hwmon_path in sorted(Path("/sys/class/hwmon").glob("hwmon*/temp*_input")):
        temperature = _read_temperature_path(hwmon_path)
        if temperature is not None:
            return temperature

    # Поиск температурных зон в порядке приоритета
    thermal_zones = [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/devices/virtual/thermal/thermal_zone0/temp",
        "/proc/acpi/thermal_cooling/THM0/temperature",
    ]
    
    for zone_path in thermal_zones:
        temperature = _read_temperature_path(Path(zone_path))
        if temperature is not None:
            return temperature
    
    return None


def _read_temperature_path(path: Path) -> float | None:
    """Прочитать температуру из sysfs/procfs в градусах Цельсия."""
    if not path.exists():
        return None

    try:
        raw_value = path.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError as error:
        logger.debug("Не удалось прочитать temperature path %s: %s", path, error)
        return None

    match = re.search(r"[-+]?\d+(?:\.\d+)?", raw_value)
    if match is None:
        return None

    try:
        temperature = float(match.group(0))
    except ValueError:
        return None

    if temperature >= 1000:
        temperature = temperature / 1000.0

    if _is_valid_temperature(temperature):
        return temperature

    return None


def _check_nvidia_gpu_via_smi() -> bool:
    """Проверка NVIDIA GPU через nvidia-smi (fallback без nvidia-ml-py)."""
    try:
        result = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            stderr=subprocess.DEVNULL,
            timeout=5,
            text=True,
        )
        for line in result.strip().splitlines():
            temp = float(line.strip())
            if _is_valid_temperature(temp):
                return True
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
        ValueError,
        OSError,
    ) as error:
        logger.debug("nvidia-smi не вернул GPU temperature: %s", error)

    return False


def _check_nvidia_gpu() -> bool:
    """Проверка доступности NVIDIA GPU датчика через pynvml.
    """
    try:
        from pynvml import (
            nvmlInit, 
            nvmlDeviceGetCount, 
            nvmlDeviceGetHandleByIndex,
            nvmlDeviceGetTemperature, 
            NVML_TEMPERATURE_GPU
        )
        
        # Инициализация связи с NVIDIA Driver
        nvmlInit()
        
        # Проверка количества GPU в системе
        device_count = nvmlDeviceGetCount()
        
        if device_count > 0:
            # Чтение температуры первого GPU
            handle = nvmlDeviceGetHandleByIndex(0)
            temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
            return _is_valid_temperature(temp)
        
        return False
    except ImportError:
        # pynvml не установлена
        return False
    except Exception as error:
        # NVIDIA Driver не найден/другие ошибки
        logger.debug("pynvml не вернул GPU temperature: %s", error)
        return False


def _check_platform_gpu() -> bool:
    """Проверка доступности GPU датчика на Raspberry Pi и NVIDIA Jetson."""
    system = platform.system()
    
    # RASPBERRY PI 
    if system == "Linux" and os.path.exists("/boot/config.txt"):
        try:
            result = subprocess.check_output(
                "vcgencmd measure_temp",
                shell=True,
                stderr=subprocess.DEVNULL,
                timeout=2
            )
            output = result.decode().strip()
            if "temp=" in output:
                return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as error:
            logger.debug("vcgencmd не вернул GPU temperature: %s", error)
    
    # NVIDIA JETSON 
    if system == "Linux" and os.path.exists("/etc/nv_tegra_release"):
        try:
            tegra_zones = [
                "/sys/devices/virtual/thermal/thermal_zone0/temp",
                "/sys/devices/virtual/thermal/thermal_zone1/temp",
            ]
            for zone_path in tegra_zones:
                if os.path.exists(zone_path):
                    with open(zone_path, "r") as f:
                        temp_raw = f.read().strip()
                        # Для Jetson температуру нужно делить на 1000
                        temp_celsius = float(temp_raw) / 1000.0
                        if _is_valid_temperature(temp_celsius):
                            return True
        except (IOError, ValueError, OSError) as error:
            logger.debug("Jetson thermal zones не вернули GPU temperature: %s", error)
    
    return False


def _is_valid_temperature(temp: float) -> bool:
    """Проверка, является ли значение температуры разумным и реальным (является числом и находится в допустимом диапазоне)."""
    return isinstance(temp, (int, float)) and 0 <= temp < 150
