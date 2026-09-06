# infrastructure/hardware/collectors/npu/hailo_worker.py

import logging
import platform
from pathlib import Path
from typing import Optional

from core.domain.hardware import NPUInfo


logger = logging.getLogger(__name__)


class HailoWorker:
    """
    Self-contained adapter for obtaining metrics and static information about Hailo NPUs.

    Key design decisions:
    - Fast availability check: Verifies the existence of known sysfs/hwmon paths
      during initialization to avoid expensive operations later.
    - Fallback chain for temperature: Attempts direct Hailo sysfs paths first,
      then falls back to a heuristic scan of the `/sys/class/hwmon` directory.
    - Data sanitization: Validates temperature readings to ensure they fall within
      a physically reasonable range (0°C to 150°C) before returning.
    """

    def __init__(self) -> None:
        """
        Initializes the worker and checks for Hailo NPU availability on Linux.
        """
        self._is_linux = platform.system() == "Linux"
        self._is_available = self._check_availability() if self._is_linux else False

    def _check_availability(self) -> bool:
        """
        Performs a fast check for the presence of Hailo paths in the system.

        Returns:
            bool: True if known Hailo sysfs or hwmon temperature paths exist.
        """
        return (
                Path("/sys/class/hailo/hailo0/device/temperature").exists() or
                Path("/sys/class/hailo_chardev/hailo0/temperature").exists() or
                self._find_hwmon_temp() is not None
        )

    def is_available(self) -> bool:
        """
        Checks if the worker is running on Linux and the Hailo NPU is detected.

        Returns:
            bool: True if the NPU is available for querying.
        """
        return self._is_linux and self._is_available

    def get_info(self) -> NPUInfo:
        """
        Returns static hardware information for the NPU.

        Returns:
            NPUInfo: Populated with the NPU name and host system architecture,
                     or an empty NPUInfo if not available.
        """
        if not self.is_available():
            return NPUInfo(name=None,
                           architecture=None)

        import platform as plt
        return NPUInfo(name="Hailo-8 / Hailo-8L",
                       architecture=plt.machine())

    def get_temperature(self) -> Optional[float]:
        """
        Retrieves the current NPU temperature.

        Executes a prioritized fallback chain:
        1. Direct read from known Hailo sysfs paths.
        2. Heuristic scan of `/sys/class/hwmon` for NPU-related drivers.

        Returns:
            Optional[float] The temperature in Celsius, or `None` if unavailable or invalid.
        """
        if not self.is_available():
            return None

        temp = self._temperature_hailo_sysfs()
        if temp is not None:
            return temp

        return self._find_hwmon_temp()

    def _find_hwmon_temp(self) -> Optional[float]:
        """
        Scans `/sys/class/hwmon` for NPU-specific temperature sensors.

        Looks for driver names containing 'hailo', 'npu', or 'neural', and attempts
        to read the `temp*_input` file, converting millikelvins to Celsius.

        Returns:
            Optional[float] The first valid temperature reading found, or `None`.
        """
        hwmon_root = Path("/sys/class/hwmon")
        if not hwmon_root.exists():
            return None

        npu_driver_names = ("hailo", "npu", "neural")

        for hwmon_dir in hwmon_root.iterdir():
            try:
                name_file = hwmon_dir / "name"
                if not name_file.exists():
                    continue

                driver_name = name_file.read_text(encoding="utf-8", errors="ignore").strip().lower()
                if not any(token in driver_name for token in npu_driver_names):
                    continue

                for temp_input in sorted(hwmon_dir.glob("temp*_input")):
                    try:
                        raw_value = temp_input.read_text(encoding="utf-8", errors="ignore").strip()
                        temp = float(raw_value) / 1000.0
                        if 0 <= temp < 150:
                            return temp
                    except (OSError, ValueError):
                        continue
            except OSError:
                continue
        return None

    def _temperature_hailo_sysfs(self) -> Optional[float]:
        """
        Attempts to read the Hailo NPU temperature directly from dedicated sysfs paths.

        Returns:
            Optional[float] The temperature in Celsius, or `None` if the read fails
                          or the value is outside the valid range.
        """
        hailo_paths = (
            Path("/sys/class/hailo/hailo0/device/temperature"),
            Path("/sys/class/hailo_chardev/hailo0/temperature"),
        )

        for path in hailo_paths:
            if path.exists():
                try:
                    temp = float(path.read_text(encoding="utf-8", errors="ignore").strip())
                    if 0 <= temp < 150:
                        return temp
                except (OSError, ValueError) as error:
                    logger.debug("Hailo sysfs %s не вернул температуру: %s", path, error)
                    continue
        return None

    def get_utilization(self) -> Optional[float]:
        """
        Attempts to retrieve NPU utilization.

        Returns:
            Optional[float] Currently returns `None` as utilization is not exposed
                          via the monitored sysfs/hwmon paths in this implementation.
        """
        return None

    def get_power_watts(self) -> Optional[float]:
        return None