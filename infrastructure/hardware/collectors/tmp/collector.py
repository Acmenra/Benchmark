# infrastructure/hardware/collectors/tmp/collector.py

import os
import re
import logging
import platform
import subprocess
from pathlib import Path
from core.domain.system.system import TemperatureCapabilitiesInfo

from pynvml import nvmlInit, nvmlDeviceGetCount, nvmlDeviceGetHandleByIndex, nvmlDeviceGetTemperature, NVML_TEMPERATURE_GPU


logger = logging.getLogger(__name__)


def collect_temperature() -> TemperatureCapabilitiesInfo:
    """
    Determines the availability of thermal sensors on the current system.

    Probes both CPU and GPU subsystems to build a boolean capability profile.
    This is used by the root `HardwareCollector` to populate the `SystemInfo`
    aggregate, preventing the runner from polling inaccessible sensors.

    Returns:
        TemperatureCapabilitiesInfo: A domain object containing boolean flags
                                     `cpu_sensor_available` and `gpu_sensor_available`.
    """
    cpu_available = _check_cpu_temperature_available()
    gpu_available = _check_gpu_temperature_available()
    
    return TemperatureCapabilitiesInfo(
        cpu_sensor_available=cpu_available,
        gpu_sensor_available=gpu_available
    )


def collect_cpu_temperature_celsius() -> float | None:
    """
    Retrieves the current CPU/SoC temperature in degrees Celsius.

    Executes a prioritized, cross-platform fallback chain:
    1. macOS: Attempts to read via `MPSWorker` (Apple Silicon SoC/MPS temperature).
    2. System APIs: Falls back to `psutil.sensors_temperatures()` or Windows WMI.
    3. Linux sysfs: Scans `/sys/class/thermal/` and `/sys/class/hwmon/`.
    4. Edge Devices: Attempts to read via `NPUCollector` on Linux edge platforms.

    Returns:
        float | None: The temperature in Celsius, or `None` if no valid sensor is found.
    """
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
        try:
            from infrastructure.hardware.collectors.npu import NPUCollector

            return NPUCollector().tmp()
        except Exception as error:
            logger.debug("Не удалось получить температуру через NPUCollector: %s", error)

    return None


def _check_cpu_temperature_available() -> bool:
    """
    Verifies CPU sensor accessibility.

    Methods:
    1. WMI on Windows / psutil on Linux/macOS.
    2. Reading from `/sys/class/thermal/` (Linux/Jetson/RPi).

    Returns:
        bool: `True` if `collect_cpu_temperature_celsius()` returns a valid float.
    """
    return collect_cpu_temperature_celsius() is not None


def _check_gpu_temperature_available() -> bool:
    """
    Verifies GPU sensor accessibility.

    Methods:
    1. `pynvml` / `nvidia-ml-py` (NVIDIA GPU).
    2. `nvidia-smi` (NVIDIA GPU, fallback without Python library).
    3. Platform-specific methods (RPi `vcgencmd`, Jetson Tegra zones).

    Returns:
        bool: `True` if any GPU temperature source is successfully validated.
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
    """
    Retrieves CPU temperature via system-level APIs (`psutil` or WMI).

    Returns:
        float | None: The temperature in Celsius, or `None` if unavailable.
    """
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
    """
    Retrieves CPU temperature via WMI on Windows.

    Returns:
        float | None: The temperature in Celsius, or `None` if the WMI query fails.
    """
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
    """
    Retrieves CPU temperature from Linux system thermal zones.

    Scans `/sys/class/thermal`, `/sys/devices/virtual/thermal`, and
    `/sys/class/hwmon` for valid temperature nodes.

    Returns:
        float | None: The temperature in Celsius, or `None` if no valid zone is found.
    """
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
    """
    Reads and parses a temperature value from a sysfs/procfs file.

    Handles automatic conversion from millikelvins to Celsius if the raw
    value is `>= 1000`. Validates the result using `_is_valid_temperature()`.

    Args:
        path: The Path object pointing to the thermal zone file.

    Returns:
        float | None: The temperature in Celsius, or `None` if the file is
                      missing, unreadable, or contains invalid data.
    """
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
    """
    Checks NVIDIA GPU availability via the `nvidia-smi` CLI tool.

    Acts as a fallback when the `pynvml` Python library is not installed.

    Returns:
        bool: `True` if `nvidia-smi` returns a valid GPU temperature.
    """
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
    """
    Checks NVIDIA GPU availability via the `pynvml` library.

    Initializes the NVML driver and attempts to read the temperature of
    the first detected GPU.

    Returns:
        bool: `True` if `pynvml` successfully returns a valid GPU temperature.
    """
    try:
        nvmlInit()
        
        device_count = nvmlDeviceGetCount()
        
        if device_count > 0:
            handle = nvmlDeviceGetHandleByIndex(0)
            temp = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
            return _is_valid_temperature(temp)
        
        return False
    except ImportError:
        return False
    except Exception as error:
        logger.debug("pynvml не вернул GPU temperature: %s", error)
        return False


def _check_platform_gpu() -> bool:
    """
    Checks GPU sensor availability on Raspberry Pi and NVIDIA Jetson.

    Methods:
    - RPi: Uses `vcgencmd measure_temp`.
    - Jetson: Reads Tegra thermal zones from sysfs.

    Returns:
        bool: `True` if a platform-specific GPU temperature is successfully read.
    """
    system = platform.system()
    
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
    """
    Sanity check for temperature readings.

    Validates that the temperature is a numeric type and falls within a
    physically reasonable range for computing hardware (0°C to 150°C),
    filtering out erroneous or uninitialized sensor readings.

    Args:
        temp: The temperature value to validate.

    Returns:
        bool: `True` if `0 <= temp < 150`.
    """

    return isinstance(temp, (int, float)) and 0 <= temp < 150
