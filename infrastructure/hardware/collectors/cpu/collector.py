# infrastructure/hardware/collectors/cpu/collector.py

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
from infrastructure.hardware.collectors.base import BaseHardwareCollector
from infrastructure.utils.utils import empty_to_none, read_text


logger = logging.getLogger(__name__)


class CPUCollector(BaseHardwareCollector):
    """Сборщик метрик CPU. Реализует контракт BaseHardwareCollector."""

    def __init__(self, system_info_config: SystemInfoConfig) -> None:
        super().__init__(system_info_config)

        psutil.cpu_percent(interval=None)

        self._hardware_info = self._gather_static_info()

    def get_hardware_info(self) -> CPUInfo:
        """Возвращает кэшированную статическую информацию о процессоре."""
        return self._hardware_info

    def get_metrics(self) -> MetricStatistics:
        """
        Возвращает снимок текущей загрузки CPU.
        Вызывается из фонового потока оркестратора.
        """
        metric = MetricStatistics(unit="percent")
        metric.history.append(
            DataPoint(
                # ИСПРАВЛЕНО: используем монотонный perf_counter для высокой точности
                time_in_ms=time.perf_counter() * 1000.0,
                value=psutil.cpu_percent(interval=None),
            )
        )
        return metric

    def _gather_static_info(self) -> CPUInfo:
        """Внутренний метод для первичного сбора характеристик CPU."""
        return CPUInfo(
            name=self._collect_cpu_name(),
            architecture=empty_to_none(platform.machine()),
            physical_cores=psutil.cpu_count(logical=False),
            logical_cores=psutil.cpu_count(logical=True) or os.cpu_count(),
            max_frequency_mhz=self._collect_max_frequency_mhz(),
        )

    def _collect_cpu_name(self) -> str | None:
        """Получение названия модели процессора с учетом текущей ОС."""
        cpuinfo_name = self._collect_cpu_name_from_cpuinfo()
        if cpuinfo_name is not None:
            return cpuinfo_name

        system = platform.system()
        if system == "Darwin":
            return self._collect_macos_cpu_name()
        if system == "Linux":
            return self._collect_linux_cpu_name()
        if system == "Windows":
            return empty_to_none(platform.processor())

        return empty_to_none(platform.processor())

    def _collect_cpu_name_from_cpuinfo(self) -> str | None:
        try:
            import cpuinfo
            cpu_info = cpuinfo.get_cpu_info()
            return empty_to_none(cpu_info.get("brand_raw", ""))
        except (ImportError, Exception):
            return None

    def _collect_macos_cpu_name(self) -> str | None:
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                check=True, capture_output=True, text=True, timeout=3,
            )
            return empty_to_none(result.stdout)
        except (OSError, subprocess.SubprocessError):
            return empty_to_none(platform.processor())

    def _collect_linux_cpu_name(self) -> str | None:
        cpuinfo_text = read_text(Path("/proc/cpuinfo"))
        for line in cpuinfo_text.splitlines():
            if self._is_cpu_name_line(line):
                _, _, value = line.partition(":")
                cpu_name = empty_to_none(value)
                if cpu_name is not None:
                    return cpu_name

        lscpu_name = self._collect_linux_cpu_name_from_lscpu()
        if lscpu_name is not None:
            return lscpu_name

        return empty_to_none(platform.processor())

    def _is_cpu_name_line(self, line: str) -> bool:
        normalized_line = line.lower()
        key, _, value = normalized_line.partition(":")
        key = key.strip()
        value = value.strip()

        if key in {"model name", "hardware", "model"}:
            return bool(value)
        return key == "processor" and bool(value) and not value.isdigit()

    def _collect_linux_cpu_name_from_lscpu(self) -> str | None:
        try:
            result = subprocess.run(
                ["lscpu"], check=True, capture_output=True, text=True, timeout=3,
            )
            for line in result.stdout.splitlines():
                if line.startswith("Model name:"):
                    _, _, value = line.partition(":")
                    return empty_to_none(value)
        except (OSError, subprocess.SubprocessError):
            pass
        return None

    def _collect_max_frequency_mhz(self) -> float | None:
        frequency = psutil.cpu_freq()
        if frequency is None:
            return None
        if frequency.max and frequency.max > 0:
            return float(frequency.max)
        if frequency.current and frequency.current > 0:
            return float(frequency.current)
        return None