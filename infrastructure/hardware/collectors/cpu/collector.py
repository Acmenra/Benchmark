# infrastructure/hardware/collectors/cpu/collector.py

import os
import time
from typing import Optional

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
    """
    Concrete implementation of the CPU data and telemetry gathering contract.

    This collector handles OS-specific quirks to reliably extract CPU metadata
    and runtime utilization. It caches static data on initialization to ensure
    zero overhead during the benchmarking inference loop.

    Key design decisions:
    - Static info (name, cores, frequency) is gathered exactly once in __init__.
    - Dynamic metrics (utilization) use `time.perf_counter()` for monotonic,
      high-precision timestamping, avoiding OS clock sync jumps.
    - Implements a robust, multi-stage fallback chain for CPU name resolution
      across macOS, Linux, and Windows.
    """

    def __init__(self,
                 system_info_config: SystemInfoConfig) -> None:
        """
        Initializes the CPU collector and pre-computes static hardware info.

        This method warms up the `psutil` CPU percent counter (which requires
        an initial call to establish a baseline for subsequent measurements)
        and caches the static CPU specifications to ensure subsequent
        `get_hardware_info()` calls are O(1).

        Args:
            system_info_config: Configuration flags for telemetry collection.
        """
        super().__init__(system_info_config)
        psutil.cpu_percent(interval=None)
        self._hardware_info = self._gather_static_info()

    def get_hardware_info(self) -> CPUInfo:
        """
        Returns the pre-computed, cached static CPU specifications.

        Returns:
            CPUInfo: An immutable dataclass containing the CPU name, architecture,
                     core counts, and maximum frequency.
        """
        return self._hardware_info

    def get_metrics(self) -> MetricStatistics:
        """
        Captures a single snapshot of the current CPU utilization.

        This method is designed to be called periodically from a background thread
        by the metrics orchestrator. It uses `time.perf_counter()` for the timestamp
        to ensure high-resolution, monotonic timing that is immune to system clock
        adjustments or NTP synchronization drift.

        Returns:
            MetricStatistics: A container holding a single DataPoint representing
                              the current CPU utilization percentage.
        """
        metric = MetricStatistics(unit="percent")
        metric.history.append(DataPoint(time_in_ms=time.perf_counter() * 1000.0,
                                        value=psutil.cpu_percent(interval=None)
                                        )
                              )
        return metric

    def _gather_static_info(self) -> CPUInfo:
        """
        Orchestrates the collection of static CPU metadata.

        Delegates the extraction of the CPU name and max frequency to specialized
        helper methods, while using `psutil` and `os` for core counts and architecture.

        Returns:
            CPUInfo: A fully populated, immutable CPU information dataclass.
        """
        return CPUInfo(name=self._collect_cpu_name(),
                       architecture=empty_to_none(platform.machine()),
                       physical_cores=psutil.cpu_count(logical=False),
                       logical_cores=psutil.cpu_count(logical=True) or os.cpu_count(),
                       max_frequency_mhz=self._collect_max_frequency_mhz())

    def _collect_cpu_name(self) -> Optional[str]:
        """
        Resolves the full commercial name of the CPU using a prioritized fallback chain.

        The resolution order is:
        1. `py-cpuinfo` library (most readable and cross-platform).
        2. OS-specific native commands (`sysctl` on macOS, `/proc/cpuinfo` on Linux).
        3. Standard library fallback (`platform.processor()`).

        Returns:
            Optional[str]: The resolved CPU brand string, or None if it cannot be determined.
        """
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

    def _collect_cpu_name_from_cpuinfo(self) -> Optional[str]:
        """
        Attempts to retrieve the CPU name using the `py-cpuinfo` third-party library.

        Returns:
            Optional[str]: The raw brand string from `py-cpuinfo`, or None if the library
                        is not installed or fails to execute.
        """
        try:
            import cpuinfo
            cpu_info = cpuinfo.get_cpu_info()
            return empty_to_none(cpu_info.get("brand_raw", ""))
        except (ImportError, Exception):
            return None

    def _collect_macos_cpu_name(self) -> Optional[str]:
        """
         Retrieves the CPU name on macOS using the `sysctl` command.

         Queries `machdep.cpu.brand_string` with a strict 3-second timeout to prevent
         hanging on unresponsive system calls.

         Returns:
             Optional[str]: The CPU name string, or a fallback to `platform.processor()`.
         """
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                check=True, capture_output=True, text=True, timeout=3,
            )
            return empty_to_none(result.stdout)
        except (OSError, subprocess.SubprocessError):
            return empty_to_none(platform.processor())

    def _collect_linux_cpu_name(self) -> Optional[str]:
        """
        Retrieves the CPU name on Linux by parsing `/proc/cpuinfo`.

        Scans the file for standard keys like 'model name', 'hardware', or 'model'.
        If parsing fails or yields no result, it falls back to the `lscpu` CLI tool.

        Returns:
            Optional[str]: The extracted CPU name, or None if not found.
        """
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

    def _is_cpu_name_line(self,
                          line: str) -> bool:
        """
        Heuristic check to determine if a line from `/proc/cpuinfo` contains the CPU name.

        Validates that the line starts with a recognized key (e.g., 'model name', 'hardware')
        and contains a non-empty, non-numeric value (to avoid matching the 'processor : 0' line).

        Args:
            line: A single line of text from `/proc/cpuinfo`.

        Returns:
            bool: True if the line is identified as the CPU name declaration.
        """
        normalized_line = line.lower()
        key, _, value = normalized_line.partition(":")
        key = key.strip()
        value = value.strip()

        if key in {"model name", "hardware", "model"}:
            return bool(value)
        return key == "processor" and bool(value) and not value.isdigit()

    def _collect_linux_cpu_name_from_lscpu(self) -> Optional[str]:
        """
        Fallback method to retrieve the CPU name on Linux using the `lscpu` CLI tool.

        Executes `lscpu` with a 3-second timeout and parses the 'Model name:' field.

        Returns:
            Optional[str]: The extracted model name, or None if the command fails or is missing.
        """
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

    def _collect_max_frequency_mhz(self) -> Optional[float]:
        """
        Determines the maximum clock frequency of the CPU in Megahertz.

        Uses `psutil.cpu_freq()`. It prefers the explicit `max` attribute. If that is
        unavailable or zero (common on some ARM/Edge devices), it gracefully falls back
        to the `current` frequency as an approximation.

        Returns:
            Optional[float]: The maximum frequency in MHz, or None if it cannot be determined.
        """
        frequency = psutil.cpu_freq()
        if frequency is None:
            return None
        if frequency.max and frequency.max > 0:
            return float(frequency.max)
        if frequency.current and frequency.current > 0:
            return float(frequency.current)
        return None