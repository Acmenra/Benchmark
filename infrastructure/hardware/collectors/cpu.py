# infrastructure/hardware/collectors/cpu.py

import os
import time
import psutil
import logging
import platform
import subprocess
from pathlib import Path

from core.domain.hardware import CPUInfo
from core.domain.config.system import SystemInfoConfig
from core.domain.metrics import MetricStatistics, DataPoint
from infrastructure.hardware.collectors.base import BaseCollector


logger = logging.getLogger(__name__)


class CPUCollector(BaseCollector):
    """Сборщик статической информации и runtime-метрик CPU."""

    def __init__(self, system_info_config: SystemInfoConfig | None = None) -> None:
        super().__init__(
            system_info_config
            or SystemInfoConfig(
                collect_gpu=False,
                collect_power=False,
                collect_temperature=False,
            )
        )
        # Статическую информацию получаем один раз.
        self._hardware_info = collect_cpu()


    def info(self) -> CPUInfo:
        """Вернуть статическую информацию о процессоре."""
        return self.get_hardware_info()

    def tmp(self) -> None:
        """Температура CPU собирается отдельным temperature collector."""
        return None

    def frq(self) -> float | None:
        """Вернуть текущую доступную частоту CPU в МГц."""
        return _collect_max_frequency_mhz()

    def prsnt(self) -> MetricStatistics:
        """Вернуть текущий процент загрузки CPU."""
        return self.get_metrics()

    def get_hardware_info(self) -> CPUInfo:
        """Возвращает статическую информацию о процессоре."""
        return self._hardware_info

    def prepare_metrics_collection(self) -> None:
        """
        Инициализирует неблокирующее измерение CPU.

        Этот метод и последующие get_metrics() должны вызываться
        из одного и того же потока.
        """
        psutil.cpu_percent(interval=None)

    def get_metrics(self) -> MetricStatistics:
        """Возвращает один неблокирующий замер загрузки CPU."""
        cpu_utilization = MetricStatistics(unit="percent")

        cpu_utilization.history.append(
            DataPoint(
                time_in_ms=time.time_ns() // 1_000_000,
                value=psutil.cpu_percent(interval=None),
            )
        )

        return cpu_utilization


def collect_cpu() -> CPUInfo:
    """Сбор базовой информации о процессоре."""
    return CPUInfo(
        name=_collect_cpu_name(),
        architecture=_empty_to_none(platform.machine()),
        physical_cores=psutil.cpu_count(logical=False),
        logical_cores=psutil.cpu_count(logical=True) or os.cpu_count(),
        max_frequency_mhz=_collect_max_frequency_mhz(),
    )


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
