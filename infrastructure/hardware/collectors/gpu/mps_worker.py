# infrastructure/hardware/collectors/gpu/mps_worker.py

import re
import logging
import platform
import subprocess
from typing import Optional

from core.domain.hardware import GPUInfo


logger = logging.getLogger(__name__)


class MPSWorker:
    """
    Self-contained adapter for Apple Silicon GPU and SoC telemetry.

    Implements the same interface as NVMLWorker and SMIWorker, ensuring the
    GPUCollector can use them interchangeably via the Strategy pattern.

    Key design decisions:
    - Graceful degradation: Returns `None` for metrics that lack lightweight
      macOS APIs (e.g., real-time VRAM or power draw) to avoid blocking the benchmark.
    - Two-stage temperature fallback: Attempts a fast `psutil` read first,
      falling back to the heavy `powermetrics` CLI tool only if necessary.
    """

    def __init__(self) -> None:
        """
        Initializes the worker and checks for Apple Silicon compatibility.
        """
        self._is_macos = platform.system() == "Darwin"
        self._chip_name = self._get_chip_name() if self._is_macos else None

    def is_available(self) -> bool:
        """
        Checks if the code is running on macOS with an Apple Silicon chip.

        Returns:
            bool: True if macOS and a valid chip name are detected.
        """
        return self._is_macos and self._chip_name is not None

    def get_info(self) -> GPUInfo:
        """
        Checks if the code is running on macOS with an Apple Silicon chip.

        Returns:
            bool: True if macOS and a valid chip name are detected.
        """
        if not self.is_available():
            return GPUInfo(name=None,
                           memory_mb=None,
                           driver_version=None,
                           cuda_version=None)

        unified_memory_mb = None
        try:
            import psutil
            unified_memory_mb = int(psutil.virtual_memory().total / 1024 / 1024)
        except Exception:
            pass

        return GPUInfo(name=self._chip_name,
                       memory_mb=unified_memory_mb,
                       driver_version=platform.mac_ver()[0],
                       cuda_version=None)

    def get_utilization(self) -> Optional[float]:
        """
        Attempts to retrieve GPU utilization.

        Returns:
            float | None: Always returns `None` on macOS, as there is no lightweight,
                          user-space API for real-time GPU utilization.
        """
        return None

    def get_memory_used_mb(self) -> Optional[float]:
        """
        Attempts to retrieve dedicated VRAM usage.

        Returns:
            float | None: Always returns `None`, as Apple Silicon uses Unified Memory
                          and does not expose separate VRAM tracking to user-space processes.
        """
        return None

    def get_temperature(self) -> Optional[float]:
        """
        Retrieves the current SoC temperature.

        Executes a prioritized fallback chain:
        1. Fast, non-blocking read via `psutil.sensors_temperatures()`.
        2. Heavy CLI read via `powermetrics` (with a strict 5-second timeout).

        Returns:
            float | None: The temperature in Celsius, or `None` if unavailable.
        """
        temp = self._temperature_psutil()
        if temp is not None:
            return temp
        return self._temperature_powermetrics()

    def get_power_watts(self) -> Optional[float]:
        """
        Attempts to retrieve GPU power draw.

        Returns:
            float | None: Always returns `None`, as macOS lacks a lightweight API
                          for real-time power telemetry.
        """
        return None

    def _get_chip_name(self) -> Optional[str]:
        """
        Retrieves the commercial name of the Apple chip (e.g., 'Apple M4 Pro').

        Returns:
            str | None: The chip name string, or `None` if the `sysctl` command fails.
        """
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                check=True, capture_output=True, text=True, timeout=2,
            )
            return result.stdout.strip()
        except Exception as e:
            logger.debug("Не удалось получить имя чипа macOS: %s", e)
            return None

    def _temperature_psutil(self) -> Optional[float]:
        """
        Fast and safe temperature retrieval via `psutil`.

        Returns:
            float | None: The first valid temperature reading (0-150°C) from a
                          sensor labeled with 'cpu' or 'gpu', or `None`.
        """
        try:
            import psutil
            if not hasattr(psutil, "sensors_temperatures"):
                return None

            temps = psutil.sensors_temperatures()
            for sensor_name, readings in temps.items():
                if "cpu" not in sensor_name.lower() and "gpu" not in sensor_name.lower():
                    continue
                for reading in readings:
                    if 0 <= reading.current < 150:
                        return reading.current
        except (AttributeError, OSError, ImportError) as error:
            logger.debug("psutil не вернул MPS temperature: %s", error)

        return None

    def _temperature_powermetrics(self) -> Optional[float]:
        """
        Heavy temperature retrieval via the `powermetrics` CLI tool.

        WARNING: This command can take up to 5 seconds and may require `sudo`
        privileges on some macOS versions. It is used only as a last resort.

        Returns:
            float | None: The parsed SoC/GPU temperature in Celsius, or `None`.
        """
        try:
            result = subprocess.run(
                ["powermetrics", "-n", "1", "--samplers", "thermal"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return None

            for line in result.stdout.splitlines():
                for pattern in (
                        r"CPU die temperature:\s+([\d.]+)\s+C",
                        r"GPU die temperature:\s+([\d.]+)\s+C",
                        r"SoC.*temperature:\s+([\d.]+)\s+C",
                ):
                    match = re.search(pattern, line)
                    if match:
                        temp = float(match.group(1))
                        if 0 <= temp < 150:
                            return temp
        except (OSError, subprocess.SubprocessError, ValueError, subprocess.TimeoutExpired) as error:
            logger.debug("powermetrics не вернул MPS temperature: %s", error)

        return None