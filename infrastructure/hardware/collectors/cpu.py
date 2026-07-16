# infrastructure/hardware/collectors/cpu.py

import os
import time
import psutil
import platform
import subprocess
from pathlib import Path

from core.entities.hardware import CPUInfo
from core.entities.metrics import DataPoint, MetricStatistics
from infrastructure.hardware.collectors.base import BaseCollector, is_valid_temperature


class CPUCollector(BaseCollector): # TODO это единая точка правды о СPU
    """Сборщик статической информации и runtime-метрик CPU."""

    # TDOO - оно инитается (как раз получение инфы о железе),

    def get_hardware_info(self) -> CPUInfo:
        """Возвращает статическую информацию о процессоре."""
        return collect_cpu()

    def get_metrics(self) -> ...:
        """Возвращает загрузку процессора."""
        cpu_utilization = MetricStatistics(unit="percent")
        cpu_utilization.history.append(
            DataPoint(
                time_in_ms=int(time.time() * 1000),
                value=psutil.cpu_percent(interval=0.1),
            )
        )

        return cpu_utilization

    def is_temperature_sensor_available(self) -> bool:
        """Определяет доступность температурных датчиков CPU."""
        return get_cpu_temperature() is not None

    def tmp(self) -> float | None:
        """Возвращает текущую температуру CPU в °C."""
        return get_cpu_temperature()


def collect_cpu() -> CPUInfo:
    """Сбор базовой информации о процессоре."""
    return CPUInfo(
        name=_collect_cpu_name(),
        architecture=_empty_to_none(platform.machine()),
        physical_cores=psutil.cpu_count(logical=False),
        logical_cores=psutil.cpu_count(logical=True) or os.cpu_count(),
        max_frequency_mhz=_collect_max_frequency_mhz(),
        temperature_sensor_available=is_temperature_sensor_available(),
    )


def is_temperature_sensor_available() -> bool:
    """Определяет доступность температурных датчиков CPU."""
    return get_cpu_temperature() is not None


def get_cpu_temperature() -> float | None:
    """Получение температуры CPU через доступные системные источники."""
    try:
        temp = _get_cpu_temperature_system()
        if temp is not None:
            return temp
    except Exception:
        pass

    try:
        return _get_cpu_temperature_thermal_zone()
    except Exception:
        pass

    return None


def _get_cpu_temperature_system() -> float | None:
    """Получение температуры CPU через системные API."""
    try:
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if temps:
                for readings in temps.values():
                    if readings and isinstance(readings, list):
                        for reading in readings:
                            temp = reading.current
                            if is_valid_temperature(temp):
                                return temp
    except (AttributeError, OSError):
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
            if hasattr(item, "Temperature") and item.Temperature:
                temp_celsius = float(item.Temperature) / 10.0
                if is_valid_temperature(temp_celsius):
                    return temp_celsius
            if hasattr(item, "HighPrecisionTemperature") and item.HighPrecisionTemperature:
                temp_celsius = float(item.HighPrecisionTemperature) / 100.0
                if is_valid_temperature(temp_celsius):
                    return temp_celsius
    except (ImportError, AttributeError, OSError):
        pass

    return None


def _get_cpu_temperature_thermal_zone() -> float | None:
    """Получение температуры CPU из системных тепловых зон Linux."""
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
                    temp_celsius = float(temp_raw) / 1000.0
                    if is_valid_temperature(temp_celsius):
                        return temp_celsius
        except (IOError, ValueError, OSError):
            continue

    return None


def _collect_cpu_name() -> str | None:
    """Получение названия модели процессора с учетом текущей ОС."""
    # Сначала пробуем внешний пакет: он часто дает самое читаемое имя CPU.
    cpuinfo_name = _collect_cpu_name_from_cpuinfo()
    if cpuinfo_name is not None:
        return cpuinfo_name

    system = platform.system()

    if system == "Darwin":
        return _collect_macos_cpu_name()
    if system == "Linux":
        return _collect_linux_cpu_name()
    if system == "Windows":
        return _empty_to_none(platform.processor())

    return _empty_to_none(platform.processor())


def _collect_cpu_name_from_cpuinfo() -> str | None:
    """Получить название процессора через py-cpuinfo, если пакет установлен."""
    try:
        import cpuinfo
    except ImportError:
        return None

    try:
        cpu_info = cpuinfo.get_cpu_info()
    except Exception:
        return None

    return _empty_to_none(cpu_info.get("brand_raw", ""))


def _collect_macos_cpu_name() -> str | None:
    try:
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return _empty_to_none(platform.processor())

    return _empty_to_none(result.stdout)


def _collect_linux_cpu_name() -> str | None:
    # На Linux, Raspberry Pi и Jetson CPU обычно описан в /proc/cpuinfo.
    cpuinfo = _read_text(Path("/proc/cpuinfo"))
    for line in cpuinfo.splitlines():
        if _is_cpu_name_line(line):
            _, _, value = line.partition(":")
            cpu_name = _empty_to_none(value)
            if cpu_name is not None:
                return cpu_name

    # Если /proc/cpuinfo не дал понятного имени, пробуем lscpu.
    lscpu_name = _collect_linux_cpu_name_from_lscpu()
    if lscpu_name is not None:
        return lscpu_name

    # Последний безопасный fallback: пусть имя будет неполным, но не пустым.
    return _empty_to_none(platform.processor())


def _is_cpu_name_line(line: str) -> bool:
    """Проверяем, содержит ли строка /proc/cpuinfo название CPU/платы."""
    normalized_line = line.lower()
    key, _, value = normalized_line.partition(":")
    key = key.strip()
    value = value.strip()

    if key in {"model name", "hardware", "model"}:
        return bool(value)

    # На ARM-платформах Processor иногда содержит описание CPU,
    # а на обычном Linux processor часто содержит только номер ядра.
    return key == "processor" and bool(value) and not value.isdigit()


def _collect_linux_cpu_name_from_lscpu() -> str | None:
    """Получаем название CPU через lscpu, если команда доступна."""
    try:
        result = subprocess.run(
            ["lscpu"],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    for line in result.stdout.splitlines():
        if line.startswith("Model name:"):
            _, _, value = line.partition(":")
            return _empty_to_none(value)
    return None


def _collect_max_frequency_mhz() -> float | None:
    """Получить максимальную частоту CPU в МГц, если она доступна."""
    frequency = psutil.cpu_freq()
    if frequency is None:
        return None

    # На некоторых платформах max недоступен или равен 0.
    # В таком случае используем текущую частоту как fallback.
    if frequency.max and frequency.max > 0:
        return float(frequency.max)
    if frequency.current and frequency.current > 0:
        return float(frequency.current)
    return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _empty_to_none(value: str) -> str | None:
    """Преобразовать пустую строку в None для отчета."""
    stripped_value = value.strip()
    return stripped_value or None
