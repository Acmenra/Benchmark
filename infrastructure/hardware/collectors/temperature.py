# infrastructure/hardware/collectors/temperature.py

import logging

logger = logging.getLogger(__name__)

import os
import platform
import subprocess

from core.entities.hardware import TemperatureCapabilitiesInfo

# TODO прибрать!

def collect_temperature() -> TemperatureCapabilitiesInfo:
    """Определение доступности температурных датчиков на текущей системе."""
    cpu_available = _check_cpu_temperature_available()
    gpu_available = _check_gpu_temperature_available()
    
    return TemperatureCapabilitiesInfo(
        cpu_sensor_available=cpu_available,
        gpu_sensor_available=gpu_available
    )


def _check_cpu_temperature_available() -> bool:
    """Определение доступности температурных датчиков CPU.
    
    Методы проверки:
    1. WMI на Windows / psutil на Linux/macOS
    2. Чтение из /sys/class/thermal/ (Linux/Jetson/RPi)
    """
    try:
        # Метод 1: системные API (Windows WMI, Linux psutil)
        temps = _get_cpu_temperature_system()
        if temps is not None:
            return True
    except Exception:
        pass
    
    try:
        # Метод 2: через файловую систему thermal zones
        temps = _get_cpu_temperature_thermal_zone()
        if temps is not None:
            return True
    except Exception:
        pass
    
    return False


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
    except Exception:
        pass

    try:
        if _check_nvidia_gpu_via_smi():
            return True
    except Exception:
        pass
    
    try:
        if _check_platform_gpu():
            return True
    except Exception:
        pass
    
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
    except (AttributeError, OSError, ImportError):
        pass

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
    except (ImportError, AttributeError, OSError):
        pass

    return None


def _get_cpu_temperature_thermal_zone() -> float | None:
    """Получение температуры CPU из системных тепловых зон Linux."""

    # Поиск температурных зон в порядке приоритета
    thermal_zones = [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/devices/virtual/thermal/thermal_zone0/temp",
        "/proc/acpi/thermal_cooling/THM0/temperature",
    ]
    
    for zone_path in thermal_zones:
        try:
            if os.path.exists(zone_path):
                with open(zone_path, "r") as f:
                    temp_raw = f.read().strip()
                    # В Linux температуру нужно делить на 1000
                    temp_celsius = float(temp_raw) / 1000.0
                    if _is_valid_temperature(temp_celsius):
                        return temp_celsius
        except (IOError, ValueError, OSError):
            continue
    
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
    ):
        pass

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
    except Exception:
        # NVIDIA Driver не найден/другие ошибки
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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
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
        except (IOError, ValueError, OSError):
            pass
    
    return False


def _is_valid_temperature(temp: float) -> bool:
    """Проверка, является ли значение температуры разумным и реальным (является числом и находится в допустимом диапазоне)."""
    return isinstance(temp, (int, float)) and 0 <= temp < 150